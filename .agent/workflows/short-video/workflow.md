---
description: 短视频生产工作流 v29 — 模块化重构。详细规范拆分至 references/ 目录。
name: short-video
version: 29.0.0
trigger: /short-video
---
# 短视频生产工作流 v29

从 RAG 知识库一键生成横屏短视频，**一键发布到抖音/B站/快手/视频号/TikTok/YouTube/LinkedIn/Instagram**（8 平台自动）+ **小红书手动发布**。**storyline.md 是唯一数据源**，slides/台词/字幕全部自动生成。支持**中英文双语版本**。

## 核心理念

> **逻辑链完整 > 时长控制** — 逻辑链断了，多短都没用。
> **解读 > 播报** — 台词是观点输出，不是念数据。
> **数据先行** — 先用 RAG 探索数据，再围绕数据写 storyline。

### 六大铁律

| # | 规则 | 指标目标 |
| - | ---- | -------- |
| 1 | **3 秒钩子** — 前 3 秒必须抛出痛点问题或反直觉事实 | 3s播放率 ≥ 50% |
| 2 | **逻辑链完整** — 每个判断有因果，不跳步不断链 | 完播率 ≥ 20% |
| 3 | **系列化拆分** — 大主题拆 3-6 集，每集聚焦 1 个核心点 | 关注转化 ≥ 2% |
| 4 | **表格引用 1:1** — 表格 N 行数据 = N 条引用（每行来源不同） | 引用覆盖率 100% |
| 5 | **零编造** — 每个数据点必须有 RAG 引用原文支撑，没有来源写「待查」 | 编造数据 = 0 |
| 6 | **禁止重复台词** — 同一句话/观点/数据点不得跨 slide 重复，换说法也算 | 跨页重复 = 0 |

### 钩子类型库

| 类型 | 对应步骤 | 公式 | 示例 |
| ---- | -------- | ---- | ---- |
| 数据反转 | ①数据 | "A看着不错，但实际上B" | "507就能获邀？我翻完数据发现没这么简单" |
| 问题揭示 | ②问题 | "大部分人没意识到X" | "23万人排队，94%的人连门槛都摸不到" |
| 原因揭秘 | ③原因 | "为什么会这样？因为X" | "分数线降了54分，但竞争更激烈了" |
| 风险预警 | ④风险 | "如果你不注意X，后果是Y" | "邀请人数缩了75%，分数线还会涨" |
| 方案框架 | ⑤方案 | "我帮你算了/整理了X" | "507分你够不够？我按4种学历算了一遍" |

**技术栈**: Remotion (React) + Edge TTS（默认 zh-CN-YunyangNeural）/ 火山引擎 TTS（备选）

```
定题 → 系列规划 → RAG 数据探索 → storyline.md(数据+台词) → 硬核审计
  → parser 自动解析 → TTS → Remotion 渲染 → final.mp4 (×N集)
```

---

## Step 0: 定题

Agent 收到主题后，确认参数：

| 参数 | 默认值 | 说明 |
| ---- | ------ | ---- |
| 画面比例 | 16:9 landscape | 横屏视频号 |
| 时长 | **不设硬上限，逻辑链完整优先** | 参考 60-120 秒 |
| slides 数 | **8-12 张** | 含封面和结尾 |
| 受众 | 华人海外生活 | 内容定位 |
| TTS | Edge TTS (`zh-CN-YunyangNeural`) | 备选: 火山引擎咪仔 / CosyVoice / 腾讯云 |
| 频道名 | **海外生活指南** | 所有 storyline 作者字段必须使用 |

**痛点驱动选题**：列 4-6 个受众最关心的问题 → 不预设答案 → RAG 数据决定内容。

---

## Step 0.3: 主题分层研究 → `{slug}-research.md`

**执行者**: Agent

> 💡 先定范围，再分层（5 步逻辑链：数据→问题→原因→风险→方案），再探数据，最后拆视频。

📖 **详细规范**：[research-guide.md](references/research-guide.md)（查询工程铁律、反模式表、分组规则）

### 执行 RAG 检索

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --queries data/short-videos/{slug}/{slug}-research.md `
  --collection ca_federal `
  --output data/short-videos/{slug}/sources.json
