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
#   "requests",
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
独立工具脚本：script.txt → narration.wav + timestamps.json

用法:
  uv run synthesize.py --script ./script.txt --output ./narration/
  uv run synthesize.py --script ./script.txt --output ./narration/ --backend edge
  uv run synthesize.py --script ./script.txt --output ./narration/ --backend moss --voice-sample ./voice.wav
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from loguru import logger


# ── Config ──────────────────────────────────────────────────

import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parents[3]  # textbook-rag/
DEFAULT_VOICE_SAMPLE = SCRIPTS_DIR.parent / "voice" / "voice-sample.wav"
DEFAULT_PROMPT_TEXT = "而在天气仍有些微热的夏末，这种深色系新装并不为消费者买账。"
MOSS_REPO = PROJECT_ROOT / ".github" / "references" / "MOSS-TTS-Nano"
COSYVOICE_DIR = PROJECT_ROOT / ".github" / "CosyVoice"


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


def parse_storyline(path: Path) -> list[dict]:
    """解析 storyline.md 为结构化列表。

    从 **台词**: 块中提取逐行台词，用 ## [type] 标题识别 slide 分界。
    跳过 📋 引用来源汇总 section。
    """
    text = path.read_text(encoding="utf-8")
    parsed = []
    current_slide = ""
    in_narration = False
    is_first_line_of_slide = True  # 当前 slide 的第一句台词

    # 截断：遇到引用来源汇总就停止
    summary_match = re.search(r"^## 📋", text, re.MULTILINE)
    if summary_match:
        text = text[:summary_match.start()]

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        # 检测 slide 标题: ## [type] 显示标题
        slide_match = re.match(r"^##\s+\[(.+?)\]\s*(.*)", stripped)
        if slide_match:
            current_slide = slide_match.group(2).strip() or slide_match.group(1)
            in_narration = False
            is_first_line_of_slide = True
            continue

        # 检测台词开始标记
        if stripped.startswith("**台词**:") or stripped.startswith("**台词：**"):
            in_narration = True
            # 检查同行是否有内容 (如 "**台词**: 第一句话")
            after = re.sub(r"^\*\*台词\*\*[：:]", "", stripped).strip()
            if after:
                parsed.append({
                    "chapter": current_slide,
                    "narration": after,
                    "visual_hint": "",
                    "line_idx": len(parsed),
                    "is_slide_start": is_first_line_of_slide,
                })
                is_first_line_of_slide = False
            continue

        # 台词区结束条件: 空行 / 新的 ** 字段 / --- 分隔
        if in_narration:
            if not stripped or stripped.startswith("---") or (
                stripped.startswith("**") and not stripped.startswith("**台词")
            ):
                in_narration = False
                continue
            # 跳过 markdown 格式行
            if stripped.startswith("|") or stripped.startswith("#"):
                in_narration = False
                continue
            # 有效台词行
            parsed.append({
                "chapter": current_slide,
                "narration": stripped,
                "visual_hint": "",
                "line_idx": len(parsed),
                "is_slide_start": is_first_line_of_slide,
            })
            is_first_line_of_slide = False

    logger.info(f"[Storyline] Parsed {len(parsed)} narration lines from {path.name}")
    return parsed


# ── TTS Text Preprocessing ─────────────────────────────────

# 中文标点集合
_CN_PUNCT_SENTENCE = '。？！；：'
_CN_PUNCT_CLAUSE = '，、'
_CN_PUNCT_PAIR = '""''（）《》【】'
_DASH_PATTERNS = ['——', '—', '──', '--']
_MAX_SEGMENT_CHARS = 18  # ai-video-director R1 规则: 标点间最大中文字数


