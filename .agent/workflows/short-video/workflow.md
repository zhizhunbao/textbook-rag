---
description: 短视频生产工作流 v15 — 数据先行 + Remotion + 火山引擎TTS
name: short-video
version: 15.0.0
trigger: /short-video
---
# 短视频生产工作流 v15

从 RAG 知识库一键生成微信视频号横屏短视频。

## 核心理念

> **完播率 > 信息量** — 短视频平台推荐算法以完播率为核心权重。
> 一条 4 分钟视频完播率 4%，不如 5 条 90 秒视频各 30% 完播。

> **清晰度 > 时长限制** — 硬卡 60 秒 / 250 字会导致脚本变成"念要点"。
> 把话说明白比卡秒数重要。

> **数据先行** — 先用 RAG 探索数据，再围绕数据写 storyline。
> 不允许跳过数据探索直接写内容。

### 三大铁律

| # | 规则                                                         | 指标目标        |
| - | ------------------------------------------------------------ | --------------- |
| 1 | **3 秒钩子** — 前 3 秒必须抛出痛点问题或反直觉事实    | 3s播放率 ≥ 50% |
| 2 | **90 秒以内** — 每条视频 60-90 秒，清晰度优先         | 完播率 ≥ 20%   |
| 3 | **系列化拆分** — 大主题拆 3-6 集，每集聚焦 1 个核心点 | 关注转化 ≥ 2%  |

### 钩子类型库

| 类型       | 示例                                | 适用场景   |
| ---------- | ----------------------------------- | ---------- |
| 反直觉数据 | "CRS满分500，邀请线507，满分都不够" | 数据类视频 |
| 痛点提问   | "你知道LMIA加分已经取消了吗？"      | 政策变化   |
| 损失厌恶   | "少了这一步，学历分直接降22分"      | 流程类视频 |
| 身份代入   | "如果你30岁以上，这条一定要看"      | 人群定向   |

**技术栈**: Remotion (React) + 火山引擎 TTS（豆包语音 2.0 · 咪仔）

```
定题 → 系列规划 → RAG 数据探索 → 故事线(基于数据) → 硬核审计
  → slides.json → script.txt → TTS → Remotion 渲染 → final.mp4 (×N集)
```

---

## Step 0: 定题

Agent 收到主题后，确认参数：

| 参数      | 默认值                                                | 说明                 |
| --------- | ----------------------------------------------------- | -------------------- |
| 画面比例  | 16:9 landscape                                        | 横屏视频号           |
| 时长      | **60-90 秒**                                    | 弹性上限，清晰度优先 |
| slides 数 | **8-12 张**                                     | 含封面和结尾         |
| 受众      | 华人移民/留学                                         | 内容定位             |
| TTS       | 火山引擎 TTS (咪仔 `zh_female_mizai_uranus_bigtts`) | 降级: 腾讯云 / Edge  |

### 痛点驱动选题

1. **痛点问题 = 观众的真实疑问** — 每个主题列 4-6 个目标受众最关心的问题
2. **不预设答案** — 避免在选题阶段就限定内容，数据可能揭示更好的角度
3. **RAG 数据决定内容** — 数据探索后可能发现更好的切入点

---

## Step 0.3: 主题分层研究 → `{slug}-research.md`

**执行者**: Agent

> 💡 **先定范围，再分层，再探数据，最后拆视频。**
> 任何主题都用同一套骨架组织研究，防止信息爆炸。

### 研究范围（4 层之前必须先定）

```markdown
## 研究范围
- **覆盖**: 本次研究覆盖什么（如：PNP 联邦总览级别）
- **不覆盖**: 明确排除什么（如：各省具体 stream 细节）
- **深度**: 概览 / 对比 / 单省深入
- **数据源**: 用哪些 RAG collection + 官网
```

> ⚠️ 范围不清就开始研究 = 越写越发散 = 写完自己都凌乱。
> 像 PNP 这种各省规则不同的主题，必须先界定是"联邦总览"还是"单省深入"。

