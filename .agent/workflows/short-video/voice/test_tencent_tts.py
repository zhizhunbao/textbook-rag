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

# 腾讯云 TTS 完整中文音色（VoiceType ID）
# 来源: https://cloud.tencent.com/document/product/1073/92668
VOICES = {
    # ── 超自然大模型音色（最高质量，中英文，24k）──
    "502001_智小柔_聊天女声":     502001,
    "502003_智小敏_聊天女声":     502003,
    "502004_智小满_营销女声":     502004,
    "502005_智小解_解说男声":     502005,
    "502006_智小悟_聊天男声":     502006,
    "502007_智小虎_聊天童声":     502007,
    "602003_爱小悠_聊天女声":     602003,
    "602004_暖心阿灿_聊天男声":   602004,
    "602005_专业梓欣_聊天女声":   602005,
    "603000_懂事少年_特色男声":   603000,
    "603001_潇湘妹妹_特色女声":   603001,
    "603002_软萌心心_特色男童声": 603002,
    "603003_随和老李_聊天男声":   603003,
    "603004_温柔小柠_聊天女声":   603004,
    "603005_知心大林_聊天男声":   603005,
    "603006_沉稳青叔_聊天男声":   603006,
    "603007_邻家女孩_聊天女声":   603007,
    # ── 大模型音色（高质量，24k）──
    "501000_智斌_阅读男声":       501000,
    "501001_智兰_资讯女声":       501001,
    "501002_智菊_阅读女声":       501002,
    "501003_智宇_阅读男声":       501003,
    "501004_月华_聊天女声":       501004,
    "501005_飞镜_聊天男声":       501005,
    "501006_千嶂_聊天男声":       501006,
    "501007_浅草_聊天男声":       501007,
    "601008_爱小豪_聊天男声":     601008,
    "601009_爱小芊_聊天女声":     601009,
    "601010_爱小娇_聊天女声":     601010,
    "601011_爱小川_聊天男声":     601011,
    "601012_爱小璟_特色女声":     601012,
    "601013_爱小伊_阅读女声":     601013,
    "601014_爱小简_聊天男声":     601014,
    # ── 精品音色（免费 800 万字，16k）──
    "101001_智瑜_情感女声":       101001,
    "101004_智云_通用男声":       101004,
    "101011_智燕_新闻女声":       101011,
    "101013_智辉_新闻男声":       101013,
    "101015_智萌_男童声":         101015,
    "101016_智甜_女童声":         101016,
    "101019_智彤_粤语女声":       101019,
    "101021_智瑞_新闻男声":       101021,
    "101026_智希_通用女声":       101026,
    "101027_智梅_通用女声":       101027,
    "101030_智柯_通用男声":       101030,
    "101054_智友_通用男声":       101054,
    "101055_智付_通用女声":       101055,
    # ── 旧版（可能已下线，兼容保留）──
    "301000_智逍遥_广播男声":     301000,
    "301001_智灵儿_甜美女声":     301001,
    "301012_智小刚_阳刚男声":     301012,
    "301015_智小柔_温柔女声":     301015,
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
