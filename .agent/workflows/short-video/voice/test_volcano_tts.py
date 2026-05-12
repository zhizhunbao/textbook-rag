# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests",
#   "loguru",
#   "python-dotenv",
# ]
# ///
"""
test_volcano_tts.py — 测试火山引擎（豆包语音）TTS V3 API 预置音色
================================================================
已升级至 V3 HTTP Chunked 单向流式接口:
  https://openspeech.bytedance.com/api/v3/tts/unidirectional

用法:
  uv run test_volcano_tts.py                     # 测试全部 2.0 音色（精选）
  uv run test_volcano_tts.py --group 短视频       # 只测某个分组
  uv run test_volcano_tts.py --group 英文         # 只测英文
  uv run test_volcano_tts.py --model 1.0         # 测试 1.0 音色
  uv run test_volcano_tts.py --all               # 测试全部音色（2.0 + 1.0）

环境变量 (.env):
  VOLC_TTS_API_KEY=你的APIKey      (新版控制台，推荐)
  VOLC_TTS_APPID=你的AppID          (旧版控制台)
  VOLC_TTS_TOKEN=你的AccessToken    (旧版控制台)

音色来源: 豆包语音_音色列表_1778147509.pdf
API 文档: https://www.volcengine.com/docs/6561/1598757
"""

from __future__ import annotations

import base64
import json
import time
import uuid
import argparse
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv
from loguru import logger

# ── 加载 .env（向上 4 层） ────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[4] / ".env")

import os

# ── 测试文本 ─────────────────────────────────────────────────────────
TEST_TEXT = (
    "大家好，欢迎来到今天的节目。"
    "我们今天要聊一聊加拿大快速通道移民的评分标准，"
    "帮你搞清楚CRS到底怎么算。"
)

TEST_TEXT_EN = (
    "Hello everyone, welcome to today's episode. "
    "We're going to talk about Canada's Express Entry CRS scoring system, "
    "and help you figure out exactly how your score is calculated."
)

# ── V3 API 常量 ──────────────────────────────────────────────────────
API_V3_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
RESOURCE_ID_2_0 = "seed-tts-2.0"
RESOURCE_ID_1_0 = "seed-tts-1.0"

