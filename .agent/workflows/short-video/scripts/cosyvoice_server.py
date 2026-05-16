# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "fastapi==0.115.6",
#   "uvicorn==0.30.0",
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
#   "pydantic==2.7.0",
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
cosyvoice_server.py — CosyVoice 本地 TTS 服务
================================================
启动一个 FastAPI 服务，提供零样本声音复刻 TTS。
模型加载一次，后续通过 HTTP 调用，避免每句话都重新加载模型。

用法:
  # 启动服务（首次会自动下载模型，约 1.5GB）
  uv run cosyvoice_server.py

  # 指定模型版本
  uv run cosyvoice_server.py --model CosyVoice2-0.5B
  uv run cosyvoice_server.py --model Fun-CosyVoice3-0.5B

  # 合成测试
  curl -X POST http://localhost:9880/tts -H "Content-Type: application/json" \
    -d '{"text": "你好世界", "prompt_text": "希望你以后能够做的比我还好呦。", "prompt_wav": "voice-sample.wav"}' \
    --output test.wav
"""


import argparse
import io
import os
import sys
import time
from pathlib import Path

# ── 路径设置 ──────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parents[3]  # textbook-rag/
COSYVOICE_DIR = PROJECT_ROOT / ".github" / "CosyVoice"

# ── CUDA DLL 搜索路径 ────────────────────────────────────
# uv 缓存环境的 torch 2.3.1 只带 cuDNN 8，但 onnxruntime-gpu 需要 cuDNN 9。
# 从主项目 .venv（torch 2.8+cu128）借用 cuDNN 9 DLL，必须在 ONNX 导入前注册。
_venv_torch_lib = PROJECT_ROOT / ".venv" / "Lib" / "site-packages" / "torch" / "lib"
if _venv_torch_lib.exists():
    os.add_dll_directory(str(_venv_torch_lib))

# 添加 CosyVoice 及其依赖到路径
sys.path.insert(0, str(COSYVOICE_DIR))
sys.path.insert(0, str(COSYVOICE_DIR / "third_party" / "Matcha-TTS"))


def main():
    p = argparse.ArgumentParser(description="CosyVoice 本地 TTS 服务")
    p.add_argument("--model", default="CosyVoice2-0.5B",
                   choices=["CosyVoice2-0.5B", "Fun-CosyVoice3-0.5B", "CosyVoice-300M"],
                   help="模型版本")
    p.add_argument("--port", type=int, default=9880, help="服务端口")
    p.add_argument("--host", default="127.0.0.1", help="监听地址")
    p.add_argument("--prompt-wav", type=Path,
                   default=SCRIPTS_DIR.parent / "voice" / "voice-sample.wav",
                   help="默认参考音频路径")
    p.add_argument("--prompt-text", default="而在天气仍有些微热的夏末，这种深色系新装并不为消费者买账。",
                   help="参考音频对应的文本")
    args = p.parse_args()

    # ── 下载模型 ─────────────────────────────────────────
    model_dir = COSYVOICE_DIR / "pretrained_models" / args.model
    if not model_dir.exists():
        print(f"[CosyVoice] 下载模型 {args.model}...")
        from huggingface_hub import snapshot_download
        snapshot_download(
            f"FunAudioLLM/{args.model}",
            local_dir=str(model_dir),
        )
        print(f"[CosyVoice] 模型已下载到: {model_dir}")

    # ── 加载模型 ─────────────────────────────────────────
    print(f"[CosyVoice] 加载模型 {args.model}...")
    t0 = time.time()

    from cosyvoice.cli.cosyvoice import AutoModel
    cosyvoice = AutoModel(model_dir=str(model_dir))
    print(f"[CosyVoice] 模型加载完成 ({time.time() - t0:.1f}s)")
    print(f"[CosyVoice] 采样率: {cosyvoice.sample_rate}")

    # ── 预热：注册说话人 ──────────────────────────────────
    if args.prompt_wav.exists():
        print(f"[CosyVoice] 预注册说话人: {args.prompt_wav.name}")
        try:
            cosyvoice.add_zero_shot_spk(
                args.prompt_text,
                str(args.prompt_wav),
                "default_spk"
            )
            print("[CosyVoice] 说话人注册成功: default_spk")
        except Exception as e:
            print(f"[CosyVoice] 说话人预注册失败（将使用实时模式）: {e}")

    # ── FastAPI 服务 ──────────────────────────────────────
    import torchaudio
    from fastapi import FastAPI
    from fastapi.responses import Response
    from pydantic import BaseModel

    app = FastAPI(title="CosyVoice TTS Server")

    class TTSRequest(BaseModel):
        text: str
        prompt_text: str = args.prompt_text
        prompt_wav: str = str(args.prompt_wav)
        use_cached_spk: bool = True  # 使用预注册的说话人（更快）

    @app.post("/tts")
    async def tts(req: TTSRequest):
        t0 = time.time()

        # 优先使用缓存的说话人（跳过参考音频编码，更快）
        if req.use_cached_spk:
            try:
                results = list(cosyvoice.inference_zero_shot(
                    req.text, "", "", zero_shot_spk_id="default_spk", stream=False
                ))
            except Exception:
                # 降级到实时模式
                results = list(cosyvoice.inference_zero_shot(
                    req.text, req.prompt_text, req.prompt_wav, stream=False
                ))
        else:
            results = list(cosyvoice.inference_zero_shot(
                req.text, req.prompt_text, req.prompt_wav, stream=False
            ))

        if not results:
            return Response(content="TTS failed", status_code=500)

        # 拼接所有 chunk
        import torch
        speech = torch.cat([r['tts_speech'] for r in results], dim=1)

        # 转 WAV bytes
        buf = io.BytesIO()
        torchaudio.save(buf, speech, cosyvoice.sample_rate, format="wav")
        wav_bytes = buf.getvalue()

        elapsed = time.time() - t0
        duration = speech.shape[1] / cosyvoice.sample_rate
        print(f"[TTS] '{req.text[:20]}...' → {duration:.1f}s audio in {elapsed:.1f}s (RTF={elapsed/duration:.2f})")

        return Response(content=wav_bytes, media_type="audio/wav")

    @app.get("/health")
    async def health():
        return {"status": "ok", "model": args.model, "sample_rate": cosyvoice.sample_rate}

    # ── 启动 ─────────────────────────────────────────────
    import uvicorn
    print(f"[CosyVoice] 服务启动: http://{args.host}:{args.port}")
    print(f"[CosyVoice] 健康检查: http://{args.host}:{args.port}/health")
    print(f"[CosyVoice] TTS 端点: POST http://{args.host}:{args.port}/tts")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
