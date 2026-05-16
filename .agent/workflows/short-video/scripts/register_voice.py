# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "tencentcloud-sdk-python",
#   "python-dotenv",
#   "loguru",
# ]
# ///
"""
register_voice.py — 腾讯云一句话声音复刻
=========================================
上传 voice-sample.wav → 音质检测 → 创建复刻任务 → 轮询 → 输出 VoiceType

用法:
  uv run register_voice.py
  uv run register_voice.py --sample ./my-voice.wav --name "我的音色"
  uv run register_voice.py --status <TaskId>   # 只查询已有任务状态

完成后会输出 FastVoiceType，在 synthesize.py 中使用：
  --backend tencent-clone --voice <FastVoiceType>
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ── 默认路径 ──────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_VOICE_SAMPLE = SCRIPTS_DIR.parent / "voice" / "voice-sample.wav"
ENV_PATH = Path(__file__).resolve().parents[4] / ".env"


def _init_vrs_client():
    """初始化腾讯云 VRS 客户端。"""
    load_dotenv(ENV_PATH)

    secret_id = os.environ.get("SecretId", "")
    secret_key = os.environ.get("SecretKey", "")
    if not secret_id or not secret_key:
        logger.error(f"SecretId/SecretKey not found in {ENV_PATH}")
        sys.exit(1)

    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.vrs.v20200824 import vrs_client

    cred = credential.Credential(secret_id, secret_key)
    http_profile = HttpProfile()
    http_profile.endpoint = "vrs.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return vrs_client.VrsClient(cred, "ap-guangzhou", client_profile)


def get_training_text(client) -> tuple[str, str]:
    """Step 0: 获取训练文本 → 返回 (TextId, Text)。

    TextId 有效期 7 天，且只能用一次。必须每次注册前重新获取。
    """
    from tencentcloud.vrs.v20200824 import models

    logger.info("[Step 0] 获取训练文本...")

    req = models.GetTrainingTextRequest()
    params = {"TaskType": 5}  # 5 = 一句话声音复刻
    req.from_json_string(json.dumps(params))

    resp = client.GetTrainingText(req)
    resp_dict = json.loads(resp.to_json_string())
    logger.info(f"[Step 0] Response: {json.dumps(resp_dict, ensure_ascii=False, indent=2)}")

    data = resp_dict.get("Data", resp_dict)
    text_list = data.get("TrainingTextList", [])
    if not text_list:
        logger.error("[Step 0] 未返回训练文本列表")
        sys.exit(1)

    text_id = text_list[0].get("TextId", "")
    training_text = text_list[0].get("Text", "")

    if not text_id:
        logger.error("[Step 0] 未返回 TextId")
        sys.exit(1)

    logger.success(f"[Step 0] TextId = {text_id}")
    logger.info(f"[Step 0] 训练文本: {training_text}")
    logger.warning("[Step 0] ⚠️ 请确保 voice-sample.wav 朗读的就是这段文本！")
    logger.warning("[Step 0]    如果不是，需要重新录制后再注册。")
    return text_id, training_text


def detect_audio_quality(client, audio_path: Path, text_id: str) -> str:
    """Step 1: 音质检测 → 返回 AudioId。

    一句话复刻要求：
    - 时长 5-15 秒
    - 文件 ≤ 2MB
    - 单声道 16bit WAV, 推荐 16kHz/24kHz
    """
    from tencentcloud.vrs.v20200824 import models

    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        sys.exit(1)

    # 检查文件大小
    size_mb = audio_path.stat().st_size / (1024 * 1024)
    if size_mb > 2.0:
        logger.warning(f"File size {size_mb:.1f}MB > 2MB limit. May be rejected.")

    # 读取 + Base64
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    logger.info(f"[Step 1] 音质检测: {audio_path.name} ({size_mb:.1f}MB)")

    req = models.DetectEnvAndSoundQualityRequest()
    params = {
        "TextId": text_id,
        "AudioData": audio_b64,
        "TypeId": 2,        # 2 = 音质检测
        "Codec": "wav",
        "SampleRate": 16000, # voice-sample.wav 默认 16kHz
        "TaskType": 5,       # 5 = 一句话声音复刻
    }
    req.from_json_string(json.dumps(params))

    resp = client.DetectEnvAndSoundQuality(req)
    resp_dict = json.loads(resp.to_json_string())
    logger.info(f"[Step 1] Response: {json.dumps(resp_dict, ensure_ascii=False, indent=2)}")

    # 提取 AudioId
    data = resp_dict.get("Data", resp_dict)
    audio_id = data.get("AudioId", "")
    detection_code = data.get("DetectionCode", -1)

    if detection_code != 0:
        detection_msg = data.get("DetectionMsg", "Unknown error")
        logger.error(f"[Step 1] 音质检测失败: code={detection_code}, msg={detection_msg}")
        sys.exit(1)

    logger.success(f"[Step 1] 音质检测通过! AudioId = {audio_id}")
    return audio_id


def create_vrs_task(client, audio_id: str, voice_name: str, voice_gender: int) -> str:
    """Step 2: 创建一句话声音复刻任务 → 返回 TaskId。"""
    from tencentcloud.vrs.v20200824 import models

    logger.info(f"[Step 2] 创建复刻任务: name={voice_name}, gender={'男' if voice_gender == 1 else '女'}")

    req = models.CreateVRSTaskRequest()
    params = {
        "SessionId": f"voice_clone_{int(time.time())}",
        "VoiceName": voice_name,
        "VoiceGender": voice_gender,   # 1=男, 2=女
        "VoiceLanguage": 1,            # 1=中文
        "AudioIdList": [audio_id],
        "TaskType": 5,                 # 5=一句话声音复刻
    }
    req.from_json_string(json.dumps(params))

    resp = client.CreateVRSTask(req)
    resp_dict = json.loads(resp.to_json_string())
    logger.info(f"[Step 2] Response: {json.dumps(resp_dict, ensure_ascii=False, indent=2)}")

    data = resp_dict.get("Data", resp_dict)
    task_id = data.get("TaskId", "")

    if not task_id:
        logger.error("[Step 2] 未返回 TaskId，任务创建失败")
        sys.exit(1)

    logger.success(f"[Step 2] 任务已创建! TaskId = {task_id}")
    return task_id


def poll_task_status(client, task_id: str, max_wait: int = 120) -> dict:
    """Step 3: 轮询任务状态，直到完成或超时。

    Status: 0=排队, 1=处理中, 2=成功, 3=失败
    """
    from tencentcloud.vrs.v20200824 import models

    logger.info(f"[Step 3] 等待任务完成... (最长 {max_wait}s)")

    start = time.time()
    while time.time() - start < max_wait:
        req = models.GetVRSTaskStatusRequest()
        params = {"TaskId": task_id}
        req.from_json_string(json.dumps(params))

        resp = client.GetVRSTaskStatus(req)
        resp_dict = json.loads(resp.to_json_string())

        data = resp_dict.get("Data", resp_dict)
        status = data.get("Status", -1)
        status_str = data.get("StatusStr", "Unknown")

        elapsed = int(time.time() - start)
        logger.info(f"  [{elapsed}s] Status={status} ({status_str})")

        if status == 2:  # 成功
            voice_type = data.get("VoiceType", "")
            logger.success(f"[Step 3] 声音复刻成功!")
            logger.success(f"  FastVoiceType = {voice_type}")
            logger.success(f"  在 synthesize.py 中使用:")
            logger.success(f"    --backend tencent-clone --voice {voice_type}")
            return data

        if status == 3:  # 失败
            error_msg = data.get("ErrorMsg", "Unknown error")
            logger.error(f"[Step 3] 声音复刻失败: {error_msg}")
            logger.info(f"Full response: {json.dumps(resp_dict, ensure_ascii=False, indent=2)}")
            sys.exit(1)

        time.sleep(5)

    logger.error(f"[Step 3] 超时 ({max_wait}s)，请稍后用 --status {task_id} 查询")
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(
        description="腾讯云一句话声音复刻 — 注册你的声音",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  uv run register_voice.py                              # 使用默认 voice-sample.wav
  uv run register_voice.py --sample ./my-voice.wav      # 自定义音频
  uv run register_voice.py --status abc123              # 查询已有任务
  uv run register_voice.py --gender 2 --name "小红"      # 女声 + 自定义名称
""",
    )
    p.add_argument("--sample", type=Path, default=DEFAULT_VOICE_SAMPLE,
                   help="参考音频 WAV (5-15秒, ≤2MB, 16kHz单声道)")
    p.add_argument("--name", default="我的复刻音色",
                   help="音色名称")
    p.add_argument("--gender", type=int, choices=[1, 2], default=1,
                   help="性别: 1=男, 2=女")
    p.add_argument("--status", metavar="TASK_ID",
                   help="查询已有任务状态（跳过检测和创建）")
    p.add_argument("--text-only", action="store_true",
                   help="只获取训练文本并保存TextId，不进行注册。录音后用 --text-id 继续。")
    p.add_argument("--text-id", metavar="TEXT_ID",
                   help="使用之前获取的TextId（跳过GetTrainingText）")
    p.add_argument("--max-wait", type=int, default=120,
                   help="最长等待时间(秒)")
    args = p.parse_args()

    client = _init_vrs_client()

    if args.status:
        # 仅查询模式
        poll_task_status(client, args.status, args.max_wait)
        return

    # Step 1: 获取训练文本
    if args.text_only:
        text_id, training_text = get_training_text(client)
        # 保存 TextId 到文件，方便下次使用
        text_id_file = args.sample.parent / "text-id.txt"
        with open(text_id_file, "w", encoding="utf-8") as f:
            f.write(f"{text_id}\n{training_text}\n")
        logger.success(f"TextId 已保存到: {text_id_file}")
        logger.success(f"")
        logger.success(f"📋 请朗读以下文本并录音:")
        logger.success(f"   「{training_text}」")
        logger.success(f"")
        logger.success(f"录好后保存为 WAV (16kHz单声道) 到: {args.sample}")
        logger.success(f"然后运行: uv run register_voice.py --text-id {text_id}")
        return

    # Step 2: 确定 TextId
    if args.text_id:
        text_id = args.text_id
        logger.info(f"使用指定的 TextId: {text_id}")
    else:
        # 自动获取新的（用户必须提前录好匹配音频）
        text_id, training_text = get_training_text(client)

    # 完整流程: 检测 → 创建 → 轮询
    audio_id = detect_audio_quality(client, args.sample, text_id)
    task_id = create_vrs_task(client, audio_id, args.name, args.gender)
    result = poll_task_status(client, task_id, args.max_wait)

    # 保存结果到 voice 目录
    result_file = args.sample.parent / "clone-result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存: {result_file}")


if __name__ == "__main__":
    main()