# ── 火山引擎 TTS 音色列表 ─────────────────────────────────────────────
# 格式: { "显示名_场景": ("voice_type", "语种", "性别", "模型版本") }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 豆包语音合成模型 2.0 音色  (resource_id = seed-tts-2.0)
# voice_type 后缀: _uranus_bigtts
# 支持: 情感变化、指令遵循、ASMR、字幕时间戳 (enable_subtitle)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICES_2_0 = {
    # ━━━ 通用场景 ━━━
    "Vivi_通用":              ("zh_female_vv_uranus_bigtts",                "zh", "女", "2.0"),
    "小何_通用":              ("zh_female_xiaohe_uranus_bigtts",            "zh", "女", "2.0"),
    "云舟_通用":              ("zh_male_m191_uranus_bigtts",                "zh", "男", "2.0"),
    "小天_通用":              ("zh_male_taocheng_uranus_bigtts",            "zh", "男", "2.0"),
    "刘飞_通用":              ("zh_male_liufei_uranus_bigtts",              "zh", "男", "2.0"),
    "魅力苏菲_通用":          ("zh_female_sophie_uranus_bigtts",            "zh", "女", "2.0"),
    "清新女声_通用":          ("zh_female_qingxinnvsheng_uranus_bigtts",    "zh", "女", "2.0"),
    "邻家女孩_通用":          ("zh_female_linjianvhai_uranus_bigtts",       "zh", "女", "2.0"),
    "邻家男孩_通用":          ("zh_male_linjiananhai_uranus_bigtts",        "zh", "男", "2.0"),
    "知性女声_通用":          ("zh_female_zhixingnv_uranus_bigtts",         "zh", "女", "2.0"),
    "温柔妈妈_通用":          ("zh_female_wenroumama_uranus_bigtts",        "zh", "女", "2.0"),
    "亲切女声_通用":          ("zh_female_qinqienv_uranus_bigtts",          "zh", "女", "2.0"),
    "俏皮女声_通用":          ("zh_female_qiaopinv_uranus_bigtts",          "zh", "女", "2.0"),
    "高冷沉稳_通用":          ("zh_male_gaolengchenwen_uranus_bigtts",      "zh", "男", "2.0"),
    "渊博小叔_通用":          ("zh_male_yuanboxiaoshu_uranus_bigtts",       "zh", "男", "2.0"),
    "阳光青年_通用":          ("zh_male_yangguangqingnian_uranus_bigtts",   "zh", "男", "2.0"),
    "儒雅青年_通用":          ("zh_male_ruyaqingnian_uranus_bigtts",        "zh", "男", "2.0"),
    "东方浩然_通用":          ("zh_male_dongfanghaoran_uranus_bigtts",      "zh", "男", "2.0"),
    "深夜播客_通用":          ("zh_male_shenyeboke_uranus_bigtts",          "zh", "男", "2.0"),
    "温柔小哥_通用":          ("zh_male_wenrouxiaoge_uranus_bigtts",        "zh", "男", "2.0"),

    # ━━━ 视频配音 ━━━
    "大壹_视频配音":          ("zh_male_dayi_uranus_bigtts",                "zh", "男", "2.0"),
    "流畅女声_视频配音":      ("zh_female_liuchangnv_uranus_bigtts",        "zh", "女", "2.0"),
    "儒雅逸辰_视频配音":      ("zh_male_ruyayichen_uranus_bigtts",          "zh", "男", "2.0"),
    "鸡汤女_视频配音":        ("zh_female_jitangnv_uranus_bigtts",          "zh", "女", "2.0"),

    # ━━━ 短视频/解说（重点） ━━━
    "解说小明_短视频":        ("zh_male_jieshuoxiaoming_uranus_bigtts",     "zh", "男", "2.0"),
    "磁性解说男声_短视频":    ("zh_male_cixingjieshuonan_uranus_bigtts",    "zh", "男", "2.0"),
    "广告解说_短视频":        ("zh_male_guanggaojieshuo_uranus_bigtts",     "zh", "男", "2.0"),
    "悬疑解说_短视频":        ("zh_male_xuanyijieshuo_uranus_bigtts",       "zh", "男", "2.0"),
    "鸡汤妹妹_短视频":       ("zh_female_jitangmei_uranus_bigtts",         "zh", "女", "2.0"),
    "心灵鸡汤_短视频":       ("zh_female_xinlingjitang_uranus_bigtts",     "zh", "女", "2.0"),
    "活力小哥_短视频":        ("zh_male_huolixiaoge_uranus_bigtts",         "zh", "男", "2.0"),

    # ━━━ 有声阅读 ━━━
    "霸气青叔_有声阅读":      ("zh_male_baqiqingshu_uranus_bigtts",         "zh", "男", "2.0"),

    # ━━━ 教育 ━━━
    "Tina老师_教育":         ("zh_female_yingyujiaoxue_uranus_bigtts",     "zh", "女", "2.0"),
    "少儿故事_教育":         ("zh_female_shaoergushi_uranus_bigtts",       "zh", "女", "2.0"),

    # ━━━ 特色 ━━━
    "译制片男_通用":          ("zh_male_yizhipiannan_uranus_bigtts",        "zh", "男", "2.0"),
    "TVB女声_通用":          ("zh_female_tvbnv_uranus_bigtts",              "zh", "女", "2.0"),
    "高冷御姐_通用":          ("zh_female_gaolengyujie_uranus_bigtts",      "zh", "女", "2.0"),
    "反卷青年_通用":          ("zh_male_fanjuanqingnian_uranus_bigtts",     "zh", "男", "2.0"),

    # ━━━ 英文 (2.0) ━━━
    "Tim_英文":              ("en_male_tim_uranus_bigtts",                 "en", "男", "2.0"),
    "Dacey_英文":            ("en_female_dacey_uranus_bigtts",             "en", "女", "2.0"),
    "Stokie_英文":           ("en_female_stokie_uranus_bigtts",            "en", "女", "2.0"),
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 豆包语音合成模型 1.0 音色  (resource_id = seed-tts-1.0)
# voice_type 后缀: _mars_bigtts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICES_1_0 = {
    # ━━━ 通用 ━━━
    "清新女声_v1":           ("zh_female_qingxin",                "zh", "女", "1.0"),
    "醇厚男声_v1":           ("zh_male_chunhou",                  "zh", "男", "1.0"),
    "知性女声_v1":           ("zh_female_zhixing",                "zh", "女", "1.0"),
    "亲切男声_v1":           ("zh_male_qinqie",                   "zh", "男", "1.0"),

    # ━━━ 新闻播报 ━━━
    "女主播_新闻_v1":         ("zh_female_zhubo",                  "zh", "女", "1.0"),
    "男主播_新闻_v1":         ("zh_male_zhubo",                    "zh", "男", "1.0"),

    # ━━━ 广告/短视频 ━━━
    "活力广告男声_v1":       ("zh_male_ad",                       "zh", "男", "1.0"),
    "磁性解说男声_v1":       ("zh_male_commentate",               "zh", "男", "1.0"),
    "影视解说_v1":           ("zh_male_xiaoming",                 "zh", "男", "1.0"),
    "悬疑解说_v1":           ("zh_male_changtianyi_xuanyi",       "zh", "男", "1.0"),

    # ━━━ 英文 ━━━
    "Adam_英文_v1":          ("en_male_adam",                     "en", "男", "1.0"),
    "Sarah_英文_v1":         ("en_female_sarah",                  "en", "女", "1.0"),
}