def _clean_for_subtitle(text: str) -> str:
    """清洗文本用于字幕显示（非 TTS 输入）。

    - 句末标点（。？！；：）→ 去掉
    - 配对标点（引号/括号）→ 去掉
    - 保留逗号和顿号 → 保持字幕可读性
    - 连续空格 → 单个空格
    """
    # 句末标点 → 去掉
    text = re.sub(f'[{_CN_PUNCT_SENTENCE}]', '', text)
    # 配对标点 → 去掉
    text = re.sub(f'[{_CN_PUNCT_PAIR}]', '', text)
    # 连续空格 → 单个
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _count_cn_chars(text: str) -> int:
    """统计纯中文字符数。"""
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def _precheck_text(lines: list[str]) -> None:
    """合成前文本质检（参考 ai-video-director check_script.py）。

    检查维度:
    - R1: 标点间中文字符 ≤ 18（防止一口气念完）
    - R2: 禁止破折号（TTS 停顿不稳定）
    - 句长: 超过 50 字符警告（TTS 韵律崩坏风险）
    - 标点密度: 无标点的长句警告
    """
    issues = 0
    for i, line in enumerate(lines, 1):
        # R2: 破折号检查
        for dash in _DASH_PATTERNS:
            if dash in line:
                logger.warning(f"  [PreCheck L{i}] 含破折号「{dash}」，TTS 停顿不稳定: {line[:40]}...")
                issues += 1

        # 句长检查
        if len(line) > 50:
            logger.warning(f"  [PreCheck L{i}] 句长 {len(line)} 字符(>50)，TTS 韵律可能崩坏: {line[:40]}...")
            issues += 1

        # R1: 标点间字数检查
        segments = re.split(f'[{_CN_PUNCT_SENTENCE}{_CN_PUNCT_CLAUSE}]', line)
        for seg in segments:
            seg = seg.strip()
            cn_count = _count_cn_chars(seg)
            if cn_count < 3:  # 纯英文段落豁免
                continue
            if cn_count > _MAX_SEGMENT_CHARS:
                logger.warning(
                    f"  [PreCheck L{i}] 标点间 {cn_count} 中文字(>{_MAX_SEGMENT_CHARS})，"
                    f"需加逗号: 「{seg[:30]}...」"
                )
                issues += 1

        # 无标点检查: 长句无任何中文标点
        has_punct = bool(re.search(f'[{_CN_PUNCT_SENTENCE}{_CN_PUNCT_CLAUSE}]', line))
        if not has_punct and _count_cn_chars(line) > 12:
            logger.warning(f"  [PreCheck L{i}] 无标点的长中文句，TTS 无换气点: {line[:40]}...")
            issues += 1

    if issues:
        logger.warning(f"[PreCheck] 发现 {issues} 个 TTS 质量风险，建议修改台词后重新合成")
    else:
        logger.info(f"[PreCheck] {len(lines)} 行台词质检通过 ✓")


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


def _synth_tencent_clone(client, text: str, out: Path, fast_voice_type: str):
    """腾讯云 TTS 声音复刻合成 → mp3。

    使用 VoiceType=200000000 + FastVoiceType 调用复刻音色。
    FastVoiceType 由 register_voice.py 注册后获得。
    """
    import base64
    from tencentcloud.tts.v20190823 import models

    req = models.TextToVoiceRequest()
    req.Text = text
    req.SessionId = f"clone_{hash(text) & 0xFFFFFF:06x}"
    req.VoiceType = 200000000       # 固定值：声音复刻模式
    req.FastVoiceType = fast_voice_type  # register_voice.py 返回的音色 ID
    req.Volume = 5
    req.Speed = 0
    req.Codec = "mp3"

    resp = client.TextToVoice(req)
    audio = base64.b64decode(resp.Audio)

    with open(out, "wb") as f:
        f.write(audio)


# ── Volcano Engine TTS V3 Backend ──────────────────────────

VOLC_V3_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"


def _init_volcano_creds() -> dict:
    """加载火山引擎 TTS 凭证（仅调用一次）。"""
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[4] / ".env"
    load_dotenv(env_path)

    api_key = os.environ.get("VOLC_TTS_API_KEY", "")
    appid = os.environ.get("VOLC_TTS_APPID", "")
    token = os.environ.get("VOLC_TTS_TOKEN", "")
    if not api_key and (not appid or not token):
        raise RuntimeError(
            f"Volcano TTS 凭证未设置。请在 {env_path} 中设置:\n"
            "  VOLC_TTS_API_KEY=你的APIKey  (推荐)\n"
            "  或 VOLC_TTS_APPID + VOLC_TTS_TOKEN (旧版)"
        )
    return {"api_key": api_key, "appid": appid, "token": token}