```

### 完成条件

- `{slug}-research.md` 存在，含查询表 + 5 步逻辑链
- `sources.json` 存在（cite_rag.py 产出）
- 每个数据点有 `.md` 路径 + 完整 URL 来源
- 缺失数据已标注

---

## Step 0.5: 系列规划（大主题必须）

**触发条件**: 主题信息点 > 3 个，单集逻辑链无法完整覆盖

### 拆分原则

1. **每集 1 个核心问题** — 观众看完能记住 1 件事
2. **每集独立成篇** — 不看其他集也能理解
3. **集尾钩子** — 预告下集内容，引导关注
4. **命名规范**: `{slug}-ep{N}`，如 `ee-crs-ep1`

### 完成条件

- 系列规划表存在（或单集视频跳过此步）
- 每集聚焦 1 个核心问题，逻辑链完整

---

## Step 2: storyline.md — 唯一数据源

**触发 Skill**: `video-storyline`

> ⚠️ **storyline.md 是整条视频的唯一数据源 (Single Source of Truth)。**
> 所有数据必须来自 Step 0.3 的 sources.json + 原文。slides.json / script.txt **不再手写**。

📖 **详细格式规范**：[storyline-spec.md](references/storyline-spec.md)（元数据区、Slide 类型、通用字段、台词铁律、完整示例）

### 完成条件

- `storyline.md` 存在且格式合规
- 第一页是 `[cover]`，含 3 秒钩子
- **所有数字/日期/费用来自 sources.json 原文**
- 每个数据页有 `**引用**` + `**来源**`
- **表格引用 1:1** — 表格行数 = 引用条数
- 每页有 `**台词**`（逐句换行，解读型风格）
- **台词中判断句 + 翻译句占比 50% 以上**
- **禁止重复台词（铁律 6）**
- 信息点 ≤ 3，slides ≤ 12（不含引用来源页）
- `[citation]` 引用来源 slide 存在（`[preview]` 之前，渲染给观众看）

---

## Step 2.5: 硬核度审计 (Quality Gate)

**执行者**: Agent 自检

> **核心问题**: 台词是在**解读数据**还是在**念数据**？逻辑链是否完整？

📖 **详细审计标准**：[audit-checklist.md](references/audit-checklist.md)（7 维评估、水句/播报模式表、逻辑链断裂检测）

### 判定等级

| 等级 | 条件 | 动作 |
| ---- | ---- | ---- |
| 🟢**硬核** | 8 维全部及格 + 🔴 ≤ 10% + 📢 ≤ 20% | 继续 Step 3 |
| 🟡**科普** | 1-2 维不及格 | 修改 storyline 后重新审计 |
| 🔴**水文** | 3+ 维不及格 | 回 Step 2 重写 |

### 完成条件

- 审计结果为 🟢 **硬核**
- 具体数字 ≥ 3 个，🔴 ≤ 10%，📢 ≤ 20%
- 逻辑链无断裂
- 跨段一致性通过（结论vs预告无矛盾、无冗余、与下期内容对齐）

---

## Step 3: 自动解析（Parser 自动完成）

> ⚠️ 此步骤由 `storyline-parser.js` 自动完成，无需手动操作。

Parser 从 `storyline.md` 自动生成 `SlideData[]`（slide 数据）+ `narration[]`（台词数组，用于 TTS + 字幕）。

---

## Step 5: 语音合成 → `narration/`

### 方式A: TTS 自动合成（台词迭代阶段用，快速预览）

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend edge `
  --voice zh-CN-YunyangNeural `
  --gap 300 --slide-gap 800 --fade 80
```

### 方式B: 真人录音（台词定稿后用，品质最高）

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/record.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --whisper-model medium
```

交互操作: ⏎ 开始/停止录音 | r 重录 | p 播放 | s 跳过 | q 中止

📖 **TTS 备选引擎 + 音频管线 + 配置**：[tts-guide.md](references/tts-guide.md)

### 完成条件

- `narration/narration.wav` 存在
- `narration/timestamps.json` 存在

---

## Step 6: Remotion 渲染 → `output/final.mp4`

```powershell
# // turbo
# cwd: textbook-rag/
node .agent/workflows/short-video/remotion/render.mjs --data data/short-videos/{slug}
```

📖 **组件架构 + 字号规范**：[remotion-render.md](references/remotion-render.md)

### 完成条件

- `output/final.mp4` 存在
- 时长合理（无硬上限，逻辑链完整优先）

---

## Step 7: 检查 & 发布

```powershell
# // turbo
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 `
  data/short-videos/{slug}/output/final.mp4
```

### 发布前检查清单

- [ ] 逻辑链完整，无跳步断链
- [ ] 前 3 秒是钩子（非寒暄）
- [ ] 信息点 ≤ 3 个
- [ ] 每个论点有证据 slide 支撑
- [ ] **表格引用 1:1**
- [ ] 声音自然，数字/英文混排无机器人感
- [ ] 结尾 `[preview]` 固定三段式：通用互动（不变）+ 下期预告（每期换）+ 关注CTA（不变）
- [ ] `[preview]` 不询问观众个人移民/财务数据（避免擦边咨询风险）