def synthesize_v3(
    text: str,
    voice_type: str,
    *,
    api_key: str = "",
    appid: str = "",
    token: str = "",
    resource_id: str = RESOURCE_ID_2_0,
    enable_subtitle: bool = False,
) -> tuple[bytes, list[dict]]:
    """调用火山引擎 TTS V3 HTTP Chunked 单向流式 API

    Returns:
        (audio_bytes, subtitles)  — 音频数据 + 字幕列表
    """

    # ── 构建 Headers ──
    if api_key:
        headers = {
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }
    elif appid and token:
        headers = {
            "X-Api-App-Id": appid,
            "X-Api-Access-Key": token,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }
    else:
        raise RuntimeError("No credentials: set VOLC_TTS_API_KEY or VOLC_TTS_APPID+VOLC_TTS_TOKEN")

    # ── 构建 Body ──
    payload = {
        "user": {"uid": "tts_test_user"},
        "req_params": {
            "text": text,
            "speaker": voice_type,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
            },
        },
    }

    # 2.0 音色支持字幕
    if enable_subtitle and resource_id == RESOURCE_ID_2_0:
        payload["req_params"]["audio_params"]["enable_subtitle"] = True

    # ── 流式请求 ──
    session = requests.Session()
    resp = session.post(API_V3_URL, headers=headers, json=payload, stream=True, timeout=60)

    if resp.status_code != 200:
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        raise RuntimeError(f"HTTP {resp.status_code}: {body}")

    # ── 解析流式 chunked 响应 ──
    audio_chunks: list[bytes] = []
    subtitles: list[dict] = []

    for line in resp.iter_lines():
        if not line:
            continue

        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue

        code = chunk.get("code", 0)

        # 20000000 = 合成结束 OK
        if code == 20000000:
            break

        # 非 0 且非 20000000 → 错误
        if code != 0:
            msg = chunk.get("message", str(chunk))
            raise RuntimeError(f"API error {code}: {msg}")

        # 音频数据
        data = chunk.get("data")
        if data:
            audio_chunks.append(base64.b64decode(data))

        # 字幕数据
        sentence = chunk.get("sentence")
        if sentence:
            subtitles.append(sentence)

    return b"".join(audio_chunks), subtitles