### 通用 4 层骨架（每个主题带默认 RAG 查询）

> ⚠️ **每个主题自带英文 RAG 查询模板。**
> Agent 根据具体主题填入关键词，生成 `queries.md`，用 `cite_rag.py` 一次性检索。
> Agent 只读 `sources.json` 的片段，**不直接读 .md 文件**，省 token。

```
L1 概念层 (3)
  ├── L1.1 定义  → "{X} overview definition eligibility"
  ├── L1.2 关系  → "{X} relationship {Y} how they connect"
  └── L1.3 机制  → "{X} application process steps how it works"

L2 结构层 (3)
  ├── L2.1 路径  → "{X} streams types pathways categories"
  ├── L2.2 参与方 → "{X} who manages provinces federal requirements"
  └── L2.3 范围  → "{X} who is eligible excluded provinces territories"

L3 数据层 (4)
  ├── L3.1 费用  → "{X} application fee cost permanent residence"
  ├── L3.2 时间  → "{X} processing time months how long"
  ├── L3.3 门槛  → "{X} minimum score quota allocation numbers"
  └── L3.4 变化  → "{X} recent changes 2025 2026 new policy"

L4 决策层 (2)
  ├── L4.1 选择  → "{X} which stream path best for skilled worker graduate"
  └── L4.2 时机  → "{X} 2026 should I apply now window deadline"
```

### 研究流程

```
Step 1: Agent 写 {slug}-research.md 骨架（含 RAG 查询表，12 个英文查询）
Step 2: cite_rag.py --queries {slug}-research.md → sources.json（脚本跑，零 token）
Step 3: Agent 读 sources.json 片段，回填 research.md 各层内容
```

> 产出只有 2 个文件: `{slug}-research.md` + `sources.json`

### 研究规范

1. **每个主题必须有来源** — `.md` 路径 + 完整官网 URL（不简写）
2. **引用原文** — 关键数据必须附官网英文原文 blockquote
3. **标注缺失** — 没有 RAG 数据的主题标注 `❌ 未入库` + 建议入库命令
4. **每层独立可读** — 不看其他层也能理解本层内容

### 从层到子弹

研究完成后，Agent 从 4 层中提取"子弹"（短视频选题）：

- **1 个主题 = 1 颗子弹 = 1 条视频**
- 短视频优先取 L3/L4 层（数据+决策），L1/L2 作为背景穿插
- 12 个主题不一定都出视频，只取有情绪张力的

### 执行 RAG 检索

> research.md 里的查询表直接作为 cite_rag.py 的输入，不需要单独的 queries.md。

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --queries data/short-videos/{slug}/{slug}-research.md `
  --persona live-study-immigration `
  --output data/short-videos/{slug}/sources.json
```

> ⚠️ ChromaDB 数据全部英文（来自 canada.ca），中文查询命中率极低。**必须用英文查询。**

### 数据不足时入库

如果 RAG 检索结果不足以覆盖某个主题，**必须先入库再继续**：

```powershell
# 单页入库
uv run python scripts/ingest/ingest_urls.py `
  --category federal-ircc --collection ca_federal --force `
  "https://www.canada.ca/en/..."

# EE 轮次 JSON 数据入库
uv run python scripts/ingest/ingest_urls.py `
  --ee-rounds --category federal-ircc --collection ca_federal --force
```

入库后重新执行 RAG 检索，直到 12 个主题全部有数据。

### 完成条件

- `{slug}-research.md` 存在，含查询表 + 4 层 12 主题
- `sources.json` 存在（cite_rag.py 产出）
- 每个数据点有 `.md` 路径 + 完整 URL 来源
- 缺失数据已标注

---

## Step 0.5: 系列规划（大主题必须）

**触发条件**: 主题内容预估超过 90 秒（信息点 > 5 个）

