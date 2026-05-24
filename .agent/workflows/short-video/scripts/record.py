# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "sounddevice",
#   "soundfile",
#   "faster-whisper",
#   "loguru",
# ]
# ///
"""
record.py — 真人逐页录音工具
==============================
替代 synthesize.py 的 TTS，产出完全相同的 narration.wav + timestamps.json。

用法:
  uv run record.py --storyline ./storyline.md --output ./narration/
  uv run record.py --storyline ./storyline.md --output ./narration/ --whisper-model medium
  uv run record.py --storyline ./storyline.md --output ./narration/ --dry-run

交互:
  回车 → 开始/停止录音
  r    → 重录当前页
  p    → 播放当前录音
  s    → 跳过当前页（用静音占位）
  q    → 中止录音，已录部分仍可拼接
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import wave
from pathlib import Path

# Windows 控制台 Unicode 修复
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import sounddevice as sd
import soundfile as sf
from loguru import logger


# ── Config ─────────────────────────────────────────────────
SAMPLE_RATE = 48000    # 录音采样率（和 synthesize.py 输出一致）
CHANNELS = 1           # 单声道
SCRIPTS_DIR = Path(__file__).resolve().parent


# ── Storyline Parser (复用 synthesize.py 的逻辑) ──────────

def parse_storyline(path: Path) -> list[dict]:
    """解析 storyline.md 为按 slide 分组的台词列表。

    返回: [{ "slide_index": 0, "title": "封面", "lines": ["台词1", "台词2"] }, ...]
    """
    text = path.read_text(encoding="utf-8")
    slides: list[dict] = []
    current_slide = {"slide_index": -1, "title": "", "type": "", "lines": []}
    in_narration = False

    # 截断引用来源汇总
    summary_match = re.search(r"^## 📋", text, re.MULTILINE)
    if summary_match:
        text = text[:summary_match.start()]

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        # 检测 slide 标题: ## [type] 显示标题
        slide_match = re.match(r"^##\s+\[(.+?)\]\s*(.*)", stripped)
        if slide_match:
            # 保存上一个 slide
            if current_slide["slide_index"] >= 0 and current_slide["lines"]:
                slides.append(current_slide)
            slide_type = slide_match.group(1)
            slide_title = slide_match.group(2).strip() or slide_match.group(1)
            current_slide = {
                "slide_index": len(slides),
                "title": slide_title,
                "type": slide_type,
                "lines": [],
            }
            in_narration = False
            continue

        # 检测台词开始标记
        if stripped.startswith("**台词**:") or stripped.startswith("**台词：**") or stripped.startswith("**Narration**:"):
            in_narration = True
            after = re.sub(r"^\*\*(?:台词|Narration)\*\*[：:]", "", stripped).strip()
            if after:
                current_slide["lines"].append(after)
            continue

        # 台词区结束条件: --- 分隔 / 新的 ** 字段 (除了 **台词)
        if in_narration:
            if stripped.startswith("---") or (
                stripped.startswith("**") and not stripped.startswith("**台词") and not stripped.startswith("**Narration")
            ):
                in_narration = False
                continue
            if not stripped:
                # 仅跳过空行，不退出台词解析模式，从而支持两段式中间带空行的排版！
                continue
            if stripped.startswith("|") or stripped.startswith("#"):
                in_narration = False
                continue
            current_slide["lines"].append(stripped)

    # 保存最后一个 slide
    if current_slide["slide_index"] >= 0 and current_slide["lines"]:
        slides.append(current_slide)

    # 重新编号 slide_index
    for i, slide in enumerate(slides):
        slide["slide_index"] = i

    logger.info(f"[Storyline] 解析到 {len(slides)} 个 slide，共 {sum(len(s['lines']) for s in slides)} 行台词")
    return slides


# ── Terminal UI ────────────────────────────────────────────

# ANSI 颜色码
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BG_RED = "\033[41m"


def _clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _show_slide(slide: dict, total: int, status: str = "ready"):
    """在终端显示当前 slide 的台词（提词器）。"""
    _clear_screen()
    idx = slide["slide_index"] + 1
    slide_type = slide["type"]
    title = slide["title"]

    # 状态栏
    if status == "recording":
        status_text = f"  {_BG_RED}{_BOLD} 🔴 录音中 {_RESET}"
    elif status == "done":
        status_text = f"  {_GREEN}{_BOLD} ✅ 已录制 {_RESET}"
    else:
        status_text = f"  {_DIM} ⏸  待录制 {_RESET}"

    print(f"\n{_CYAN}{'═' * 60}{_RESET}")
    print(f"  {_BOLD}📄 Slide {idx}/{total}{_RESET}  [{slide_type}]  {status_text}")
    print(f"  {_DIM}{title}{_RESET}")
    print(f"{_CYAN}{'─' * 60}{_RESET}\n")

    # 台词
    for line in slide["lines"]:
        print(f"  {_YELLOW}{line}{_RESET}\n")

    print(f"{_CYAN}{'─' * 60}{_RESET}")


def _show_controls(is_recorded: bool):
    """显示操作提示。"""
    controls = [
        f"{_GREEN}⏎ 回车{_RESET} 开始录音",
    ]
    if is_recorded:
        controls = [
            f"{_GREEN}⏎ 回车{_RESET} → 下一页",
            f"{_YELLOW}r{_RESET} 重录",
            f"{_CYAN}p{_RESET} 播放",
        ]
    controls.append(f"{_DIM}s 跳过  q 中止{_RESET}")
    print(f"  {'  │  '.join(controls)}")
    print()


# ── Recording Engine ──────────────────────────────────────

def _record_audio(output_path: Path) -> float:
    """录制音频直到用户按回车停止。返回录制时长（秒）。"""
    frames: list[np.ndarray] = []
    stop_event = threading.Event()

    def callback(indata, frame_count, time_info, status):
        if status:
            logger.warning(f"[录音] {status}")
        frames.append(indata.copy())

    # 开始录音
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        callback=callback,
        blocksize=4096,
    )

    with stream:
        input()  # 等待用户按回车停止

    # 保存
    if frames:
        audio = np.concatenate(frames, axis=0)
        sf.write(str(output_path), audio, SAMPLE_RATE, subtype="PCM_16")
        duration = len(audio) / SAMPLE_RATE
        return duration
    return 0.0


def _play_audio(path: Path):
    """播放录音。"""
    if not path.exists():
        print(f"  {_RED}文件不存在{_RESET}")
        return

    try:
        data, sr = sf.read(str(path), dtype="int16")
        print(f"  {_CYAN}▶ 播放中...{_RESET}", end="", flush=True)
        sd.play(data, sr)
        sd.wait()
        print(f" {_GREEN}完成{_RESET}")
    except Exception as e:
        logger.warning(f"播放失败: {e}")
        # 回退到 ffplay
        try:
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
                timeout=30,
            )
        except Exception:
            print(f"  {_RED}播放失败，请手动检查: {path}{_RESET}")


def _get_duration(path: Path) -> float:
    """用 ffprobe 获取音频时长(秒)。"""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


# ── Whisper Timestamp Generation ─────────────────────────

def _generate_timestamps(
    audio_path: Path,
    slides: list[dict],
    slide_wavs: list[Path],
    out_dir: Path,
    whisper_model: str = "medium",
    slide_gap_ms: int = 800,
    gap_ms: int = 300,
) -> list[dict]:
    """用 faster-whisper 从最终音频生成 timestamps.json。

    策略: 逐 slide wav 分别跑 whisper 获取 word-level timestamps，
    然后根据拼接时的偏移量调整绝对时间。
    """
    from faster_whisper import WhisperModel

    logger.info(f"[Whisper] 加载模型 {whisper_model}...")
    model = WhisperModel(whisper_model, device="auto", compute_type="auto")

    timestamps = []
    lead_silence = 0.15  # 和 synthesize.py 一致
    current_time = lead_silence
    global_line_idx = 0

    for slide in slides:
        slide_idx = slide["slide_index"]
        wav_path = slide_wavs[slide_idx]

        if not wav_path.exists():
            # 跳过的 slide，用静音占位
            current_time += 0.5  # 最小占位
            continue

        slide_duration = _get_duration(wav_path)
        is_first_line = True

        # 对单个 slide 的音频跑 whisper
        segments, info = model.transcribe(
            str(wav_path),
            language="zh",
            word_timestamps=True,
            vad_filter=True,
        )

        slide_timestamps = []
        for segment in segments:
            if segment.words:
                # 按句子分组（用标点断句）
                current_sentence = []
                sentence_start = None

                for word in segment.words:
                    if sentence_start is None:
                        sentence_start = word.start

                    current_sentence.append(word.word)

                    # 检测句子结束（标点或最后一个 word）
                    is_end = (word == segment.words[-1] or
                              any(p in word.word for p in "。！？；"))

                    if is_end and current_sentence:
                        text = "".join(current_sentence).strip()
                        if text:
                            slide_timestamps.append({
                                "start": sentence_start,
                                "end": word.end,
                                "text": text,
                            })
                        current_sentence = []
                        sentence_start = None
            else:
                # 没有 word-level，回退到 segment level
                slide_timestamps.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                })

        # 如果 whisper 没有识别到内容，用整个 slide 作为一个 timestamp
        if not slide_timestamps:
            all_text = " ".join(slide["lines"])
            slide_timestamps.append({
                "start": 0.0,
                "end": slide_duration,
                "text": _clean_for_subtitle(all_text),
            })

        # 调整到全局时间轴
        for ts in slide_timestamps:
            global_line_idx += 1
            timestamps.append({
                "index": global_line_idx,
                "start": round(current_time + ts["start"], 3),
                "end": round(current_time + ts["end"], 3),
                "text": _clean_for_subtitle(ts["text"]),
                "slide_index": slide_idx,
                "is_slide_start": is_first_line,
            })
            is_first_line = False

        # 移动时间指针
        current_time += slide_duration + (slide_gap_ms / 1000.0)

    logger.info(f"[Whisper] 生成 {len(timestamps)} 条时间戳")
    return timestamps


def _clean_for_subtitle(text: str) -> str:
    """清洗文本用于字幕显示（和 synthesize.py 保持一致）。"""
    CN_PUNCT_SENTENCE = '。？！；：'
    CN_PUNCT_PAIR = '""''（）《》【】'
    text = re.sub(f'[{CN_PUNCT_SENTENCE}]', '', text)
    text = re.sub(f'[{CN_PUNCT_PAIR}]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ── Concatenation Pipeline ────────────────────────────────

def _concat_audio(
    slide_wavs: list[Path],
    out_dir: Path,
    gap_ms: int = 300,
    slide_gap_ms: int = 800,
    fade_ms: int = 80,
) -> Path:
    """拼接所有 slide 的录音为最终 narration.wav。

    复用 synthesize.py 的后处理逻辑：
    - lead silence (150ms)
    - slide 间静音 (slide_gap_ms)
    - 全局 EBU R128 loudnorm
    """
    tmp = out_dir / "temp_record"
    tmp.mkdir(exist_ok=True)

    target_sr = SAMPLE_RATE
    slide_gap = slide_gap_ms / 1000.0

    # 生成静音文件
    silence_slide = tmp / "silence_slide.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", f"{slide_gap:.3f}",
         "-c:a", "pcm_s16le", str(silence_slide)],
        capture_output=True,
    )

    lead_silence = tmp / "lead_silence.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", "0.15",
         "-c:a", "pcm_s16le", str(lead_silence)],
        capture_output=True,
    )

    trail_silence = tmp / "trail_silence.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", "0.30",
         "-c:a", "pcm_s16le", str(trail_silence)],
        capture_output=True,
    )

    # 归一化每个 slide 录音
    valid_indices = []
    for i, wav in enumerate(slide_wavs):
        if not wav.exists():
            continue
        valid_indices.append(i)
        seg_norm = tmp / f"norm_{i:03d}.wav"
        # 重采样 + 微淡入淡出
        fade = fade_ms / 1000.0
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav),
             "-af", (
                 f"aresample={target_sr},"
                 f"afade=t=in:st=0:d=0.03,"
                 f"afade=t=out:st=0:d={fade}"
             ),
             "-ac", "1", "-c:a", "pcm_s16le", str(seg_norm)],
            capture_output=True,
        )
        # 更新 fade out 的 start 时间
        dur = _get_duration(seg_norm)
        if dur > fade:
            seg_faded = tmp / f"faded_{i:03d}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(seg_norm),
                 "-af", f"afade=t=in:st=0:d=0.03,afade=t=out:st={max(0, dur - fade):.3f}:d={fade:.3f}",
                 "-c:a", "pcm_s16le", str(seg_faded)],
                capture_output=True,
            )
            if seg_faded.exists():
                seg_faded.rename(seg_norm)

    # 拼接
    concat_list = tmp / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write("file 'lead_silence.wav'\n")
        for j, i in enumerate(valid_indices):
            f.write(f"file 'norm_{i:03d}.wav'\n")
            if j < len(valid_indices) - 1:
                f.write("file 'silence_slide.wav'\n")
        f.write("file 'trail_silence.wav'\n")

    merged_wav = tmp / "merged.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(merged_wav)],
        capture_output=True,
    )

    # 全局 loudnorm
    out_audio = out_dir / "narration.wav"
    logger.info("[Concat] 全局 loudnorm (EBU R128 -16 LUFS)...")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(merged_wav),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "pcm_s16le", str(out_audio)],
        capture_output=True,
    )
    if result.returncode != 0 or not out_audio.exists():
        logger.warning("[Concat] loudnorm 失败，使用原始合并")
        shutil.copy2(str(merged_wav), str(out_audio))

    # 清理临时文件
    shutil.rmtree(tmp, ignore_errors=True)

    total_dur = _get_duration(out_audio)
    logger.success(f"[Concat] {out_audio.name} ({total_dur:.1f}s)")
    return out_audio


# ── Main Recording Loop ──────────────────────────────────

def record_session(
    slides: list[dict],
    out_dir: Path,
    whisper_model: str = "medium",
    gap_ms: int = 300,
    slide_gap_ms: int = 800,
    fade_ms: int = 80,
    dry_run: bool = False,
):
    """主录音循环。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw_recordings"
    raw_dir.mkdir(exist_ok=True)

    total = len(slides)
    slide_wavs = [raw_dir / f"slide_{i:03d}.wav" for i in range(total)]

    logger.info(f"[Record] 开始录音：{total} 个 slide")
    if dry_run:
        logger.info("[Record] dry-run 模式：用静音替代录音")

    i = 0
    while i < total:
        slide = slides[i]
        wav_path = slide_wavs[i]
        is_recorded = wav_path.exists()

        _show_slide(slide, total, "done" if is_recorded else "ready")
        _show_controls(is_recorded)

        if dry_run:
            # 生成 2 秒静音作为替代
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i",
                 f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", "2.0",
                 "-c:a", "pcm_s16le", str(wav_path)],
                capture_output=True,
            )
            print(f"  {_GREEN}[dry-run] 生成 2s 静音{_RESET}")
            i += 1
            continue

        cmd = input(f"  {_DIM}>{_RESET} ").strip().lower()

        if cmd == "q":
            logger.info("[Record] 用户中止录音")
            break
        elif cmd == "s":
            print(f"  {_YELLOW}跳过 Slide {i + 1}{_RESET}")
            i += 1
            continue
        elif cmd == "p" and is_recorded:
            _play_audio(wav_path)
            continue
        elif cmd == "r" or (cmd == "" and not is_recorded):
            # 开始录音
            _show_slide(slide, total, "recording")
            print(f"  {_RED}{_BOLD}🔴 录音中...{_RESET}  按 {_GREEN}回车{_RESET} 停止\n")
            duration = _record_audio(wav_path)
            logger.info(f"  [Slide {i + 1}] 录制 {duration:.1f}s → {wav_path.name}")

            # 录完后显示结果，等待确认
            _show_slide(slide, total, "done")
            dur_str = f"{duration:.1f}s"
            print(f"  {_GREEN}✅ 已录制 ({dur_str}){_RESET}")
            _show_controls(True)
            continue
        elif cmd == "" and is_recorded:
            # 下一页
            i += 1
            continue
        else:
            print(f"  {_DIM}无效操作，请重试{_RESET}")
            continue

    # ── 汇总 ──
    recorded_count = sum(1 for w in slide_wavs if w.exists())
    print(f"\n{_CYAN}{'═' * 60}{_RESET}")
    print(f"  {_BOLD}录音完成{_RESET}: {recorded_count}/{total} 个 slide 已录制")
    print(f"{_CYAN}{'═' * 60}{_RESET}\n")

    if recorded_count == 0:
        logger.error("没有任何录音，退出")
        return

    # ── 拼接 ──
    logger.info("[Pipeline] 开始拼接音频...")
    _concat_audio(slide_wavs, out_dir, gap_ms, slide_gap_ms, fade_ms)

    # ── 生成时间戳 ──
    logger.info("[Pipeline] 生成时间戳...")
    timestamps = _generate_timestamps(
        out_dir / "narration.wav",
        slides,
        slide_wavs,
        out_dir,
        whisper_model=whisper_model,
        slide_gap_ms=slide_gap_ms,
        gap_ms=gap_ms,
    )

    ts_path = out_dir / "timestamps.json"
    ts_path.write_text(
        json.dumps(timestamps, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.success(f"[Pipeline] timestamps.json ({len(timestamps)} 条)")

    # 保留 raw_recordings 目录供后续重录单页
    logger.info(f"[Pipeline] 原始录音保留在: {raw_dir}")
    logger.success(f"[Pipeline] ✅ 完成！可直接渲染: node render.mjs --data ...")


# ── CLI ────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="真人逐页录音工具 — 替代 TTS，产出 narration.wav + timestamps.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
交互操作:
  ⏎ 回车    开始录音 / 确认并下一页
  r         重录当前页
  p         播放当前录音
  s         跳过当前页
  q         中止录音
        """,
    )
    p.add_argument("--storyline", type=Path, required=True, help="storyline.md 路径")
    p.add_argument("--output", type=Path, required=True, help="输出目录")
    p.add_argument("--whisper-model", default="medium",
                   choices=["tiny", "base", "small", "medium", "large-v3"],
                   help="Whisper 模型大小 (默认: medium)")
    p.add_argument("--gap", type=int, default=300, help="句间停顿 ms")
    p.add_argument("--slide-gap", type=int, default=800, help="换页停顿 ms")
    p.add_argument("--fade", type=int, default=80, help="淡入淡出 ms")
    p.add_argument("--dry-run", action="store_true",
                   help="用静音替代录音（测试拼接流程）")
    args = p.parse_args()

    if not args.storyline.exists():
        logger.error(f"文件不存在: {args.storyline}")
        return

    slides = parse_storyline(args.storyline)
    if not slides:
        logger.error("未解析到任何台词")
        return

    record_session(
        slides,
        args.output,
        whisper_model=args.whisper_model,
        gap_ms=args.gap,
        slide_gap_ms=args.slide_gap,
        fade_ms=args.fade,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
