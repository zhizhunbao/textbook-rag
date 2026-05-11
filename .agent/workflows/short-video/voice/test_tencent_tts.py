# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "tencentcloud-sdk-python",
#   "loguru",
#   "python-dotenv",
# ]
# ///
"""
test_tencent_tts.py — 测试腾讯云 TTS 预置音色
================================================
用法:
  uv run test_tencent_tts.py

音色来源: https://cloud.tencent.com/document/product/1073/34112
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

import os

TEST_TEXT = "大家好，欢迎来到今天的节目。我们今天要聊一聊加拿大快速通道移民的评分标准，帮你搞清楚CRS到底怎么算。"

# 腾讯云 TTS 热门音色（VoiceType ID）
# 完整列表: https://cloud.tencent.com/document/product/1073/92668
VOICES = {
    # 精品音色（免费 800 万字）
    "智瑜_温柔女声":       101001,
    "智聆_亲和女声":       101002,
    "智美_客服女声":       101003,
    "智云_通用男声":       101004,
    "智莉_亲和女声":       101005,
    "智言_险沉稳男声":     101006,
    "智娜_广告女声":       101007,
    "智琪_温柔女声":       101008,
    "智芸_知性女声":       101009,
    "智华_新闻男声":       101010,
    # 大模型音色（免费 10 万字）
    "智逍遥_广播男声":     301000,
    "智灵儿_甜美女声":     301001,
    "智小柔_温柔女声":     301015,
    "智小刚_阳刚男声":     301012,
}


def main():
    secret_id = os.environ.get("SecretId", "")
    secret_key = os.environ.get("SecretKey", "")
    if not secret_id or not secret_key:
        logger.error("请在 .env 中设置 SecretId 和 SecretKey")
        return

    from tencentcloud.common import credential
    from tencentcloud.tts.v20190823 import tts_client, models

    cred = credential.Credential(secret_id, secret_key)
    client = tts_client.TtsClient(cred, "ap-shanghai")

    out_dir = Path(__file__).parent / "samples_tencent"
    out_dir.mkdir(exist_ok=True)

    results = []

    for label, voice_type in VOICES.items():
        logger.info(f"Generating: {label} (VoiceType={voice_type})...")

        try:
            req = models.TextToVoiceRequest()
            req.Text = TEST_TEXT
            req.SessionId = f"test_{voice_type}"
            req.VoiceType = voice_type
            req.Volume = 5       # 音量 [-10, 10]
            req.Speed = 0        # 语速 [-2, 6]
            req.Codec = "mp3"

            t0 = time.time()
            resp = client.TextToVoice(req)
            elapsed = time.time() - t0

            # 解码 Base64 音频
            audio = base64.b64decode(resp.Audio)

            # 保存 WAV（通过 ffmpeg 转换）
            mp3_file = out_dir / f"{voice_type}_{label}.mp3"
            wav_file = out_dir / f"{voice_type}_{label}.wav"

            with open(mp3_file, "wb") as f:
                f.write(audio)

            import subprocess
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3_file), str(wav_file)],
                capture_output=True,
            )
            if wav_file.exists():
                mp3_file.unlink(missing_ok=True)

            size_kb = len(audio) / 1024

            results.append({
                "label": label,
                "voice_type": voice_type,
                "size": f"{size_kb:.0f}KB",
                "gen_time": f"{elapsed:.1f}s",
                "status": "✅",
            })
            logger.success(f"  {label}: {size_kb:.0f}KB in {elapsed:.1f}s")

        except Exception as e:
            results.append({
                "label": label,
                "voice_type": voice_type,
                "size": "-",
                "gen_time": "-",
                "status": f"❌ {e}",
            })
            logger.error(f"  {label}: {e}")

    # 汇总
    logger.info("\n" + "=" * 75)
    logger.info("📊 腾讯云 TTS Test Results")
    logger.info("=" * 75)
    logger.info(f"{'音色':<20} {'VoiceType':<12} {'大小':<10} {'耗时':<10} {'状态'}")
    logger.info("-" * 75)
    for r in results:
        logger.info(
            f"{r['label']:<20} {r['voice_type']:<12} {r['size']:<10} "
            f"{r['gen_time']:<10} {r['status']}"
        )
    logger.info("=" * 75)
    logger.info(f"🎧 试听文件已保存到: {out_dir}")
    logger.info("💡 精品音色(10xxxx) 免费800万字; 大模型音色(30xxxx) 免费10万字")


if __name__ == "__main__":
    main()
