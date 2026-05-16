# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "torch==2.3.1",
#   "torchaudio==2.3.1",
#   "conformer==0.3.2",
#   "diffusers==0.29.0",
#   "gdown==5.1.0",
#   "hydra-core==1.3.2",
#   "HyperPyYAML==1.2.3",
#   "inflect==7.3.1",
#   "librosa==0.10.2",
#   "lightning==2.2.4",
#   "matplotlib==3.7.5",
#   "modelscope==1.20.0",
#   "networkx==3.1",
#   "numpy==1.26.4",
#   "omegaconf==2.3.0",
#   "onnx==1.16.0",
#   "onnxruntime-gpu==1.18.0",
#   "openai-whisper==20231117",
#   "protobuf==4.25",
#   "pyarrow==18.1.0",
#   "pyworld==0.3.4",
#   "rich==13.7.1",
#   "soundfile==0.12.1",
#   "tensorboard==2.14.0",
#   "transformers==4.51.3",
#   "wetext==0.0.4",
#   "wget==3.2",
#   "x-transformers==2.11.24",
#   "huggingface_hub",
# ]
#
# [tool.uv]
# extra-index-url = ["https://download.pytorch.org/whl/cu121"]
# ///
"""
test_cosyvoice.py — CosyVoice 声音克隆快速测试
================================================
直接本地加载模型，用 voice-sample.wav 克隆声音，合成 3 段测试音频。
不依赖 FastAPI server，适合快速验证克隆效果。

用法:
  uv run test_cosyvoice.py
  uv run test_cosyvoice.py --model CosyVoice2-0.5B
  uv run test_cosyvoice.py --model Fun-CosyVoice3-0.5B
"""

import os
import sys
import time
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────────
VOICE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = VOICE_DIR.parent / "scripts"
PROJECT_ROOT = VOICE_DIR.parents[3]  # textbook-rag/
COSYVOICE_DIR = PROJECT_ROOT / ".github" / "CosyVoice"

# CUDA DLL 搜索路径（和 cosyvoice_server.py 保持一致）
_venv_torch_lib = PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "torch" / "lib"
if _venv_torch_lib.exists():
    os.add_dll_directory(str(_venv_torch_lib))

sys.path.insert(0, str(COSYVOICE_DIR))
sys.path.insert(0, str(COSYVOICE_DIR / "third_party" / "Matcha-TTS"))

# ── 参考音频 ──────────────────────────────────────────────────
VOICE_SAMPLE = VOICE_DIR / "voice-sample.wav"
PROMPT_TEXT = "而在天气仍有些微热的夏末，这种深色系新装并不为消费者买账。"

# ── 测试文本（覆盖不同场景）──────────────────────────────────
TEST_SENTENCES = [
    # 短句：基本音色测试
    "你好，欢迎来到加拿大新移民频道。",
    # 中句：信息密度+数字
    "2026年，Express Entry的CRS分数线稳定在507到515分之间，比去年略有上升。",
    # 长句：叙事语气+逻辑链
    "很多新移民不知道，到了加拿大的第一件事，不是找房子，不是办银行卡，而是先申请一个SIN号码，因为没有它，你连工资都拿不到。",
]


