# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
视频组装器 v6（高精度幻灯片版）
===============================
基于 ffmpeg concat demuxer 处理幻灯片：
  - 核心：先生成纯视频轨道，再与完整音频合并，最后叠加字幕
  - 优势：三步分离，避免视频内容与字幕互相覆盖
  - 兼容：支持 visuals/ (mp4) 和 slides/ (png)

用法: uv run assemble_video.py <project_dir>
"""
import subprocess
import json
import re
from pathlib import Path
import argparse
import shutil

RESOLUTION = (1920, 1080)
SUBTITLE_BAR_H = 200      # 字幕条高度（像素），与幻灯片内容解耦
SUBTITLE_BG = "0xf0f2f7"  # 字幕条背景色（与 slides.md section background 一致）


def main():
    parser = argparse.ArgumentParser(description="高精度幻灯片视频组装器")
    parser.add_argument("project_dir")
    args = parser.parse_args()

    proj = Path(args.project_dir)
    narration_dir = proj / "narration"
    visuals_dir = proj / "visuals"
    slides_dir = proj / "slides"
    output_dir = proj / "output"
    output_dir.mkdir(exist_ok=True)
    tmp_dir = output_dir / "tmp_build"
    tmp_dir.mkdir(exist_ok=True)

    # 1. 读取旁白 (优先项目根目录，兼容 narration/ 下)
    script_path = proj / "script.txt"
    if not script_path.exists():
        script_path = narration_dir / "script.txt"
    if not script_path.exists():
        print(f"Error: script.txt not found in {proj} or {narration_dir}")
        return

    # 剥离视觉提示后缀读取文本，跳过章节标头和空行
    # 支持多行对应一张幻灯片：有 | 的行开新 slide，没有 | 的行延续上一张
    raw_lines = script_path.read_text(encoding="utf-8").splitlines()
    lines = []
    visual_hints = []
    for l in raw_lines:
        stripped = l.strip()
        if not stripped or stripped.startswith('#'):
            continue
        parts = stripped.split('|', 1)
        lines.append(parts[0].strip())
        # 没有 | 分隔符的行 → 延续上一张 slide（hint 为空字符串标记）
        visual_hints.append(parts[1].strip() if len(parts) > 1 else '')
    n = len(lines)
    print(f"Narrations: {n} segments")

    # 构建 slide 索引映射：
    #   - 有 | 且不含 [同上] → 新 slide
    #   - 有 | 且含 [同上]   → 复用上一页 slide
    #   - 没有 |（hint 为空）→ 延续上一页 slide（多行对应一张）
    slide_indices = []
    current_slide = 0
    for i, hint in enumerate(visual_hints):
        if not hint:
            # 没有 | 分隔符的行，延续上一张 slide
            slide_indices.append(max(current_slide, 1))
        elif '同上' in hint:
            slide_indices.append(current_slide)
        else:
            current_slide += 1
            slide_indices.append(current_slide)
    total_slides = current_slide
    print(f"Unique slides: {total_slides} ({n - total_slides} shared)")

    # 2. 读取音频
    audio_path = find_audio(narration_dir)
    audio_dur = get_duration(audio_path)
    print(f"Audio: {audio_path.name} ({audio_dur:.1f}s)")

    # 3. 获取时间戳
    ts_path = narration_dir / "timestamps.json"
    if ts_path.exists():
        print("Time: Using TTS timestamps")
        segments = json.loads(ts_path.read_text(encoding="utf-8"))
    else:
        print("Time: Using proportional segments (pro-rata)")
        segments = proportion_segments(lines, audio_dur)

    # 4. 构建场景/幻灯片映射
    scene_map = build_scene_map(visuals_dir, slides_dir, n, slide_indices)

    # 确保段数匹配
    n_segs = min(len(segments), n)
    segments = segments[:n_segs]

    # 5. 生成字幕
    srt_path = output_dir / "subtitles.srt"
    generate_srt(segments, srt_path)

    # 6. 生成视频轨（Concat Demuxer 方案）
    w, h = RESOLUTION
    concat_list = tmp_dir / "video_concat.txt"

    print(f"\n[Step 1/3] Preparing frame sequence...")
    with open(concat_list, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            dur = seg["end"] - seg["start"]
            if i + 1 < len(segments):
                gap = segments[i + 1]["start"] - seg["end"]
                if gap > 0:
                    dur += gap  # 幻灯片在音频停顿期间保持显示

            scene_path = scene_map.get(i + 1)

            if scene_path and scene_path.exists():
                f.write(f"file '{scene_path.resolve()}'\n")
                f.write(f"duration {dur:.6f}\n")
            else:
                black_img = tmp_dir / f"black_{i:02d}.png"
                if not black_img.exists():
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:d=1",
                        "-frames:v", "1", str(black_img)
                    ], capture_output=True)
                f.write(f"file '{black_img.resolve()}'\n")
                f.write(f"duration {dur:.6f}\n")

            print(f"  [{i+1:2d}] {scene_path.name if scene_path else 'black'} -> {dur:.2f}s")

        # Concat Demuxer 最后的哨兵包
        if segments:
            last_scene = scene_map.get(len(segments))
            if last_scene and last_scene.exists():
                 f.write(f"file '{last_scene.resolve()}'\n")

    # ── 分步合成（视频内容与字幕分离）──────────────────────

    # 7a. 幻灯片 → 纯视频轨 (无音频)
    print(f"\n[Step 2/3] Generating slideshow + muxing audio...")
    total_h = h + SUBTITLE_BAR_H
    print(f"  Layout: {w}x{h} slide + {SUBTITLE_BAR_H}px subtitle bar = {w}x{total_h}")
    slideshow_path = tmp_dir / "slideshow.mp4"
    r1 = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
               f"pad={w}:{h}:-1:-1:color=black,"
               f"pad={w}:{total_h}:0:0:color={SUBTITLE_BG},"
               f"fps=30",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
        str(slideshow_path)
    ], capture_output=True, text=True)
    if r1.returncode != 0:
        print(f"  [ERR] Slideshow failed: {r1.stderr[-500:]}")
    else:
        ss_size = slideshow_path.stat().st_size / 1024 / 1024 if slideshow_path.exists() else 0
        print(f"  Slideshow: {ss_size:.1f}MB")

    # 7b. 视频 + 音频 → 中间文件 (无字幕)
    muxed_path = tmp_dir / "muxed.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(slideshow_path), "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(muxed_path)
    ], capture_output=True)

    # 7c. 字幕叠加 → 最终视频（字幕渲染在底部独立字幕条中）
    print(f"[Step 3/3] Burning subtitles into subtitle bar...")

    # 生成 ASS 字幕文件，精确控制字幕位置在底部 200px 字幕条内
    ass_path = tmp_dir / "subtitles.ass"
    play_res_y = h + SUBTITLE_BAR_H  # 1280
    # MarginV: 从底部算起，将字幕居中于字幕条
    margin_v = (SUBTITLE_BAR_H - 90) // 2  # 90≈字号对应行高，居中
    with open(ass_path, "w", encoding="utf-8") as af:
        af.write("[Script Info]\n")
        af.write(f"PlayResX: {w}\n")
        af.write(f"PlayResY: {play_res_y}\n")
        af.write("ScaledBorderAndShadow: yes\n\n")
        af.write("[V4+ Styles]\n")
        af.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                 "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                 "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                 "Alignment, MarginL, MarginR, MarginV, Encoding\n")
        af.write(f"Style: Default,Microsoft YaHei UI,72,"
                 f"&H003b2a1e,&H000000FF,&H40f7f2f0,&H00000000,"
                 f"-1,0,0,0,100,100,0,0,1,3,0,"
                 f"2,80,80,{margin_v},1\n\n")
        af.write("[Events]\n")
        af.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        # 解析 SRT → ASS events
        with open(srt_path, "r", encoding="utf-8") as sf:
            srt_content = sf.read().strip().replace("\r\n", "\n")
        blocks = srt_content.split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_line = lines[1].replace(",", ".")
                parts = time_line.split(" --> ")
                start = parts[0].strip()
                end = parts[1].strip()
                text = " ".join(lines[2:]).replace("\n", "\\N")
                # ASS 时间格式: H:MM:SS.cc
                def srt_to_ass_time(t):
                    h_, m_, rest = t.split(":")
                    s_, ms_ = rest.split(".")
                    return f"{int(h_)}:{m_}:{s_}.{ms_[:2]}"
                af.write(f"Dialogue: 0,{srt_to_ass_time(start)},{srt_to_ass_time(end)},"
                         f"Default,,0,0,0,,{text}\n")

    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    final_path = output_dir / "final.mp4"
    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(muxed_path),
        "-vf", f"subtitles='{ass_escaped}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        str(final_path)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [WARN] ASS subtitle burn failed, falling back to no subtitles")
        print(f"  stderr: {result.stderr[-500:] if result.stderr else 'none'}")
        # Fallback: just copy muxed as final
        shutil.copy2(str(muxed_path), str(final_path))

    # 清理
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if final_path.exists():
        size_mb = final_path.stat().st_size / 1024 / 1024
        print(f"\nOK: {final_path} ({size_mb:.1f}MB)")
    else:
        print("\nERROR: Assembly failed")


def find_audio(narration_dir: Path) -> Path:
    for name in ["narration.mp3", "full_narration_myvoice.mp3", "full_narration_qwen.mp3", "full_narration.mp3"]:
        p = narration_dir / name
        if p.exists():
            return p
    mp3s = list(narration_dir.glob("*.mp3"))
    if mp3s:
        return mp3s[0]
    raise FileNotFoundError(f"Missing audio in {narration_dir}")


def get_duration(path: Path) -> float:
    if path.suffix.lower() in [".png", ".jpg", ".jpeg"]: return 0.0
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stdout.strip()
    return float(out) if out else 0.0


def build_scene_map(visuals_dir: Path, slides_dir: Path, n: int, slide_indices: list = None) -> dict[int, Path]:
    """构建场景映射。支持 slide_indices 做 [同上] 复用。"""
    scene_map = {}
    for i in range(1, n + 1):
        if slide_indices and i <= len(slide_indices):
            slide_num = slide_indices[i - 1]
        else:
            slide_num = i

        paths = [
            visuals_dir / f"scene_{slide_num:02d}.mp4",
            slides_dir / f"slides.{slide_num:03d}.png",
            slides_dir / f"video_slides.{slide_num:03d}.png",
            slides_dir / f"video_slides.{slide_num}.png",
            slides_dir / f"slide.{slide_num:03d}.png",
            slides_dir / f"slide.{slide_num}.png",
        ]
        for p in paths:
            if p.exists():
                scene_map[i] = p
                break
    return scene_map


def proportion_segments(lines, total_dur):
    char_counts = [len(line) for line in lines]
    total_chars = sum(char_counts)
    segments = []
    t = 0.0
    for i, line in enumerate(lines):
        dur = (char_counts[i] / total_chars) * total_dur
        segments.append({
            "index": i + 1,
            "start": round(t, 3),
            "end": round(t + dur, 3),
            "text": line,
        })
        t += dur
    return segments


def split_by_punct(text, punct):
    """按标点符号分句。"""
    sentences = []
    current = ""
    for ch in text:
        current += ch
        if ch in punct:
            sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences


def merge_short(sentences, min_len=6):
    """合并过短的片段。"""
    if not sentences:
        return []
    merged = []
    buf = ""
    for s in sentences:
        buf += s
        if len(buf) >= min_len:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] += buf
        else:
            merged.append(buf)
    return merged


def split_long(text, max_chars):
    """拆分长句，不劈开英文单词/数字/引号内容。"""
    chunks = []
    current = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isascii() and ch.isalpha():
            word = ""
            while i < len(text) and (text[i].isascii() and (text[i].isalpha() or text[i] in '-_')):
                word += text[i]
                i += 1
            if len(current) + len(word) > max_chars and current:
                chunks.append(current.strip())
                current = ""
            current += word
        elif ch.isdigit():
            word = ""
            while i < len(text) and (text[i].isdigit() or text[i] in '.%'):
                word += text[i]
                i += 1
            if i < len(text) and text[i] in '年分倍次个级维亿万千百层':
                word += text[i]
                i += 1
            if len(current) + len(word) > max_chars and current:
                chunks.append(current.strip())
                current = ""
            current += word
        else:
            current += ch
            i += 1
            if len(current) >= max_chars:
                chunks.append(current.strip())
                current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks


def generate_srt(segments, output_path, max_chars=40):
    """生成 SRT 字幕。字幕持续显示直到下一条替换（无空白间隙）。"""
    sentence_punct = set("。！？；!?;")

    # 第一步：收集所有字幕条目（start, end, text）
    entries = []
    for seg in segments:
        text = seg.get("text", "")
        if "|" in text:
            text = text.split("|")[0].strip()
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start

        # 先按标点分句（保留标点用于分句定位）
        sentences = split_by_punct(text, sentence_punct)
        merged = merge_short(sentences, 12)
        if not merged:
            continue

        final_chunks = []
        for s in merged:
            if len(s) <= max_chars:
                final_chunks.append(s)
            else:
                final_chunks.extend(split_long(s, max_chars))

        # 分句完成后，去掉标点让字幕更干净
        import re as _re
        cleaned = []
        for c in final_chunks:
            # 列举标点 → 空格（防止名词合并）
            c = _re.sub(r'[、，,]', ' ', c)
            # 句末/装饰标点 → 删除
            c = _re.sub(r'[。；：！？\u201c\u201d\u2018\u2019（）《》【】]', '', c)
            c = _re.sub(r'\s{2,}', ' ', c).strip()
            if c:
                cleaned.append(c)
        final_chunks = cleaned

        total_chars = sum(len(c) for c in final_chunks)
        if total_chars == 0:
            continue

        t = seg_start
        for chunk in final_chunks:
            chunk_dur = (len(chunk) / total_chars) * seg_dur
            end_t = min(t + chunk_dur, seg_end)
            entries.append((t, end_t, chunk))
            t = end_t

    # 第二步：字幕持续显示 — 每条字幕的结束时间 = 下一条的开始时间
    for i in range(len(entries) - 1):
        start_i, end_i, text_i = entries[i]
        start_next = entries[i + 1][0]
        # 延长到下一条字幕开始（字幕无间隙切换）
        entries[i] = (start_i, start_next, text_i)

    # 第三步：写入 SRT
    with open(output_path, "w", encoding="utf-8-sig") as f:
        for idx, (start, end, text) in enumerate(entries, 1):
            f.write(f"{idx}\n")
            f.write(f"{fmt_time(start)} --> {fmt_time(end)}\n")
            f.write(f"{text}\n\n")

    print(f"  SRT: {len(entries)} lines")


def fmt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

if __name__ == "__main__":
    main()