def main():
    parser = argparse.ArgumentParser(description="测试火山引擎 TTS V3 API 音色")
    parser.add_argument(
        "--group", type=str, default=None,
        help="只测某个分组关键词，如: 短视频, 通用, 英文, 教育, 视频配音 等",
    )
    parser.add_argument(
        "--model", type=str, default="2.0", choices=["2.0", "1.0"],
        help="选择模型版本: 2.0 (默认) 或 1.0",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="测试全部音色 (2.0 + 1.0)",
    )
    parser.add_argument(
        "--subtitle", action="store_true",
        help="启用字幕返回 (仅 2.0)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("VOLC_TTS_API_KEY", "")
    appid = os.environ.get("VOLC_TTS_APPID", "")
    token = os.environ.get("VOLC_TTS_TOKEN", "")

    if not api_key and (not appid or not token):
        logger.error(
            "请在 .env 中设置凭证:\n"
            "  VOLC_TTS_API_KEY=你的APIKey   (推荐)\n"
            "  或 VOLC_TTS_APPID + VOLC_TTS_TOKEN (旧版)"
        )
        return

    auth_mode = "API Key" if api_key else "AppID+Token"
    logger.info(f"🔑 鉴权方式: {auth_mode}")

    # ── 选择音色集 ──
    if args.all:
        voices = {**VOICES_2_0, **VOICES_1_0}
        logger.info("📋 测试全部音色 (2.0 + 1.0)")
    elif args.model == "1.0":
        voices = VOICES_1_0
        logger.info("📋 测试 1.0 音色")
    else:
        voices = VOICES_2_0
        logger.info("📋 测试 2.0 音色")

    # ── 按 group 过滤 ──
    if args.group:
        voices = {k: v for k, v in voices.items() if args.group in k}
        if not voices:
            logger.error(f"未找到包含 '{args.group}' 的音色")
            return
        logger.info(f"📋 筛选分组: '{args.group}'，共 {len(voices)} 个音色")

    out_dir = Path(__file__).parent / "samples_volcano"
    out_dir.mkdir(exist_ok=True)

    results = []

    for label, (voice_type, lang, gender, model_ver) in voices.items():
        text = TEST_TEXT_EN if lang == "en" else TEST_TEXT
        resource_id = RESOURCE_ID_2_0 if model_ver == "2.0" else RESOURCE_ID_1_0

        logger.info(f"🎙️  {label} (speaker={voice_type}, model={model_ver})...")

        try:
            t0 = time.time()
            audio, subtitles = synthesize_v3(
                text, voice_type,
                api_key=api_key, appid=appid, token=token,
                resource_id=resource_id,
                enable_subtitle=args.subtitle,
            )
            elapsed = time.time() - t0

            if not audio:
                raise RuntimeError("No audio data returned")

            # 保存 mp3 → 转 wav
            mp3_file = out_dir / f"{voice_type}_{label}.mp3"
            wav_file = out_dir / f"{voice_type}_{label}.wav"

            with open(mp3_file, "wb") as f:
                f.write(audio)

            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3_file), str(wav_file)],
                capture_output=True,
            )
            if wav_file.exists():
                mp3_file.unlink(missing_ok=True)

            size_kb = len(audio) / 1024

            # 字幕信息
            sub_info = ""
            if subtitles:
                sub_info = f" [{len(subtitles)} subs"
                total_words = sum(len(s.get("words", [])) for s in subtitles)
                if total_words:
                    sub_info += f", {total_words} words"
                sub_info += "]"

            results.append({
                "label": label,
                "speaker": voice_type,
                "gender": gender,
                "model": model_ver,
                "size": f"{size_kb:.0f}KB",
                "gen_time": f"{elapsed:.1f}s",
                "status": f"✅{sub_info}",
            })
            logger.success(f"  ✅ {size_kb:.0f}KB in {elapsed:.1f}s{sub_info}")

        except Exception as e:
            results.append({
                "label": label,
                "speaker": voice_type,
                "gender": gender,
                "model": model_ver,
                "size": "-",
                "gen_time": "-",
                "status": f"❌ {e}",
            })
            logger.error(f"  ❌ {e}")

    # ── 汇总 ──────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 100)
    logger.info("🌋 火山引擎 TTS V3 Test Results")
    logger.info("=" * 100)
    logger.info(
        f"{'音色':<25} {'speaker':<45} {'性别':<4} {'版本':<5} {'大小':<8} {'耗时':<8} {'状态'}"
    )
    logger.info("-" * 100)
    for r in results:
        logger.info(
            f"{r['label']:<25} {r['speaker']:<45} {r['gender']:<4} "
            f"{r['model']:<5} {r['size']:<8} {r['gen_time']:<8} {r['status']}"
        )
    logger.info("=" * 100)
    logger.info(f"🎧 试听文件已保存到: {out_dir}")
    ok = sum(1 for r in results if "✅" in r["status"])
    logger.info(f"📊 成功: {ok}/{len(results)}")


if __name__ == "__main__":
    main()