### 拆分原则

1. **每集 1 个核心问题** — 观众看完能记住 1 件事
2. **每集独立成篇** — 不看其他集也能理解
3. **集尾钩子** — 预告下集内容，引导关注
4. **命名规范**: `{slug}-ep{N}`，如 `ee-crs-ep1`

### 系列规划表格式

```markdown
| 集数 | 标题 | 核心问题 | 钩子类型 | 预估时长 |
|------|------|----------|----------|----------|
| EP1 | ... | 一句话问题 | 反直觉/痛点/... | 50s |
```

### 完成条件

- 系列规划表存在（或单集视频跳过此步）
- 每集预估时长 ≤ 90 秒
- 每集有独立钩子

---

## Step 1: (已合并入 Step 0.3)

> RAG 数据探索已整合进 Step 0.3「主题分层研究」。
> queries.md + sources.json 在研究阶段一并产出。

---

## Step 2: 叙事线 → `storyline.md`（基于已探索的数据）

**触发 Skill**: `video-storyline`

> ⚠️ **storyline 的所有数据必须来自 Step 0.3 已探索的 sources.json + 原文。**
> 不允许凭记忆编造数据。每个数据断言必须附带来源 URL。

Agent 基于 Step 0.3 发现的硬数据构建**单集**叙事逻辑:

1. **3 秒钩子**（必须是第一个节点）— 用 sources.json 中最有冲击力的数据
2. 核心论点（最多 3 个信息点）— 每个论点必须有 sources.json 中的硬数据支撑
3. 每个论点配对证据（blockquote 引用原文 + 来源 URL）
4. **互动收尾** — 评论区问题 + 下集预告

### 引用格式

每个证据直接用 blockquote 引原文 + URL（无需 `[需要引用]` 占位标记）：

```markdown
> "English citation text from official source"
> — [source-page](https://www.canada.ca/en/...)
```

### 引用来源汇总表

storyline 末尾包含完整引用汇总：

```markdown
## 📋 引用来源汇总
| # | 断言 | 引用原文 | 来源URL |
|---|------|----------|--------|
| 1 | ... | "..." | https://... |
```

### 论点表格格式

论点部分统一用 markdown 表格，**禁止** bullet list 罗列论点：

```markdown
### 论点
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 信息点A | 数据A | 说明A |
```

### 90 秒约束检查

- 信息点 ≤ 3 个（超过必须拆集）
- slides ≤ 12 张（含封面 + 结尾）
- 口播文字无硬上限（参考：中文 ~4 字/秒，清晰度优先）

### 完成条件

- `storyline.md` 存在
- 第一个节点是 3 秒钩子
- **所有数字/日期/费用来自 sources.json 原文**（不允许凭记忆）
- 每个证据有 blockquote 引用 + URL（无 `[需要引用]` 占位）
- 信息点 ≤ 3，slides ≤ 12
- 引用来源汇总表存在

> **从此步开始，storyline.md 是 single source of truth。**
> slides.json 和 script.txt 的所有数据都必须来自最终版 storyline。

---

## Step 2.5: 硬核度审计 (Quality Gate)

**执行者**: Agent 自检

> **核心问题**: storyline 里的硬数据够不够让内容变成"让人截图保存的硬货"？

### 5 维评估标准

| 维度                 | 定义                   | 及格线  |
| -------------------- | ---------------------- | ------- |
| **独家数据**   | 具体数字/日期/门槛     | ≥ 5/10 |
| **反直觉洞察** | 打破常见误解           | ≥ 5/10 |
| **可操作性**   | 观众看完能立刻做点什么 | ≥ 4/10 |
| **信息密度**   | 每秒有效信息量，无废话 | ≥ 5/10 |
| **证据强度**   | 每个断言有官方来源     | ≥ 7/10 |

### 审计流程

