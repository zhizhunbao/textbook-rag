# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "edge-tts",
#   "loguru",
#   "qwen-tts",
#   "soundfile",
#   "torch",
#   "torchaudio",
#   "tencentcloud-sdk-python",
#   "python-dotenv",
# ]
#
# [tool.uv.sources]
# torch = { index = "pytorch-cu124" }
# torchaudio = { index = "pytorch-cu124" }
#
# [[tool.uv.index]]
# name = "pytorch-cu124"
# url = "https://download.pytorch.org/whl/cu124"
# explicit = true
# ///
"""
synthesize.py — TTS 语音合成工具
================================
独立工具脚本：script.txt → narration.mp3 + timestamps.json

用法:
  uv run synthesize.py --script ./script.txt --output ./narration/
  uv run synthesize.py --script ./script.txt --output ./narration/ --backend edge
  uv run synthesize.py --script ./script.txt --output ./narration/ --backend moss --voice-sample ./voice.wav
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from loguru import logger


# ── Config ──────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_VOICE_SAMPLE = SCRIPTS_DIR.parent / "voice" / "voice-sample.wav"
MOSS_REPO = Path(__file__).resolve().parents[4] / ".github" / "references" / "MOSS-TTS-Nano"


# ── Script Parser ──────────────────────────────────────────

def parse_script(path: Path) -> list[dict]:
    """解析 script.txt 为结构化列表。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    parsed = []
    chapter = ""
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("# "):
            chapter = raw[2:].strip()
            continue
        has_pipe = "|" in raw
        parts = raw.rsplit("|", 1)
        narration = parts[0].strip()
        hint = ""
        if len(parts) > 1:
            m = re.search(r"\[(.+?)\]", parts[1])
            if m:
                hint = m.group(1).strip()
        parsed.append({
            "chapter": chapter,
            "narration": narration,
            "visual_hint": hint,
            "line_idx": len(parsed),
            "is_slide_start": has_pipe,  # 有 | = 新幻灯片开始
        })
    return parsed


# ── TTS Text Preprocessing ─────────────────────────────────

def _clean_for_tts(text: str) -> str:
    """清洗文本以减少 TTS 不自然停顿。

    - 中文标点（。，、；：！？）→ 空格
    - 连续多个空格 → 单个空格
    - 首尾空格去掉
    """
    # 中文标点 → 空格
    text = re.sub(r'[。，、；：！？""''（）《》【】]', ' ', text)
    # 连续空格 → 单个
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ── TTS Backends ───────────────────────────────────────────

def _get_duration(p: Path) -> float:
    """用 ffprobe 获取音频时长(秒)。"""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
         str(p)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 0.0


async def _synth_edge(text: str, voice: str, out: Path, rate: str = "-10%"):
    """Edge TTS 合成。"""
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def _synth_moss(text: str, out: Path, sample: Path | None = None) -> str:
    """MOSS-TTS-Nano 声音克隆。"""
    s = sample or DEFAULT_VOICE_SAMPLE
    if not s.exists():
        raise FileNotFoundError(f"Voice sample not found: {s}")
    script = MOSS_REPO / "infer.py"
    if not script.exists():
        raise FileNotFoundError(f"MOSS-TTS-Nano not found at {MOSS_REPO}")

    wav = out.with_suffix(".wav")
    r = subprocess.run(
        ["python", str(script), "--text", text,
         "--prompt-audio-path", str(s), "--output-audio-path", str(wav),
         "--mode", "voice_clone",
         "--device", "auto", "--dtype", "auto",
         "--audio-temperature", "0.8",
         "--audio-top-p", "0.95", "--audio-top-k", "25",
         "--audio-repetition-penalty", "1.2",
         "--max-new-frames", "500",
         "--enable-wetext-processing", "0"],
        capture_output=True, text=True, timeout=180,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if r.returncode != 0:
        raise RuntimeError(f"[MOSS] Voice clone failed:\n{r.stderr[:500]}")

    if wav.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav),
             "-codec:a", "libmp3lame", "-b:a", "192k", str(out)],
            capture_output=True,
        )
        if out.exists():
            wav.unlink(missing_ok=True)
    return "ok"


