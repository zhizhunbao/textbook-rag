# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "qwen-tts",
#   "soundfile",
#   "torch",
#   "torchaudio",
#   "loguru",
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
test_qwen_preset.py — 测试 Qwen3-TTS 所有内置音色
====================================================
不做语音克隆，直接用 CustomVoice 模型的预置 speaker。

用法:
  uv run test_qwen_preset.py

输出:
  voice/samples/ 目录下生成每个 speaker 的试听 WAV 文件

已知内置 Speaker:
  中文: Vivian, Serena, Uncle_Fu, Dylan, Eric
  英文: Ryan, Aiden
  日语: Ono_Anna
  韩语: Sohee
"""

from __future__ import annotations

import time
from pathlib import Path

import soundfile as sf
from loguru import logger


# 测试用文本（中文 + 英文各一句）
TEST_TEXTS = {
    "zh": "大家好，欢迎来到今天的节目。我们今天要聊一聊加拿大快速通道移民的评分标准。",
    "en": "Hello everyone, welcome to today's program. Let's talk about the Express Entry scoring system.",
}


def main():
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

    out_dir = Path(__file__).parent / "samples"
    out_dir.mkdir(exist_ok=True)

    # ── 加载 CustomVoice 模型（0.6B，比 Base 1.7B 小很多，推理更快） ──
    logger.info("Loading Qwen3-TTS-12Hz-0.6B-CustomVoice model...")
    t0 = time.time()
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        device_map="cuda:0",
        dtype="auto",
    )
    logger.info(f"Model loaded in {time.time() - t0:.1f}s")

    # ── 获取所有可用 speaker ──
    try:
        speakers = model.get_supported_speakers()
        logger.info(f"Available speakers: {speakers}")
    except Exception:
        # 如果 API 不存在，手动列出已知 speakers
        speakers = [
            "Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric",
            "Ryan", "Aiden", "Ono_Anna", "Sohee",
        ]
        logger.warning(f"get_supported_speakers() not available, using known list: {speakers}")

    # ── 逐个 speaker 生成试听 ──
    results = []
    for spk in speakers:
        # 根据 speaker 名字猜测最佳语言
        if spk in ("Ryan", "Aiden"):
            lang, text = "English", TEST_TEXTS["en"]
        elif spk == "Ono_Anna":
            lang, text = "Japanese", "こんにちは、今日は天気がいいですね。"
        elif spk == "Sohee":
            lang, text = "Korean", "안녕하세요, 오늘 프로그램에 오신 것을 환영합니다."
        else:
            lang, text = "Chinese", TEST_TEXTS["zh"]

        out_file = out_dir / f"{spk}_{lang.lower()}.wav"
        logger.info(f"Generating: {spk} ({lang})...")

        try:
            t1 = time.time()
            wavs, sr = model.generate_custom_voice(
                text=text, speaker=spk, language=lang,
            )
            elapsed = time.time() - t1

            sf.write(str(out_file), wavs[0], sr)
            dur = len(wavs[0]) / sr
            rtf = elapsed / dur if dur > 0 else 0

            results.append({
                "speaker": spk,
                "language": lang,
                "file": out_file.name,
                "duration": f"{dur:.1f}s",
                "gen_time": f"{elapsed:.1f}s",
                "rtf": f"{rtf:.2f}",
                "status": "✅",
            })
            logger.success(f"  {spk}: {dur:.1f}s audio in {elapsed:.1f}s (RTF={rtf:.2f})")

        except Exception as e:
            results.append({
                "speaker": spk,
                "language": lang,
                "file": "-",
                "duration": "-",
                "gen_time": "-",
                "rtf": "-",
                "status": f"❌ {e}",
            })
            logger.error(f"  {spk}: {e}")

    # ── 也用中文测试英文 speaker（看跨语言效果） ──
    for spk in ("Ryan", "Aiden"):
        out_file = out_dir / f"{spk}_chinese.wav"
        logger.info(f"Cross-lang test: {spk} speaking Chinese...")
        try:
            t1 = time.time()
            wavs, sr = model.generate_custom_voice(
                text=TEST_TEXTS["zh"], speaker=spk, language="Chinese",
            )
            elapsed = time.time() - t1
            sf.write(str(out_file), wavs[0], sr)
            dur = len(wavs[0]) / sr
            logger.success(f"  {spk} (Chinese): {dur:.1f}s in {elapsed:.1f}s")
            results.append({
                "speaker": f"{spk} (cross-lang CN)",
                "language": "Chinese",
                "file": out_file.name,
                "duration": f"{dur:.1f}s",
                "gen_time": f"{elapsed:.1f}s",
                "rtf": f"{elapsed/dur:.2f}" if dur > 0 else "-",
                "status": "✅",
            })
        except Exception as e:
            logger.error(f"  {spk} cross-lang: {e}")

    # ── 打印汇总 ──
    logger.info("\n" + "=" * 70)
    logger.info("📊 Preset Voice Test Results")
    logger.info("=" * 70)
    logger.info(f"{'Speaker':<25} {'Lang':<10} {'Duration':<10} {'GenTime':<10} {'RTF':<8} {'Status'}")
    logger.info("-" * 70)
    for r in results:
        logger.info(
            f"{r['speaker']:<25} {r['language']:<10} {r['duration']:<10} "
            f"{r['gen_time']:<10} {r['rtf']:<8} {r['status']}"
        )
    logger.info("=" * 70)
    logger.info(f"🎧 试听文件已保存到: {out_dir}")


if __name__ == "__main__":
    main()