1. **逐论点标注** — 🟢硬核 / 🟡科普 / 🔴水句
2. **数水句比例** — 🔴 占比 > 20% → 必须重写
3. **数据点计数** — 具体数字 < 3 个 → 必须从 sources.json 补充
4. **决策工具检查** — 是否有"你该怎么做"的判断依据

### 常见水句模式（必须砍掉或替换）

| 模式       | 示例                     | 处理               |
| ---------- | ------------------------ | ------------------ |
| 纯定义句   | "被选中了就叫省提名"     | 删除               |
| 无数据列举 | "通用轮次、项目定向轮次" | 合并为带数据的     |
| 空过渡     | "关键区别来了"           | 删除或替换为信息句 |
| 重复强调   | 同一论点说两次           | 只保留更强版本     |

### 判定等级

| 等级             | 条件                     | 动作                      |
| ---------------- | ------------------------ | ------------------------- |
| 🟢**硬核** | 5 维全部及格 + 🔴 ≤ 10% | 继续 Step 3               |
| 🟡**科普** | 1-2 维不及格             | 修改 storyline 后重新审计 |
| 🔴**水文** | 3+ 维不及格              | 回 Step 2 重写            |

### 完成条件

- 审计结果为 🟢 **硬核**
- 具体数字 ≥ 3 个
- 🔴 水句占比 ≤ 10%

---

## Step 3: AI 生成 slides.json

**执行者**: Agent

> ⚠️ 所有数据和引用必须来自 storyline.md，不允许引入新数据。

### slides.json Schema

```json
{
  "meta": { "title": "视频标题", "author": "频道名" },
  "slides": [
    {
      "type": "cover",
      "title": "主标题",
      "subtitle": "副标题（可选）",
      "source": "https://www.canada.ca/en/..."
    },
    {
      "type": "argument",
      "title": "论点标题",
      "table": { "headers": ["列1", "列2"], "rows": [["数据1", "数据2"]] },
      "citation": "Official English citation...",
      "source": "https://..."
    },
    {
      "type": "evidence",
      "title": "数据支撑",
      "table": { "headers": [], "rows": [] },
      "citation": "...",
      "source": "https://..."
    },
    {
      "type": "summary",
      "title": "总结",
      "points": ["要点1（可用 **加粗** 强调）"],
      "source": "https://..."
    },
    {
      "type": "cta",
      "title": "评论区互动",
      "content": "正文",
      "source": "https://..."
    },
    {
      "type": "preview",
      "title": "下期预告",
      "content": "预告内容",
      "source": "https://..."
    }
  ]
}
```

### Slide 类型

| type         | 用途     | 必填                   | 可选            |
| ------------ | -------- | ---------------------- | --------------- |
| `cover`    | 封面页   | title, source          | subtitle        |
| `argument` | 论点页   | title, source          | table, citation |
| `evidence` | 证据页   | title, source          | table, citation |
| `summary`  | 总结页   | title, points, source  | citation        |
| `cta`      | 互动引导 | title, content, source | —              |
| `preview`  | 下期预告 | title, content, source | —              |

### 内容规范

1. **论点+证据配对** — 每个 `argument` 后紧跟 `evidence`
2. **每页必须有 source** — 完整 URL
3. **禁止 emoji** — 标题、表格、正文不加 emoji
4. **缩写词必须解释** — 首次出现用 `EE（快速通道）` 格式
5. **URL 必须以 `.html` 结尾**
6. **文本中可用 `**加粗**`** — 渲染时变为金色高亮

### 完成条件

- `slides.json` 存在且 JSON 合法
- 每个 argument 后紧跟 evidence
- 所有 slide 都有 source 字段

---

## Step 4: 口播脚本 → `script.txt`

**执行者**: Agent

> ⚠️ 纯粹基于最终版 storyline.md 生成，只做口语化转写，不引入新内容。

### 痛点问答节奏

每个 slide 采用三拍结构：