def _synth_hf(text: str, out: Path) -> str:
    """HyperFrames 内置 TTS (Kokoro zf_xiaobei)。"""
    r = subprocess.run(
        ["npx", "hyperframes", "tts", text,
         "-v", "zf_xiaobei", "-o", str(out), "--json"],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        logger.warning(f"[HF-TTS] {r.stderr[:200]}")
        return "error"
    return "ok"


# ── Tencent Cloud TTS Backend ──────────────────────────────

def _init_tencent_client():
    """初始化腾讯云 TTS 客户端（仅调用一次）。"""
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[4] / ".env"
    load_dotenv(env_path)

    secret_id = os.environ.get("SecretId", "")
    secret_key = os.environ.get("SecretKey", "")
    if not secret_id or not secret_key:
        raise RuntimeError(f"SecretId/SecretKey not found in {env_path}")

    from tencentcloud.common import credential
    from tencentcloud.tts.v20190823 import tts_client
    cred = credential.Credential(secret_id, secret_key)
    return tts_client.TtsClient(cred, "ap-shanghai")


def _synth_tencent(client, text: str, out: Path, voice_type: int = 101007):
    """腾讯云 TTS 单句合成 → mp3。"""
    import base64
    from tencentcloud.tts.v20190823 import models

    req = models.TextToVoiceRequest()
    req.Text = text
    req.SessionId = f"synth_{hash(text) & 0xFFFFFF:06x}"
    req.VoiceType = voice_type
    req.Volume = 5
    req.Speed = 0
    req.Codec = "mp3"

    resp = client.TextToVoice(req)
    audio = base64.b64decode(resp.Audio)

    with open(out, "wb") as f:
        f.write(audio)


# ── Qwen3-TTS Backend ──────────────────────────────────────

def _load_qwen_model(voice_sample: Path | None = None):
    """加载 Qwen3-TTS 模型（仅加载一次）。"""
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

    if voice_sample and voice_sample.exists():
        logger.info(f"[Qwen] Loading Base model for voice cloning...")
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map="cuda:0",
            dtype="auto",
        )

        # 读取参考音频文字转录（ICL 模式需要）
        ref_text_file = voice_sample.with_suffix(".txt")
        ref_text = ""
        if ref_text_file.exists():
            ref_text = ref_text_file.read_text(encoding="utf-8").strip()
            logger.info(f"[Qwen] Reference transcript loaded from {ref_text_file.name}")

        # ICL 模式：同时学习音色 + 韵律 + 说话风格（需要 ref_text）
        # x_vector_only 模式：仅提取音色向量（不需要 ref_text，质量较低）
        use_icl = bool(ref_text)
        if use_icl:
            logger.info("[Qwen] ICL mode: timbre + prosody + style (高质量)")
        else:
            logger.warning("[Qwen] x_vector_only mode (低质量). 建议创建 voice-sample.txt 启用 ICL")

        logger.info(f"[Qwen] Extracting voice features from {voice_sample.name}...")
        voice_prompt = model.create_voice_clone_prompt(
            ref_audio=str(voice_sample),
            ref_text=ref_text if use_icl else None,
            x_vector_only_mode=not use_icl,
        )
        return model, "clone", voice_prompt
    else:
        logger.info("[Qwen] Loading CustomVoice model (preset)...")
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
            device_map="cuda:0",
            dtype="auto",
        )
        return model, "preset", None