### 发布

> ⚠️ **逐平台发布** — 每个平台单独一条命令，用户逐条运行。不要用一键全发。

#### 中文平台（v1）

```powershell
# 1️⃣ 视频号（⚠️ 每次发布前都需要重新扫码登录）
uv run .agent/workflows/short-video/scripts/publish_all.py --login weixin
uv run .agent/workflows/short-video/scripts/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms weixin

# 2️⃣ 小红书（⚠️ 手动发布 — 禁止自动化，已被平台处罚）
# 生成文案（标题+描述+标签），然后在小红书 APP 手动发布
uv run .agent/workflows/short-video/scripts/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms xiaohongshu --dry-run

# 3️⃣ 抖音
uv run .agent/workflows/short-video/scripts/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms douyin

# 4️⃣ B站
uv run .agent/workflows/short-video/scripts/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms bilibili

# 5️⃣ 快手
uv run .agent/workflows/short-video/scripts/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms kuaishou
```

#### 国际平台（v2）

```powershell
# 6️⃣ YouTube
uv run .agent/workflows/short-video/publish/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms youtube

# 7️⃣ TikTok
uv run .agent/workflows/short-video/publish/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms tiktok

# 8️⃣ LinkedIn
uv run .agent/workflows/short-video/publish/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms linkedin

# 9️⃣ Instagram
uv run .agent/workflows/short-video/publish/publish_all.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --platforms instagram
```

📖 **平台详情 + 合规规则 + 登录命令**：[publishing-guide.md](references/publishing-guide.md)

---

## 架构说明

### Skills

| Skill | 职责 |
| ----- | ---- |
| `video-storyline` | 叙事线设计 + 逻辑链构建 |

### Scripts

| 脚本 | 输入 | 输出 |
| ---- | ---- | ---- |
| `cite_rag.py` | research.md | sources.json |
| `storyline-parser.js` | storyline.md | SlideData[] + narration[] |
| `synthesize.py` | storyline.md + .env | narration.wav + timestamps.json |
| `record.py` | storyline.md + 麦克风 | narration.wav + timestamps.json |
| `render.mjs` | storyline.md + narration/ | final.mp4 |
| `scripts/publish_all.py` | final.mp4 + storyline.md | 中文平台一键发布 |
| `publish/publish_all.py` | final.mp4 + storyline.md | 国际平台一键发布 |

**脚本间零依赖** — 每个脚本独立运行，通过文件系统通信。

### 参考文档

| 文档 | 内容 |
| ---- | ---- |
| [research-guide.md](references/research-guide.md) | RAG 查询工程 + 研究规范 |
| [storyline-spec.md](references/storyline-spec.md) | storyline 格式 + 铁律 + 示例 |
| [audit-checklist.md](references/audit-checklist.md) | 硬核度审计标准 + 模式表 |
| [tts-guide.md](references/tts-guide.md) | TTS 规范 + 声音 + 配置 |
| [remotion-render.md](references/remotion-render.md) | Remotion 组件 + 字号 |
| [publishing-guide.md](references/publishing-guide.md) | 多平台发布 + 合规 |

---

## 文件结构

```text
data/short-videos/{slug}/
├── {slug}-research.md           # Step 0.3: 分层研究 (Agent)
├── sources.json                 # Step 0.3: RAG 检索结果 (Script)
├── storyline.md                 # Step 2: 唯一数据源 (Skill)
│   └── 包含: slide数据 + 台词 + 引用 + 来源
├── narration/                   # Step 5: TTS (自动从台词生成)
│   ├── narration.wav
│   └── timestamps.json
└── output/                      # Step 6: 最终视频
    └── final.mp4

.agent/workflows/short-video/
├── references/                  # 详细规范参考文档
│   ├── research-guide.md
│   ├── storyline-spec.md
│   ├── audit-checklist.md
│   ├── tts-guide.md
│   ├── remotion-render.md
│   └── publishing-guide.md
├── remotion/                    # Remotion 项目（通用模板）
│   ├── package.json
│   ├── render.mjs
│   └── src/
├── scripts/
│   ├── cite_rag.py
│   ├── synthesize.py
│   ├── publish_all.py
│   └── publish_weixin.py
├── publish/                     # v2 国际平台发布系统
│   ├── publish_all.py
│   ├── config.yaml
│   ├── platforms/
│   └── credentials/
├── wechat-video-channel-rules.md
└── workflow.md                  # 本文件
```