1. **痛点提问** — 观众心中的真实疑问（开新 slide，带 `|`）
2. **回答** — 直接给答案
3. **数据/引用** — 用官方数据佐证

### 编写规则

1. **前 3 秒 = 钩子** — 第一行必须是痛点问题，禁止"大家好"等废话开场
2. **一行 = 一句话** — 独立合成语音、独立显示字幕
3. **有 `|` 的行开新幻灯片，没有 `|` 的行延续上一张**
4. **最后 2-3 行必须是互动引导** — 评论区问题 + 预告下集
5. 语气自然、口语化
6. 有 RAG 来源的行标注 `[来源:URL]`

### TTS 友好规范

1. **中英文/数字不加空格** — `500分` ✅ `500 分` ❌
2. **口语数字** — 用"两"不用"二"
3. **用句号控制停顿** — 长句拆短句
4. **冒号改句号** — 冒号断句不稳定

### script.txt 格式

```
# 主题名 EP1
痛点问题？ | [钩子]
回答。
数据佐证。
下一个痛点？ | [来源:URL]
回答。
互动问题？ | [互动]
评论区告诉我。
下集预告。 | [预告]
```

### 完成条件

- `script.txt` 存在
- 带 `|` 的行数 = slides.json 的 slide 数量 ≤ 12
- 第一行是痛点钩子
- 最后有互动引导 + 下集预告

---

## Step 5: TTS 语音合成 → `narration/`

**执行脚本**: `synthesize.py`

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend volcano `
  --voice zh_female_mizai_uranus_bigtts `
  --gap 300 `
  --slide-gap 800
```

### 音色选择

**火山引擎（推荐）**:

| voice_type                                  | 名称         | 适用场景              |
| ------------------------------------------- | ------------ | --------------------- |
| **`zh_female_mizai_uranus_bigtts`** | 咪仔         | ✅ 默认，视频配音女声 |
| `zh_male_jieshuoxiaoming_uranus_bigtts`   | 解说小明     | 通用解说男声          |
| `zh_male_cixingjieshuonan_uranus_bigtts`  | 磁性解说男声 | 低沉磁性解说          |

**腾讯云（降级）**: VoiceType `101007`（智娜）或 `101001`（智瑜）

降级命令：

```powershell
# 腾讯云
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend tencent --voice 101007

# Edge TTS（离线）
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend edge
```

### 音频参数

- **句间停顿**: 300ms — 同一 slide 内句子之间
- **换页停顿**: 800ms — 切换 slide 时
- **前置静音**: 150ms 防止编码器截掉开头
- **拼接**: 全部转 44100Hz WAV，无损拼接

### 完成条件

- `narration/narration.wav` 存在
- `narration/timestamps.json` 存在

---

## Step 6: Remotion 渲染 → `output/final.mp4`

**执行脚本**: `render.mjs`

```powershell
# // turbo
# cwd: textbook-rag/.agent/workflows/short-video/remotion/
node render.mjs --data ../../../../data/short-videos/{slug}
```

### Remotion 组件架构

```
1920×1080 总画布
┌─────────────────────────────────┐
│  来源 URL 水印（顶部）           │
│  幻灯片区 (1920×880)            │  ← 渥太华蓝金主题
│  - CoverSlide: 封面（金色渐变）  │
│  - ContentSlide: 表格/列表/正文  │
│  - 证据页左侧金线标记            │
├─────────────────────────────────┤
│  字幕条 (1920×200)              │  ← TikTok 逐词高亮
│  已读词=金色  未读词=灰色        │
└─────────────────────────────────┘
```

### 完成条件

- `output/final.mp4` 存在
- 时长 ≤ 95 秒（弹性上限）

---

## Step 7: 检查 & 发布

```powershell
# // turbo
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 `
  data/short-videos/{slug}/output/final.mp4