def _synth_qwen(model, mode: str, voice_prompt, text: str, out: Path, speaker: str = "uncle_fu"):
    """Qwen3-TTS 单句合成 → mp3。"""
    import numpy as np
    import soundfile as sf

    if mode == "clone":
        wavs, sr = model.generate_voice_clone(
            text=text, language="Chinese", voice_clone_prompt=voice_prompt
        )
    else:
        wavs, sr = model.generate_custom_voice(
            text=text, speaker=speaker, language="Chinese"
        )

    wav_tmp = out.with_suffix(".wav")
    sf.write(str(wav_tmp), wavs[0], sr)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_tmp),
         "-c:a", "libmp3lame", "-b:a", "192k", str(out)],
        capture_output=True,
    )
    if out.exists():
        wav_tmp.unlink(missing_ok=True)


# ── Main Synthesis Pipeline ───────────────────────────────

async def synthesize(
    parsed: list[dict],
    out_dir: Path,
    backend: str = "qwen",
    voice: str = "zh-CN-YunxiNeural",
    rate: str = "-10%",
    gap_ms: int = 300,
    slide_gap_ms: int = 800,
    voice_sample: Path | None = None,
) -> Path:
    """逐句 TTS → 拼接 → 输出 narration.mp3 + timestamps.json。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "temp_audio"
    tmp.mkdir(exist_ok=True)

    lines = [it["narration"] for it in parsed]
    logger.info(f"[TTS] {len(lines)} segments · {backend}")

    # Qwen: 模型只加载一次
    qwen_model, qwen_mode, qwen_prompt = None, None, None
    if backend == "qwen":
        qwen_model, qwen_mode, qwen_prompt = _load_qwen_model(voice_sample)

    # Tencent: 客户端只初始化一次
    tencent_client = None
    if backend == "tencent":
        tencent_client = _init_tencent_client()

    timestamps = []
    t = 0.0
    gap = gap_ms / 1000.0
    slide_gap = slide_gap_ms / 1000.0

    for i, line in enumerate(lines):
        logger.info(f"  [{i+1}/{len(lines)}] {line[:35]}...")
        seg = tmp / f"seg_{i:03d}.mp3"

        if backend == "tencent":
            _synth_tencent(tencent_client, line, seg, voice_type=int(voice))
        elif backend == "qwen":
            _synth_qwen(qwen_model, qwen_mode, qwen_prompt, line, seg)
        elif backend == "moss":
            _synth_moss(line, seg, voice_sample)
        elif backend == "hf":
            wav = tmp / f"seg_{i:03d}.wav"
            _synth_hf(line, wav)
            if wav.exists():
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav),
                     "-codec:a", "libmp3lame", "-b:a", "192k", str(seg)],
                    capture_output=True,
                )
                wav.unlink(missing_ok=True)
        else:
            await _synth_edge(line, voice, seg, rate)

        dur = _get_duration(seg)
        timestamps.append({
            "index": i + 1,
            "start": round(t + 0.15, 3),  # +0.15s 前置静音偏移
            "end": round(t + dur + 0.15, 3),
            "text": _clean_for_tts(line),  # 字幕去标点，更干净
        })
        # 下一行是新幻灯片 → 长停顿；否则 → 短停顿
        next_is_slide = (i + 1 < len(parsed) and parsed[i + 1].get("is_slide_start", False))
        current_gap = slide_gap if next_is_slide else gap
        t += dur + current_gap

    # ── 统一采样率 → WAV 拼接 → 一次性编码 MP3 ──
    # Edge TTS 输出 24kHz MP3, 静音文件 44100Hz → -c copy 拼接会导致时间戳混乱
    # 解决方案：全部转成 44100Hz WAV，无损拼接后统一编码

    target_sr = 44100

    # 生成短停顿静音 WAV（句间）
    silence_short = tmp / "silence_short.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", f"{gap:.3f}",
         "-c:a", "pcm_s16le", str(silence_short)],
        capture_output=True,
    )

    # 生成长停顿静音 WAV（换页）
    silence_slide = tmp / "silence_slide.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", f"{slide_gap:.3f}",
         "-c:a", "pcm_s16le", str(silence_slide)],
        capture_output=True,
    )

    # 前置静音，防止 MP3 编码器延迟截掉开头
    lead_silence = tmp / "lead_silence.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", "0.15",
         "-c:a", "pcm_s16le", str(lead_silence)],
        capture_output=True,
    )

    # 将所有 MP3 段转为统一采样率 WAV
    logger.info(f"[Concat] Normalizing {len(lines)} segments to {target_sr}Hz WAV...")
    for i in range(len(lines)):
        seg_mp3 = tmp / f"seg_{i:03d}.mp3"
        seg_wav = tmp / f"seg_{i:03d}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(seg_mp3),
             "-ar", str(target_sr), "-ac", "1",
             "-c:a", "pcm_s16le", str(seg_wav)],
            capture_output=True,
        )

    # 拼接 WAV 文件（无损，无帧对齐问题）
    concat_list = tmp / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write("file 'lead_silence.wav'\n")  # 开头保护
        for i in range(len(lines)):
            f.write(f"file 'seg_{i:03d}.wav'\n")
            if i < len(lines) - 1:
                # 下一行是新幻灯片 → 长停顿；否则 → 短停顿
                next_is_slide = parsed[i + 1].get("is_slide_start", False)
                sil_name = "silence_slide.wav" if next_is_slide else "silence_short.wav"
                f.write(f"file '{sil_name}'\n")

    # WAV 拼接（-c copy 对 WAV 是安全的，因为 PCM 无帧对齐问题）
    merged_wav = tmp / "merged.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(merged_wav)],
        capture_output=True,
    )

    # 一次性编码为 MP3
    out_audio = out_dir / "narration.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(merged_wav),
         "-c:a", "libmp3lame", "-b:a", "192k", str(out_audio)],
        capture_output=True,
    )

    # ── 验证时间戳 vs 实际音频时长 ──
    actual_total = _get_duration(out_audio)
    ts_total = timestamps[-1]["end"] if timestamps else 0
    drift = abs(actual_total - ts_total) if (actual_total > 0 and ts_total > 0) else 0
    if drift > 1.0:
        logger.warning(
            f"[Verify] drift={drift:.1f}s (timestamp={ts_total:.1f}s, actual={actual_total:.1f}s)"
        )
    else:
        logger.info(f"[Verify] OK: timestamp={ts_total:.1f}s ≈ actual={actual_total:.1f}s (Δ={drift:.2f}s)")

    (out_dir / "timestamps.json").write_text(
        json.dumps(timestamps, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    shutil.rmtree(tmp, ignore_errors=True)
    total = timestamps[-1]["end"] if timestamps else 0
    logger.success(f"[TTS] {out_audio.name} ({total:.1f}s)")
    return out_audio


# ── CLI ────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="TTS 语音合成工具")
    p.add_argument("--script", type=Path, required=True, help="script.txt 路径")
    p.add_argument("--output", type=Path, required=True, help="输出目录")
    p.add_argument("--backend", choices=["moss", "edge", "hf", "qwen", "tencent"], default="tencent")
    p.add_argument("--voice", default="101007", help="Edge: voice name; Tencent: VoiceType ID")
    p.add_argument("--voice-sample", type=Path, default=None)
    p.add_argument("--rate", default="-10%")
    p.add_argument("--gap", type=int, default=300, help="句间停顿 ms（同一张幻灯片内）")
    p.add_argument("--slide-gap", type=int, default=800, help="换页停顿 ms（切换幻灯片时）")
    args = p.parse_args()

    if not args.script.exists():
        logger.error(f"{args.script} not found")
        return

    parsed = parse_script(args.script)
    if not parsed:
        logger.error("No lines parsed")
        return

    logger.info(f"Parsed {len(parsed)} lines from {args.script.name}")
    asyncio.run(synthesize(
        parsed, args.output,
        backend=args.backend,
        voice=args.voice,
        rate=args.rate,
        gap_ms=args.gap,
        slide_gap_ms=args.slide_gap,
        voice_sample=args.voice_sample,
    ))


if __name__ == "__main__":
    main()
