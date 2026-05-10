# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "edge-tts",
#   "loguru",
#   "qwen-tts",
#   "soundfile",
#   "torch",
#   "torchaudio",
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
        })
    return parsed


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


# ── Qwen3-TTS Backend ──────────────────────────────────────

def _load_qwen_model(voice_sample: Path | None = None):
    """加载 Qwen3-TTS 模型（仅加载一次）。"""
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

    if voice_sample and voice_sample.exists():
        logger.info(f"[Qwen] Loading Base model for voice cloning...")
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            device_map="cuda:0",
            dtype="auto",
        )
        logger.info(f"[Qwen] Extracting voice features from {voice_sample.name}...")
        voice_prompt = model.create_voice_clone_prompt(
            ref_audio=str(voice_sample),
            x_vector_only_mode=True,
        )
        return model, "clone", voice_prompt
    else:
        logger.info("[Qwen] Loading CustomVoice model (preset)...")
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
            device_map="cuda:0",
            torch_dtype="auto",
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

    timestamps = []
    t = 0.0
    gap = gap_ms / 1000.0

    for i, line in enumerate(lines):
        logger.info(f"  [{i+1}/{len(lines)}] {line[:35]}...")
        seg = tmp / f"seg_{i:03d}.mp3"

        if backend == "qwen":
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
            "text": line,
        })
        t += dur + gap

    # Merge segments with silence gaps (no re-encoding)
    silence = tmp / "silence.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         "anullsrc=r=44100:cl=mono", "-t", f"{gap:.3f}", str(silence)],
        capture_output=True,
    )

    # 前置静音，防止 MP3 编码器延迟截掉开头
    lead_silence = tmp / "lead_silence.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         "anullsrc=r=44100:cl=mono", "-t", "0.15", str(lead_silence)],
        capture_output=True,
    )

    concat_list = tmp / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write("file 'lead_silence.mp3'\n")  # 开头保护
        for i in range(len(lines)):
            f.write(f"file 'seg_{i:03d}.mp3'\n")
            if i < len(lines) - 1:
                f.write("file 'silence.mp3'\n")

    out_audio = out_dir / "narration.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(out_audio)],
        capture_output=True,
    )

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
    p.add_argument("--backend", choices=["moss", "edge", "hf", "qwen"], default="qwen")
    p.add_argument("--voice", default="zh-CN-YunxiNeural")
    p.add_argument("--voice-sample", type=Path, default=None)
    p.add_argument("--rate", default="-10%")
    p.add_argument("--gap", type=int, default=1000, help="句间停顿 ms")
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
        voice_sample=args.voice_sample,
    ))


if __name__ == "__main__":
    main()