```

### 发布前检查清单

- [ ] 时长 ≤ 95 秒
- [ ] 前 3 秒是钩子（非寒暄）
- [ ] 信息点 ≤ 3 个
- [ ] 每个论点有证据 slide 支撑
- [ ] 声音自然，数字/英文混排无机器人感
- [ ] 来源 URL 水印正确
- [ ] TikTok 字幕逐词高亮同步
- [ ] 结尾有互动问题 + 下集预告

### 发布规范

- **标题**: 钩子句式，带数字
- **封面**: 大字+数字，高对比度
- **标签**: `#加拿大移民` `#程序员移民` + 主题标签
- **系列标记**: 如 "EE全解析 1/5"

### 发布后追踪

| 指标      | 目标值 | 不达标动作           |
| --------- | ------ | -------------------- |
| 3s 播放率 | ≥ 50% | 换钩子/封面重发      |
| 完播率    | ≥ 25% | 缩短时长或删减信息点 |
| 互动率    | > 0    | 加强互动引导         |

---

## 架构说明

### Skills

| Skill               | 职责                    |
| ------------------- | ----------------------- |
| `video-storyline` | 叙事线设计 + 逻辑链构建 |

> `slides.json` 和 `script.txt` 由 Agent 直接编写（规则内联于 Step 3/4）。

### Scripts

| 脚本              | 输入                       | 输出                            |
| ----------------- | -------------------------- | ------------------------------- |
| `cite_rag.py`   | queries.md 或 storyline.md | sources.json                    |
| `synthesize.py` | script.txt + .env          | narration.wav + timestamps.json |
| `render.mjs`    | slides.json + narration/   | final.mp4                       |

**脚本间零依赖** — 每个脚本独立运行，通过文件系统通信。

### 已废弃脚本

| 脚本                  | 替代                   |
| --------------------- | ---------------------- |
| `compose_marp.py`   | Remotion 内置渲染      |
| `assemble_video.py` | Remotion render.mjs    |
| `slides.md` (Marp)  | slides.json (数据驱动) |

---

## 文件结构

```text
data/short-videos/{slug}/
├── queries.md                   # Step 1: RAG 探索查询 (Agent)
├── sources.json                 # Step 1: RAG 检索结果 (Script)
├── storyline.md                 # Step 2: 叙事逻辑 (Skill, 基于数据)
├── slides.json                  # Step 3: 幻灯片数据 (Agent)
├── script.txt                   # Step 4: 口播脚本 (Agent)
├── narration/                   # Step 5: TTS
│   ├── narration.wav
│   └── timestamps.json
└── output/                      # Step 6: 最终视频
    └── final.mp4

.agent/workflows/short-video/
├── remotion/                    # Remotion 项目（通用模板）
│   ├── package.json
│   ├── render.mjs
│   └── src/
│       ├── ShortVideo.tsx
│       ├── theme.ts
│       ├── components/
│       │   ├── CoverSlide.tsx
│       │   ├── ContentSlide.tsx
│       │   └── SubtitleBar.tsx
│       └── utils/
│           └── words.ts
├── scripts/
│   ├── cite_rag.py              # RAG 检索（支持 --queries 和 --storyline）
│   └── synthesize.py            # TTS 合成
├── voice/                       # 音色测试与样本
└── workflow.md                  # 本文件
```

---

## 依赖

```powershell
# Remotion (Node.js)
cd .agent/workflows/short-video/remotion && npm install

# Python 脚本 (通过 uv 自动管理)
# ffmpeg 必须在 PATH 中
```

### 火山引擎 TTS 配置

1. 开通豆包语音合成: https://console.volcengine.com/speech/service/8
2. 创建 API Key: 控制台 → 语音技术 → API Key 管理
3. `.env` 添加: `VOLC_TTS_API_KEY=你的APIKey`

### 腾讯云 TTS 配置（降级）

1. 开通: https://console.cloud.tencent.com/tts
2. `.env` 添加: `SecretId=AKIDxxxxxx` + `SecretKey=xxxxxxxx`
