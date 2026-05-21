# TTS 语音合成指南

> 本文档是 `workflow.md` Step 5 的详细参考。流程概要见 [workflow.md](../workflow.md)。

---

## TTS 友好规范（在 storyline.md 台词中遵守）

> ⚠️ **台词质量决定 TTS 质量。合成前自动质检，违规会警告。**

| # | 规则 | 罚则 | 示例 |
|---|------|------|------|
| R1 | **标点间 ≤18 个中文字** | 质检警告 | "这个分数线在跳，510分三月能上四月被刷" → 加逗号拆开 |
| R2 | **禁止破折号** `——` `--` | 质检警告 | "致命缺陷——" → 改逗号 |
| R3 | **每句 ≤40 字符** | 质检警告 | 太长的句子拆成两行（字幕卡显示不下） |
| R4 | **长中文句必须有标点** | 质检警告 | "分数线降了但竞争更激烈了" → 加逗号 |
| 5 | **中英文/数字不加空格** | - | `500分` ✅ `500 分` ❌ |
| 6 | **口语数字** | - | 用"两"不用"二" |
| 7 | **每行 = 一句 = 一条字幕卡** | - | 行间自动加停顿 |

> 💡 R1-R4 由 `synthesize.py` 内置 `_precheck_text()` 自动检查，合成前输出警告。
> 参考来源: `ai-video-director` skill 的 `check_script.py` 8 条规则。

---

## 合成命令

### Edge TTS（默认推荐）

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend edge `
  --voice zh-CN-YunyangNeural `
  --gap 300 `
  --slide-gap 800 `
  --fade 80
```

### Edge TTS 推荐声音

| 声音 | 风格 | 适合 |
|------|------|------|
| `zh-CN-YunyangNeural` | 自然男声（新闻播报） | ✅ 推荐 |
| `zh-CN-YunxiNeural` | 年轻男声 | 备选 |
| `zh-CN-XiaoxiaoNeural` | 女声 | 备选 |

### 火山引擎 咪仔（备选 1）

```powershell
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend volcano `
  --voice zh_female_mizai_uranus_bigtts `
  --gap 300 `
  --slide-gap 800 `
  --fade 80
```

### CosyVoice 本地声音复刻（降级 2）

```powershell
# 先启动服务: uv run .agent/workflows/short-video/scripts/cosyvoice_server.py
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend cosyvoice `
  --gap 300 `
  --slide-gap 800 `
  --fade 80
```

### 腾讯云预设音色（降级 3）

```powershell
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend tencent --voice 101007
```

---

## 音频处理管线

```
台词质检 → 逐句 TTS → 重采样 48kHz → 截尾部喘息
  → slide 边界 fade → 拼接(句间 300ms + 换页 800ms)
  → loudnorm -16LUFS(全局) → narration.wav + timestamps.json
```

- **采样率**: 48000Hz（Volcano 24kHz × 2 整数倍重采样）
- **前置静音**: 150ms 防止编码器截掉开头
- **后置静音**: 300ms 防止截断最后一个字
- **尾部静音截除**: silenceremove 阈值 -55dB（Edge TTS 兼容，-40dB 会误截末字衰减音）
- **时间戳**: 基于每句实际音频时长计算（不再按字数比例估算）
- **字幕清洗**: 只去句末标点和括号，保留逗号和顿号保持可读性

---

## 依赖配置

### Remotion (Node.js)

```powershell
cd .agent/workflows/short-video/remotion && npm install
```

### Python 脚本

通过 uv 自动管理。ffmpeg 必须在 PATH 中。

### 火山引擎 TTS 配置

1. 开通豆包语音合成: https://console.volcengine.com/speech/service/8
2. 创建 API Key: 控制台 → 语音技术 → API Key 管理
3. `.env` 添加: `VOLC_TTS_API_KEY=你的APIKey`

### 腾讯云 TTS 配置（降级 / 声音复刻）

1. 开通: https://console.cloud.tencent.com/tts
2. 开通声音复刻: https://console.cloud.tencent.com/tts (需额外开通 VRS 服务)
3. `.env` 添加: `SecretId=AKIDxxxxxx` + `SecretKey=xxxxxxxx`
4. 注册声音: `uv run .agent/workflows/short-video/scripts/register_voice.py`
5. 记录返回的 `FastVoiceType`，在 synthesize.py 中使用 `--backend tencent-clone --voice <ID>`