def _synth_volcano(
    creds: dict,
    text: str,
    out: Path,
    voice_type: str = "zh_female_mizai_uranus_bigtts",
    enable_subtitle: bool = False,
    speech_rate: int = 0,
) -> list[dict]:
    """火山引擎 TTS V3 HTTP Chunked 单向流式合成 → mp3。

    Returns:
        subtitles — 字幕列表（enable_subtitle=True 时有值）
    """
    import requests

    # 判断模型版本: _uranus_ → 2.0, 其他 → 1.0
    resource_id = "seed-tts-2.0" if "_uranus_" in voice_type else "seed-tts-1.0"

    # 构建 Headers
    if creds["api_key"]:
        headers = {
            "X-Api-Key": creds["api_key"],
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }
    else:
        headers = {
            "X-Api-App-Id": creds["appid"],
            "X-Api-Access-Key": creds["token"],
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }

    # 构建 Body
    payload = {
        "user": {"uid": "synth_pipeline"},
        "req_params": {
            "text": text,
            "speaker": voice_type,
            "audio_params": {
                "format": "wav",
                "sample_rate": 24000,
                "speech_rate": speech_rate,
            },
        },
    }
    if enable_subtitle and resource_id == "seed-tts-2.0":
        payload["req_params"]["audio_params"]["enable_subtitle"] = True

    # 流式请求
    resp = requests.post(VOLC_V3_URL, headers=headers, json=payload, stream=True, timeout=60)
    if resp.status_code != 200:
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        raise RuntimeError(f"Volcano TTS HTTP {resp.status_code}: {body}")

    # 解析流式 chunked 响应
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
        if code == 20000000:  # 合成结束 OK
            break
        if code != 0:
            msg = chunk.get("message", str(chunk))
            raise RuntimeError(f"Volcano TTS API error {code}: {msg}")

        data = chunk.get("data")
        if data:
            audio_chunks.append(base64.b64decode(data))

        sentence = chunk.get("sentence")
        if sentence:
            subtitles.append(sentence)

    audio = b"".join(audio_chunks)
    if not audio:
        raise RuntimeError("Volcano TTS returned no audio data")

    # 自动检测: 如果前 4 字节是 RIFF 则已有 WAV header，否则是 raw PCM
    if audio[:4] == b"RIFF":
        # 已含 WAV header，直接写入
        with open(out, "wb") as f:
            f.write(audio)
    else:
        # Raw PCM (signed 16-bit LE, mono, 24kHz)，手动加 WAV header
        import wave
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio)
    logger.debug(f"[Volcano] {out.name}: {len(audio)} bytes, "
                 f"{'WAV' if audio[:4] == b'RIFF' else 'raw PCM'}")

    return subtitles


# ── CosyVoice Local Backend ─────────────────────────────────

COSYVOICE_URL = "http://127.0.0.1:9880"