def main():
    import argparse

    p = argparse.ArgumentParser(description="CosyVoice 声音克隆快速测试")
    p.add_argument("--model", default="CosyVoice2-0.5B",
                   choices=["CosyVoice2-0.5B", "Fun-CosyVoice3-0.5B", "CosyVoice-300M"],
                   help="模型版本")
    args = p.parse_args()

    # ── 检查模型 ──────────────────────────────────────────
    model_dir = COSYVOICE_DIR / "pretrained_models" / args.model
    if not model_dir.exists():
        print(f"[ERROR] 模型未下载: {model_dir}")
        print(f"  请先运行: uv run cosyvoice_server.py --model {args.model}")
        print(f"  或手动下载: huggingface-cli download FunAudioLLM/{args.model}")
        sys.exit(1)

    if not VOICE_SAMPLE.exists():
        print(f"[ERROR] 参考音频不存在: {VOICE_SAMPLE}")
        sys.exit(1)

    # ── 输出目录 ──────────────────────────────────────────
    out_dir = VOICE_DIR / "samples_cosyvoice"
    out_dir.mkdir(exist_ok=True)

    # ── 加载模型 ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  CosyVoice 声音克隆测试")
    print(f"  模型: {args.model}")
    print(f"  参考音频: {VOICE_SAMPLE.name}")
    print(f"  输出目录: {out_dir}")
    print(f"{'='*60}\n")

    print("[1/4] 加载模型...")
    t0 = time.time()
    from cosyvoice.cli.cosyvoice import AutoModel
    import torchaudio

    cosyvoice = AutoModel(model_dir=str(model_dir))
    print(f"  ✓ 模型加载完成 ({time.time() - t0:.1f}s)")
    print(f"  采样率: {cosyvoice.sample_rate}")

    # ── 注册说话人（缓存音色向量，后续合成更快）──────────
    print("\n[2/4] 注册说话人音色...")
    t0 = time.time()
    try:
        ok = cosyvoice.add_zero_shot_spk(
            PROMPT_TEXT,
            str(VOICE_SAMPLE),
            "test_spk"
        )
        print(f"  ✓ 说话人注册成功 ({time.time() - t0:.1f}s)")
    except Exception as e:
        print(f"  ✗ 注册失败: {e}")
        print("  将使用实时模式（每次传参考音频）")
        ok = False

    # ── 逐句合成测试 ──────────────────────────────────────
    print(f"\n[3/4] 合成 {len(TEST_SENTENCES)} 段测试音频...\n")
    import torch

    results = []
    for i, text in enumerate(TEST_SENTENCES):
        label = ["短句", "中句", "长句"][i]
        print(f"  [{i+1}/{len(TEST_SENTENCES)}] {label}: {text[:30]}...")
        t0 = time.time()

        # 优先用缓存说话人（更快）
        if ok:
            chunks = list(cosyvoice.inference_zero_shot(
                text, "", "", zero_shot_spk_id="test_spk", stream=False
            ))
        else:
            chunks = list(cosyvoice.inference_zero_shot(
                text, PROMPT_TEXT, str(VOICE_SAMPLE), stream=False
            ))

        if not chunks:
            print(f"    ✗ 合成失败!")
            continue

        speech = torch.cat([c['tts_speech'] for c in chunks], dim=1)
        duration = speech.shape[1] / cosyvoice.sample_rate
        elapsed = time.time() - t0
        rtf = elapsed / duration if duration > 0 else 0

        out_path = out_dir / f"test_{i+1}_{label}.wav"
        torchaudio.save(str(out_path), speech, cosyvoice.sample_rate)

        results.append({
            "label": label,
            "text": text,
            "duration": duration,
            "elapsed": elapsed,
            "rtf": rtf,
            "path": out_path,
        })
        print(f"    ✓ {duration:.1f}s 音频, 耗时 {elapsed:.1f}s (RTF={rtf:.2f})")
        print(f"    → {out_path.name}")

    # ── 汇总 ──────────────────────────────────────────────
    print(f"\n[4/4] 测试汇总\n")
    print(f"{'─'*60}")
    print(f"  {'类型':<6} {'音频时长':>8} {'合成耗时':>8} {'RTF':>6}  文件")
    print(f"{'─'*60}")
    for r in results:
        print(f"  {r['label']:<6} {r['duration']:>7.1f}s {r['elapsed']:>7.1f}s {r['rtf']:>5.2f}  {r['path'].name}")
    print(f"{'─'*60}")

    if results:
        avg_rtf = sum(r["rtf"] for r in results) / len(results)
        total_audio = sum(r["duration"] for r in results)
        total_time = sum(r["elapsed"] for r in results)
        print(f"\n  总音频: {total_audio:.1f}s | 总耗时: {total_time:.1f}s | 平均 RTF: {avg_rtf:.2f}")
        print(f"\n  输出目录: {out_dir}")
        print(f"  请播放 WAV 文件听效果，重点关注:")
        print(f"    1. 音色相似度 — 和你的 voice-sample.wav 像不像")
        print(f"    2. 韵律自然度 — 停顿、语调是否自然")
        print(f"    3. 数字/英文 — CRS、Express Entry 等是否正确发音")
        print(f"    4. 尾部噪声 — 有没有多余的喘息/电流声")


if __name__ == "__main__":
    main()