def _synth_cosyvoice(text: str, out: Path) -> None:
    """CosyVoice 本地 TTS 合成 → wav。

    需要先启动 cosyvoice_server.py 服务。
    """
    import requests

    try:
        resp = requests.post(
            f"{COSYVOICE_URL}/tts",
            json={"text": text, "use_cached_spk": True},
            timeout=120,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        raise RuntimeError(
            "CosyVoice 服务未启动。请先运行:\n"
            "  uv run .agent/workflows/short-video/scripts/cosyvoice_server.py"
        )

    with open(out, "wb") as f:
        f.write(resp.content)


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


# ── Timestamp Post-processing ─────────────────────────────

def _split_multi_clause_timestamps(timestamps: list[dict]) -> list[dict]:
    """拆分多句 timestamp 条目为单句。

    规则: 在「中文/数字 + 空格 + 中文」处拆分（TTS 用空格替代标点）。
    英文词间空格保留不拆。时间按字数比例分配。
    """
    result = []
    idx = 1
    for ts in timestamps:
        clauses = _split_clauses(ts["text"])
        if len(clauses) <= 1:
            result.append({**ts, "index": idx})
            idx += 1
            continue
        # 按字数比例分配时间
        total_chars = sum(len(c) for c in clauses)
        duration = ts["end"] - ts["start"]
        t = ts["start"]
        for clause in clauses:
            ratio = len(clause) / total_chars
            clause_dur = ratio * duration
            result.append({
                "index": idx,
                "start": round(t, 3),
                "end": round(t + clause_dur, 3),
                "text": clause,
            })
            t += clause_dur
            idx += 1
    logger.info(f"[Split] {len(timestamps)} → {len(result)} subtitle entries")
    return result


def _split_clauses(text: str) -> list[str]:
    """在「中文/数字 + 空格 + 中文」处拆分。"""
    import re as _re
    marked = _re.sub(
        r'([\u4e00-\u9fff0-9])\s+([\u4e00-\u9fff])',
        '\\1\u2502\\2',
        text,
    )
    parts = [s.strip() for s in marked.split('\u2502') if s.strip()]
    # 合并过短的片段 (< 4 字) 到下一个
    merged = []
    for p in parts:
        if merged and len(merged[-1]) < 4:
            merged[-1] += p
        else:
            merged.append(p)
    return merged if merged else [text]


def _group_by_slide(parsed: list[dict]) -> list[list[dict]]:
    """将逐行台词按 slide 分组（用 is_slide_start 标志识别边界）。"""
    slides: list[list[dict]] = []
    current: list[dict] = []
    for item in parsed:
        if item.get("is_slide_start", False) and current:
            slides.append(current)
            current = []
        current.append(item)
    if current:
        slides.append(current)
    return slides


# ── Main Synthesis Pipeline ───────────────────────────────

async def synthesize(
    parsed: list[dict],
    out_dir: Path,
    backend: str = "volcano",
    voice: str = "zh_female_mizai_uranus_bigtts",
    rate: str = "-10%",
    speech_rate: int = 0,
    gap_ms: int = 300,
    slide_gap_ms: int = 800,
    fade_ms: int = 80,
    voice_sample: Path | None = None,
) -> Path:
    """逐句 TTS 合成 → 加呼吸间隔 → 淡入淡出过渡 → narration.wav + timestamps.json。

    v2 改进：
    - 所有后端统一逐句合成，句间插入 gap_ms 静音（"呼吸感"）
    - slide 切换处插入 slide_gap_ms 静音 + 前后 fade_ms 淡入淡出（消除"断档"）
    - 每段音频末尾截除 TTS 生成的尾部噪声/喘息（atrim + silenceremove）
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "temp_audio"
    tmp.mkdir(exist_ok=True)

    lines = [it["narration"] for it in parsed]
    logger.info(f"[TTS] {len(lines)} segments · {backend}")

    # CosyVoice: 模型只加载一次（直接推理，无需 FastAPI 服务）
    cosyvoice_model, cosyvoice_cached = None, False
    if backend == "cosyvoice":
        cosyvoice_model, cosyvoice_cached = _load_cosyvoice_model(
            prompt_wav=voice_sample,
        )

    # Qwen: 模型只加载一次
    qwen_model, qwen_mode, qwen_prompt = None, None, None
    if backend == "qwen":
        qwen_model, qwen_mode, qwen_prompt = _load_qwen_model(voice_sample)

    # Tencent: 客户端只初始化一次
    tencent_client = None
    if backend in ("tencent", "tencent-clone"):
        tencent_client = _init_tencent_client()

    # Volcano: 凭证只加载一次
    volcano_creds = None
    if backend == "volcano":
        volcano_creds = _init_volcano_creds()

    gap = gap_ms / 1000.0
    slide_gap = slide_gap_ms / 1000.0
    fade = fade_ms / 1000.0
    raw_ext = ".wav" if backend in ("volcano", "cosyvoice") else ".mp3"

    # ── 文本预检: 在花钱调 API 之前检查文本质量 ──
    _precheck_text(lines)

    # ── v2: 统一逐句合成（所有后端），句间呼吸，slide 间淡入淡出 ──
    slide_groups = _group_by_slide(parsed)
    logger.info(f"[TTS] Per-sentence synthesis: {len(lines)} lines in {len(slide_groups)} slides")

    for i, line in enumerate(lines):
        logger.info(f"  [{i+1}/{len(lines)}] {line[:50]}...")
        seg = tmp / f"raw_{i:03d}{raw_ext}"

        if backend == "cosyvoice":
            _synth_cosyvoice(cosyvoice_model, cosyvoice_cached, line, seg)
        elif backend == "volcano":
            _synth_volcano(volcano_creds, line, seg, voice_type=voice,
                           speech_rate=speech_rate)
        elif backend == "tencent-clone":
            _synth_tencent_clone(tencent_client, line, seg, fast_voice_type=voice)
        elif backend == "tencent":
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

    # ── 统一采样率 + 去尾部噪声/喘息 ──
    target_sr = 48000  # 24kHz × 2 = 整数倍重采样，无高频失真
    n_segments = len(lines)

    # 生成各类静音 WAV
    silence_slide = tmp / "silence_slide.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", f"{slide_gap:.3f}",
         "-c:a", "pcm_s16le", str(silence_slide)],
        capture_output=True,
    )
    silence_short = tmp / "silence_short.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r={target_sr}:cl=mono", "-t", f"{gap:.3f}",
         "-c:a", "pcm_s16le", str(silence_short)],
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

    # 归一化每段音频: 重采样 + 去头部呼吸声 + 去尾部喘息
    # 注意: 不在逐句阶段做音量归一化（loudnorm 会填充静音，dynaudnorm 会吞开头字）
    # 音量统一全交给合并后的全局 loudnorm
    HEAD_TRIM = 0.08  # 截掉开头 80ms（TTS 呼吸声区域，中文音节 ≥150ms 不受影响）
    MICRO_FADE = 0.03  # 30ms 微淡入，平滑截断边缘
    logger.info(f"[Concat] Processing {n_segments} segments: {target_sr}Hz + head trim {HEAD_TRIM*1000:.0f}ms...")
    for i in range(n_segments):
        seg_raw = tmp / f"raw_{i:03d}{raw_ext}"
        seg_norm = tmp / f"norm_{i:03d}.wav"
        # 重采样 + 截掉开头80ms呼吸声 + 去尾部喘息噪声
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(seg_raw),
             "-af", (
                 f"aresample={target_sr},"
                 # 固定截掉开头 80ms（呼吸声所在区域）
                 f"atrim=start={HEAD_TRIM},"
                 # 重置时间戳（atrim 后必须加，否则拼接时间错乱）
                 "asetpts=N/SR/TB,"
                 # areverse → silenceremove → areverse = 从尾部截静音
                 "areverse,silenceremove=1:0:-40dB,areverse"
             ),
             "-ac", "1", "-c:a", "pcm_s16le", str(seg_norm)],
            capture_output=True,
        )
        # 第二步: fade 处理
        # - 所有段: 30ms 微淡入（平滑截断边缘）
        # - slide 边界: 额外的长淡入/淡出
        is_slide_end = (i + 1 < len(parsed)
                        and parsed[i + 1].get("is_slide_start", False))
        is_slide_begin = parsed[i].get("is_slide_start", False) and i > 0
        fade_filters = []
        seg_dur = _get_duration(seg_norm)
        # 所有段都加微淡入
        fade_filters.append(f"afade=t=in:st=0:d={MICRO_FADE:.3f}")
        # slide 边界加长淡出/淡入
        if is_slide_end and seg_dur > fade:
            fade_filters.append(f"afade=t=out:st={max(0, seg_dur - fade):.3f}:d={fade:.3f}")
        if is_slide_begin and seg_dur > fade:
            fade_filters[0] = f"afade=t=in:st=0:d={fade:.3f}"
        seg_wav = tmp / f"seg_{i:03d}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(seg_norm),
             "-af", ",".join(fade_filters),
             "-c:a", "pcm_s16le", str(seg_wav)],
            capture_output=True,
        )

    # ── 计算时间戳（基于归一化后的实际时长） ──
    timestamps = []
    t = 0.15  # lead silence offset

    for i in range(len(lines)):
        seg_wav = tmp / f"seg_{i:03d}.wav"
        dur = _get_duration(seg_wav)
        timestamps.append({
            "index": i + 1,
            "start": round(t, 3),
            "end": round(t + dur, 3),
            "text": _clean_for_subtitle(lines[i]),
        })
        next_is_slide = (i + 1 < len(parsed)
                         and parsed[i + 1].get("is_slide_start", False))
        t += dur + (slide_gap if next_is_slide else gap)

    # ── 拼接 WAV ──
    concat_list = tmp / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write("file 'lead_silence.wav'\n")
        for i in range(n_segments):
            f.write(f"file 'seg_{i:03d}.wav'\n")
            if i < n_segments - 1:
                next_is_slide = parsed[i + 1].get("is_slide_start", False)
                sil = "silence_slide.wav" if next_is_slide else "silence_short.wav"
                f.write(f"file '{sil}'\n")
        # 结尾加 trail silence，避免最后一个字被截断
        f.write("file 'trail_silence.wav'\n")

    merged_wav = tmp / "merged.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(merged_wav)],
        capture_output=True,
    )

    # 全局 EBU R128 响度归一化（在完整音频上做，不会有短片段填充问题）
    out_audio = out_dir / "narration.wav"
    logger.info("[Concat] Applying global loudnorm (EBU R128 -16 LUFS) on merged audio...")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(merged_wav),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "pcm_s16le", str(out_audio)],
        capture_output=True,
    )
    if result.returncode != 0 or not out_audio.exists():
        logger.warning("[Concat] Global loudnorm failed, using raw merge")
        shutil.copy2(str(merged_wav), str(out_audio))

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

    # ── 拆分多句 timestamps 为单句条目 ──
    timestamps = _split_multi_clause_timestamps(timestamps)

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
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--script", type=Path, help="script.txt 路径 (旧格式)")
    group.add_argument("--storyline", type=Path, help="storyline.md 路径 (v16 格式)")
    p.add_argument("--output", type=Path, required=True, help="输出目录")
    p.add_argument("--backend", choices=["cosyvoice", "volcano", "tencent", "tencent-clone", "edge", "qwen", "moss", "hf"], default="cosyvoice")
    p.add_argument("--voice", default="zh_female_mizai_uranus_bigtts",
                   help="Volcano: voice_type; Tencent: VoiceType ID; Edge: voice name; CosyVoice: ignored")
    p.add_argument("--voice-sample", type=Path, default=None)
    p.add_argument("--rate", default="-10%", help="Edge TTS rate (e.g. '-10%%')")
    p.add_argument("--speech-rate", type=int, default=0,
                   help="Volcano TTS speech rate: -15=slightly slower, 0=normal, -50=half speed, 100=2x")
    p.add_argument("--gap", type=int, default=300, help="句间停顿 ms（同一张幻灯片内，制造呼吸感）")
    p.add_argument("--slide-gap", type=int, default=800, help="换页停顿 ms（切换幻灯片时）")
    p.add_argument("--fade", type=int, default=80, help="slide 边界淡入淡出 ms（消除断档感）")
    args = p.parse_args()

    input_path = args.storyline or args.script
    if not input_path.exists():
        logger.error(f"{input_path} not found")
        return

    if args.storyline:
        parsed = parse_storyline(args.storyline)
    else:
        parsed = parse_script(args.script)
    if not parsed:
        logger.error("No lines parsed")
        return

    logger.info(f"Parsed {len(parsed)} lines from {input_path.name}")
    asyncio.run(synthesize(
        parsed, args.output,
        backend=args.backend,
        voice=args.voice,
        rate=args.rate,
        speech_rate=args.speech_rate,
        gap_ms=args.gap,
        slide_gap_ms=args.slide_gap,
        fade_ms=args.fade,
        voice_sample=args.voice_sample,
    ))


if __name__ == "__main__":
    main()
