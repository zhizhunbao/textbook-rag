---
description: 短视频生产工作流 v22 — 零编造 + 表格引用1:1 + 解读型台词 + 禁止重复台词 + storyline.md 唯一数据源 + Remotion + 火山咪仔TTS
name: short-video
version: 22.0.0
trigger: /short-video
---
# 短视频生产工作流 v20

从 RAG 知识库一键生成微信视频号横屏短视频。**storyline.md 是唯一数据源**，slides/台词/字幕全部自动生成。

## 核心理念

> **逻辑链完整 > 时长控制** — 逻辑链断了，多短都没用。
> 时长是结果，不是目标。把一个判断讲透比硬卡 60 秒重要。

> **解读 > 播报** — 台词是观点输出，不是念数据。
> 表格放画面让观众自己看，嘴巴负责说"这意味着什么"。

> **数据先行** — 先用 RAG 探索数据，再围绕数据写 storyline。
> 不允许跳过数据探索直接写内容。

### 六大铁律

| # | 规则                                                         | 指标目标        |
| - | ------------------------------------------------------------ | --------------- |
| 1 | **3 秒钩子** — 前 3 秒必须抛出痛点问题或反直觉事实    | 3s播放率 ≥ 50% |
| 2 | **逻辑链完整** — 每个判断有因果，不跳步不断链          | 完播率 ≥ 20%   |
| 3 | **系列化拆分** — 大主题拆 3-6 集，每集聚焦 1 个核心点 | 关注转化 ≥ 2%  |
| 4 | **表格引用 1:1** — 表格 N 行数据 = N 条引用（每行来源不同） | 引用覆盖率 100% |
| 5 | **零编造** — 表格/台词中每个数据点必须有 RAG 引用原文支撑，没有来源写「待查」，绝不猜测 | 编造数据 = 0 |
| 6 | **禁止重复台词** — 同一句话/同一观点/同一数据点不得在两个及以上 slide 的台词中出现，换个说法复述也算重复 | 跨页重复 = 0 |

### 钩子类型库

> 钩子的本质：**撕开数据表面和真相之间的裂缝**，让观众想知道"为什么"。
> 钩子类型和 5 步逻辑链对应，选哪种取决于视频的核心卖点。

| 类型 | 对应步骤 | 公式 | 示例 |
| ---- | -------- | ---- | ---- |
| 数据反转 | ①数据 | "A看着不错，但实际上B" | "507就能获邀？我翻完数据发现没这么简单" |
| 问题揭示 | ②问题 | "大部分人没意识到X" | "23万人排队，94%的人连门槛都摸不到" |
| 原因揭秘 | ③原因 | "为什么会这样？因为X" | "分数线降了54分，但竞争更激烈了" |
| 风险预警 | ④风险 | "如果你不注意X，后果是Y" | "邀请人数缩了75%，分数线还会涨" |
| 方案框架 | ⑤方案 | "我帮你算了/整理了X" | "507分你够不够？我按4种学历算了一遍" |

**技术栈**: Remotion (React) + 火山引擎 TTS（zh_female_mizai_uranus_bigtts / 咪仔）

```
定题 → 系列规划 → RAG 数据探索 → storyline.md(数据+台词) → 硬核审计
  → parser 自动解析 → TTS → Remotion 渲染 → final.mp4 (×N集)
```

---

## Step 0: 定题

Agent 收到主题后，确认参数：

| 参数      | 默认值                                                | 说明                 |
| --------- | ----------------------------------------------------- | -------------------- |
| 画面比例  | 16:9 landscape                                        | 横屏视频号           |
| 时长      | **不设硬上限，逻辑链完整优先**              | 参考 60-120 秒，讲透比卡秒数重要 |
| slides 数 | **8-12 张**                                     | 含封面和结尾         |
| 受众      | 华人移民/留学                                         | 内容定位             |
| TTS       | 火山引擎 (`zh_female_mizai_uranus_bigtts` / 咪仔)     | 降级: Edge TTS / CosyVoice 本地 / 腾讯云  |

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
- **数据源**: 用哪些 ChromaDB collection（如 ca_federal, ca_fcac）+ 官网
```

> ⚠️ 范围不清就开始研究 = 越写越发散 = 写完自己都凌乱。
> 像 PNP 这种各省规则不同的主题，必须先界定是"联邦总览"还是"单省深入"。

### 5 步逻辑链骨架（替代旧 4 层结构）

> ⚠️ **研究结构必须直接映射到 storyline 逻辑链。**
> 围绕「数据 → 问题 → 原因 → 风险 → 方案」组织，不要先收集百科再提炼。

```
S1 数据采集 (按实体拆分，每条瞄准 1 个数据点)
  ├── S1.1 核心数字  → 用产品/项目真名 + 目标数据点
  │     ❌ "EE latest data numbers 2025 2026 statistics"（关键词堆砌）
  │     ✅ "Express Entry CEC invitation rounds 2026 minimum CRS score"
  ├── S1.2 分布/构成 → 指定要查的维度
  │     ❌ "{X} breakdown distribution by category type"
  │     ✅ "Express Entry Category-Based Selection healthcare STEM French 2026"
  ├── S1.3 历史对比  → 指定时间范围 + 对比维度
  │     ✅ "Express Entry CRS cutoff trend 2020 2021 2022 2023 2024 general rounds"
  └── S1.4 池子/竞争 → 用具体术语
        ✅ "Express Entry pool candidates profile CRS score distribution"

S2 问题发现 (Agent 独立推导，不走 RAG)
  ├── S2.1 数据里有什么反直觉/不对劲的？
  ├── S2.2 哪些数字看着"好"但实际藏着坑？
  └── S2.3 不同人群面对这些数据处境有何不同？

S3 原因分析 (2-3 条 RAG 查询)
  ├── S3.1 机制  → 用官方术语描述机制
  │     ✅ "Provincial Nominee Program two streams paper-based Express Entry enhanced"
  ├── S3.2 政策  → 引用具体政策名/日期
  │     ✅ "IRCC LMIA points removal March 2025 CRS calculation change"
  └── S3.3 因果  → 指向具体因果关系
        ✅ "Express Entry general rounds cancelled 2025 Category-Based Selection only"

S4 风险预测 (Agent 推导，可用 RAG 辅助)
  ├── S4.1 当前趋势持续会怎样？
  ├── S4.2 哪些因素可能导致情况变好/变差？
  └── S4.3 最坏情况是什么？

S5 方案建议 (1-2 条 RAG 查询)
  ├── S5.1 方案  → 用具体替代路径名
  │     ✅ "Provincial Nominee Program Ontario HCP stream international student eligible"
  └── S5.2 时机  → 用具体窗口/截止日
        ✅ "Ontario HCP stream intake 2026 application deadline processing time"
```

> **S2 和 S4 是 Agent 必须独立完成的推导。**
> 写不出 S2（发现问题），说明数据理解不够，必须回头补研究。

### 研究流程

```
Step 1: Agent 写 {slug}-research.md 骨架（含 5 步逻辑链 + RAG 查询表）
Step 2: cite_rag.py --queries {slug}-research.md --collection <collections> → sources.json（脚本跑，零 token）
Step 3: Agent 读 sources.json 片段，回填 S1/S3/S5 数据
Step 4: Agent 独立完成 S2（问题发现）和 S4（风险预测）的推导
```

> 产出只有 2 个文件: `{slug}-research.md` + `sources.json`

### 研究规范

1. **每个主题必须有来源** — `.md` 路径 + 完整官网 URL（不简写）
2. **引用原文** — 关键数据必须附官网英文原文 blockquote
3. **标注缺失** — 没有 RAG 数据的主题标注 `❌ 未入库` + 建议入库命令
4. **S2/S4 必须有推导过程** — 不能只写结论，必须写出"因为A所以B"的推理链

### 防跑偏铁律（RAG 查询纪律）

> ⚠️ **查询跑偏 = 视频跑偏 = 完播率归零。**

1. **主题锁定** — 每条查询必须能直接回答视频 H1 标题的问题。
   H1 = "留学一年花多少钱" → 每条查询必须关于「花了多少」「费用是多少」「金额是多少」
   如果一条查询的答案不包含具体金额/费用，就是跑偏，**立即删掉**。
2. **反向检验** — 写完查询表后，逐条问自己：「这条查询的结果会出现在视频里吗？」
   如果答案是「不会」或「可能作为背景」，直接删。
3. **每主题 2-3 条** — 同一个费用主题从不同角度查（金额 / 构成 / 对比），提高命中率。
4. **个人数据单独标注** — 来自个人经历/截图的数据标注 📌，不浪费 RAG 查询。
5. **禁止关联发散** — 严禁「既然查了学签费用，顺便查一下申请流程/打工权限/入境文件」。
   这些是**其他视频**的主题，不是本视频的。

### 查询工程铁律（检索质量）

> ⚠️ **查询不精准 = 检索噪声 = 数据回填全靠猜 = 准确率归零。**
> RAG 检索不消耗 token，查询数量不受限，但每条查询的**精准度**决定数据质量。

#### 6 条规则

| # | 规则 | 说明 |
|---|------|------|
| Q1 | **用产品/项目真名** | BM25 靠精确词匹配，用官网上的产品名命中率翻倍 |
| Q2 | **每条查询瞄准 1 个数据点** | 「免费期多久」和「月费多少」是两条查询，不要塞一条里 |
| Q3 | **同主题查询用不同维度词拉开差异** | 同一银行：新移民计划 / 资格窗口 / 学生条件 / 月费金额 / 低成本档 / 转账费 — 6 个维度 = 6 条查询 |
| Q4 | **零重复词** | 同一条查询中不出现语义重复词（如 newcomer + new immigrant, banking + bank） |
| Q5 | **按实体拆分** | 5 家银行 = 5 组查询，每组内部按维度拆。不要写 1 条查询覆盖所有银行 |
| Q6 | **数量不限，精度优先** | RAG 查询不花 token，宁可多查也不要因为省查询数而写模糊查询 |

#### 反模式对照表

| ❌ 错误写法 | 问题 | ✅ 正确写法 |
|------------|------|------------|
| `"newcomer banking account open bank Canada new immigrant"` | 关键词堆砌：newcomer/new immigrant 重复，banking/bank 重复，BM25 TF-IDF 被稀释 | `"no-cost account eligible newcomer first year Canada bank"` |
| `"newcomer new to Canada program banking account offer BMO"` | 没用产品名：BMO 官网写的是 "NewStart Program"，这条查询匹配不上 | `"BMO NewStart Program newcomer chequing fee waiver two years"` |
| `"chequing account monthly fee plan waive minimum balance RBC"` (5 家银行只换名字) | 同质化：5 条查询只换银行名，返回 chunk 高度重叠 | 每家按维度拆：月费金额 / 免月费余额 / 低成本档 / 学生条件 — 不同查询打不同页面 |
| `"big five banks Canada RBC TD BMO Scotiabank CIBC"` | 太泛：所有页面都能匹配，等于没查 | 删掉，改为按银行逐个查具体产品 |
| `"e-Transfer Interac fee ATM withdrawal non-BMO transaction charge BMO"` | 一条塞了 3 个数据点（e-Transfer + ATM + 交易费） | 拆成：`"BMO Interac e-Transfer send receive fee included"` + `"BMO non-BMO ATM withdrawal charge"` |

#### 分组规则

> 查询表按**实体**分组（每家银行一组），不按功能维度分组。
> 每组内按数据点维度排列，保证同组查询之间有明确差异。

```
❌ 旧分组（按功能）:           ✅ 新分组（按实体）:
 D. 五大行新移民产品             C. BMO（新移民+学生+费用）
   10. BMO 新移民                  8. BMO NewStart 免费期
   11. RBC 新移民                  9. BMO NewStart 资格窗口
   12. TD 新移民                   10. BMO 学生账户
 E. 五大行费用                     11. BMO 月费条件
   15. BMO 费用                    12. BMO 低成本档
   16. RBC 费用                    13. BMO 转账费
 F. 五大行转账费                 D. CIBC（新移民+学生+费用）
   21. BMO 转账                    ...
   22. RBC 转账
```

### 从研究到子弹

研究完成后，Agent 从 5 步中提取"子弹"（短视频选题）：

- **1 个主题 = 1 颗子弹 = 1 条视频**
- 每颗子弹必须有完整的 S1→S2→S3→S4→S5 链条
- 链条断了的主题不出视频，回 research 补研究

### 执行 RAG 检索

> research.md 里的查询表直接作为 cite_rag.py 的输入，不需要单独的 queries.md。

```powershell
# // turbo
# cwd: textbook-rag/
# 单 collection（移民政策类）
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --queries data/short-videos/{slug}/{slug}-research.md `
  --collection ca_federal `
  --output data/short-videos/{slug}/sources.json

# 多 collection（银行/金融类需要 ca_fcac）
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --queries data/short-videos/{slug}/{slug}-research.md `
  --collection ca_federal ca_fcac `
  --output data/short-videos/{slug}/sources.json
```

> **Collection 选择指南**:
> | 主题类别 | Collection(s) |
> |---------|---------------|
> | 移民/签证/EE/PNP | `ca_federal` |
> | 银行/信用卡/金融（监管层） | `ca_federal ca_fcac` |
> | 银行/信用卡/金融（五大行产品） | `ca_federal ca_fcac ca_bank_bmo ca_bank_cibc ca_bank_rbc ca_bank_scotiabank ca_bank_td` |
> | 省移民项目 | `ca_federal ca_ontario` / `ca_bc` 等 |

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

**触发条件**: 主题信息点 > 3 个，单集逻辑链无法完整覆盖

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
- 每集聚焦 1 个核心问题，逻辑链完整
- 每集有独立钩子

---

## Step 1: (已合并入 Step 0.3)

> RAG 数据探索已整合进 Step 0.3「主题分层研究」。
> RAG 查询表内嵌于 `{slug}-research.md`，`sources.json` 在研究阶段一并产出。

---

## Step 2: storyline.md — 唯一数据源（基于已探索的数据）

**触发 Skill**: `video-storyline`

> ⚠️ **storyline.md 是整条视频的唯一数据源 (Single Source of Truth)。**
> 所有数据必须来自 Step 0.3 的 sources.json + 原文。**绝对禁止凭记忆/推测填写任何数据。**
> slides.json / script.txt **不再手写**，由 parser 从 storyline.md 自动生成。

### storyline.md 格式规范

#### 元数据区（文件顶部）

```markdown
# 视频主标题

> **系列**: 系列名 (N/M)
> **作者**: 频道名
> **模板**: competitor-gold
> **布局**: competitor
> **时长**: 70-80秒
```

| 字段 | 必填 | 说明 |
|------|------|------|
| H1 标题 | ✅ | 视频主标题 |
| 系列 | ✅ | 系列名 + 集号 |
| 作者 | ✅ | 频道名 |
| 模板 | ❌ | 默认 `competitor-gold` |
| 布局 | ❌ | 默认 `competitor` |
| 时长 | ❌ | 参考用，不影响渲染 |

#### Slide 区（每个 `## [type]` 为一页）

标题格式: `## [slide_type] 显示标题`

| type | 用途 | 必须 | 专属字段 |
|------|------|------|---------|
| `cover` | 封面 | ✅ | `**副标题**`, `**钩子数字**`, `**钩子单位**` |
| `argument` | 论点页 | ✅ | 表格 |
| `evidence` | 数据页 | ❌ | 表格 |
| `preview` | 互动收尾 + 下期预告 | ✅ | `**内容**` |

> **收尾规则**: `[preview]` 之后必须有引用来源 slide（见下方铁律），然后是 `📋` 汇总区。

> 🔗 **引用来源 slide 铁律（每个 storyline 必须有）：**
>
> 1. **位置**: `[preview]` 之后、`📋 引用来源汇总` 之前
> 2. **类型**: `[argument]`，标题为 `引用来源` 或 `引用来源 (1/N)` `(2/N)`（URL 多时分页）
> 3. **表格格式**: 4 列 — `中文名 | 英文名 | 说明 | 链接`
> 4. **URL 必须真实**: 每个链接必须来自 storyline 上方实际使用的 `**来源**:` URL，**禁止编造或简化**
> 5. **同机构合并行**: 同一机构多个 URL 时，第一行填中文名/英文名，后续行留空（视觉分组）
> 6. **必须有台词**: 如 "本期数据均来自官方网站，完整链接在屏幕上"
> 7. **去重**: URL 在多个 slide 重复引用时，引用来源表中只列一次

#### 通用字段（每页都可用）

| 字段 | 格式 | 说明 |
|------|------|------|
| `**台词**:` | **逐句换行** | → TTS 语音 + 字幕。每行 = 1条字幕卡 = 1段TTS音频 |
| `**引用**:` | 单行英文 | 引用块显示的官方原文 |
| `**来源**:` | URL | 右上角水印 URL |
| `**本地**:` | .md 路径 | RAG 本地源文件路径（仅供检查，不渲染） |

> **台词换行规则：**
> - 每行一句话，结尾带句号/问号
> - 每行对应视频中一条字幕卡片
> - TTS 引擎逐行生成音频片段，行间自动加短停顿
> - 空行会被忽略

> ⚠️ **表格引用 1:1 铁律：**
> - 表格中每一行数据必须有独立的引用来源
> - 5 家银行对比表 = 5 条引用（每家银行一条），不能合并成 1 条
> - 引用格式：`**引用 N**: "原文"` + `**来源**: URL`，N 从 1 开始编号
> - 底部「📋 引用来源汇总」表也必须覆盖每一行数据

> 🚫 **零编造铁律（最高优先级）：**
> - **表格中每一个数据格**（金额、期限、条件、账户名等）都必须能在对应的 `**引用 N**:` 原文中找到直接依据
> - 引用原文里没有明确写的数据 → 该格填「待查」，**绝不猜测、推算、凑数**
> - 台词中引用的具体数字（月费、年限、年龄等）必须与表格一致，表格中标「待查」的数据不得出现在台词里
> - **典型违规案例**：
>   - ❌ 源数据只写 "monthly fee will be charged"，Agent 填 "\$4.95" → **编造金额**
>   - ❌ 源数据只写 "eligible clients"，Agent 填 "落地1年内" → **编造资格窗口**
>   - ❌ 源数据写的是 A 产品价格，Agent 填到 B 产品行 → **张冠李戴**
>   - ✅ 源数据没提到具体金额 → 填「待查」
> - **逐格审计流程**：写完表格后，Agent 必须逐格对照引用原文，任何无法在引用中找到原文的格子立即改为「待查」

#### 表格数据（argument/evidence 用）

标准 Markdown 表格，直接渲染到 slide：

```markdown
| 维度 | EE路 | 纸质路 |
|------|------|-------|
| CRS加分 | **+600分** | 无 |
```

> ⚠️ **表格中 `$` 必须转义为 `\$`。**
> Markdown 渲染器会把两个 `$` 之间的内容当 LaTeX 公式，导致列合并、内容消失。
>
> ```markdown
> ❌ | BMO | $17.95 | $4,000 |     ← "$17.95" 和 "$4,000" 之间被当成公式
> ✅ | BMO | \$17.95 | \$4,000 |   ← 正常显示
> ```
### storyline.md 完整示例

```markdown
# 省提名两条路，选错多等半年

> **系列**: 省提名全解析 (1/3)
> **作者**: 枫叶移民说
> **模板**: competitor-gold

---

## [cover] 省提名两条路

**副标题**: 选错了要多等半年

**台词**:
省提名有两条路。
选错了要多等半年。

---

## [argument] 省提名是两级审批

| 阶段 | 审核方 | 产出 |
|------|--------|------|
| 第一步 | 省政府 | 提名证书 |
| 第二步 | 联邦IRCC | PR永久居民 |

**引用**: "There are 2 ways to apply for permanent residence through the PNP."
**来源**: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees.html
**本地**: data/ca_federal/provincial-nominees.md

**台词**:
省提名不是拿到就完事。
它是两级审批。
第一步，省政府审核你是否符合该省需要，拿到提名证书。
第二步，联邦审核安全、医疗、背景调查，才能拿到PR。
记住，提名不等于PR，拿到提名只完成了第一步。

---

## [preview] 下期预告

**内容**: 下期讲省提名纸质路和EE路的真实处理时间

**台词**:
你符合EE资格吗？评论区告诉我你的情况。
下期我会讲，纸质路和EE路实际处理时间差多少。

---

## [argument] 引用来源

| 中文名 | 英文名 | 说明 | 链接 |
|--------|--------|------|------|
| 加拿大联邦政府 | IRCC | 省提名项目总览 | https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/provincial-nominees.html |

**台词**:
本期数据均来自加拿大联邦政府官网。
完整链接在屏幕上，你可以自己去核实。

---

## 📋 引用来源汇总
> 此区域仅供参考，不参与视频渲染。parser 自动跳过。

| # | 断言 | 引用原文 | 来源URL |
|---|------|----------|--------|
| 1 | ... | "..." | https://... |
```

### 解读型台词铁律

> **台词是解读，不是播报。表格放画面，嘴巴负责告诉观众"这意味着什么"。**
> 念数据 = 观众划走 = 完播率归零。

#### 每页 slide 的逻辑链（5 步，缺一不可）

| 步骤 | 作用 | 示例 |
|------|------|------|
| ① **数据** | 放表格/数字，画面展示 | "2026年CEC 8轮，分数线507-515" |
| ② **发现问题** | 从数据中看出什么不对劲 | "分数线在跳，510分3月能上4月被刷" |
| ③ **分析原因** | 为什么会这样 | "因为IRCC每轮邀请人数不同，2000人和8000人差4倍" |
| ④ **预测风险** | 接下来可能怎样 | "如果邀请人数继续缩，分数线可能突破515" |
| ⑤ **给出方案** | 观众该怎么做 | "别卡着507准备，至少520以上才有安全边际" |

> **光有数据不行，必须能发现问题。**
> Agent 必须独立完成 ②-⑤ 的推导，不能只列数据等用户提醒。
> 如果 Agent 写不出 ②（发现问题），说明对数据理解不够，必须回 Step 0.3 补充研究。

#### 台词风格对照

| 播报型（禁止） | 解读型（目标） |
|----------------|---------------|
| "2026年CEC抽了8轮，最低507最高515" | "我翻完8轮数据发现一个规律——分数降了，但名额也缩了" |
| "2025年起IRCC取消了通用轮" | "2025年规则变了，光拼分数不够了，你得搞清自己走哪条赛道" |
| "法语393，医疗467，技工477" | "定向类别是另一个世界，法语比CEC低了整整100分" |
| "再看趋势" "先看数据" | "但更值得注意的是……" "很多人没意识到……" |

#### 视角规则

- **必须有"我"** — "我翻了官网数据" "我注意到" "我的判断是"
- **必须有"你"** — "这对你意味着" "你的情况是" "你该怎么判断"
- **禁止纯第三人称** — "IRCC 公布了……" 必须接 "这说明……"

### 逻辑链完整性检查

- 信息点 ≤ 3 个（超过必须拆集）
- slides ≤ 12 张（含封面 + 结尾）
- **每个判断必须有因果** — "分数降了"→ 必须接"因为……" 或"这意味着……"
- **不跳步** — 观众没有前置知识，每个概念首次出现必须有 1 句解释
- 台词总字数无硬上限（逻辑链讲透比卡秒数重要）

### 完成条件

- `storyline.md` 存在且格式合规
- 第一页是 `[cover]`，含 3 秒钩子
- **所有数字/日期/费用来自 sources.json 原文**（不允许凭记忆）
- 每个数据页有 `**引用**` + `**来源**`
- **表格引用 1:1** — 表格行数 = 引用条数（5行数据 = 5条引用，不允许合并为1条）
- 每页有 `**台词**`（逐句换行，解读型风格）
- **台词中判断句 + 翻译句占比 50% 以上**
- **禁止重复台词（铁律 6）** — 逐页扫描所有 `**台词**:` 块，同一关键短语（≥6字）出现在 2+ 个 slide 中即违规。换说法复述也算重复（如 A页"25岁以下直接免费" + B页"CIBC靠年龄判定，不需要学生证明" → B页必须换角度表达）。发现重复必须合并到信息首次出现的 slide，后续 slide 改用新角度或删除
- 信息点 ≤ 3，slides ≤ 12（不含引用来源页）
- 引用来源汇总表存在，条数 ≥ 所有表格行数之和
- **引用来源 slide 存在** — `[preview]` 之后有 `[argument] 引用来源` slide，列出所有 RAG 来源 URL（中文名 | 英文名 | 说明 | 完整链接），URL 数多时分页

> **storyline.md 是唯一数据源。不再手写 slides.json 和 script.txt。**

---

## Step 2.5: 硬核度审计 (Quality Gate)

**执行者**: Agent 自检

> **核心问题**: 台词是在**解读数据**还是在**念数据**？逻辑链条是否完整？

### 7 维评估标准

| 维度                 | 定义                   | 及格线  |
| -------------------- | ---------------------- | ------- |
| **独家数据**   | 具体数字/日期/门槛     | ≥ 5/10 |
| **反直觉洞察** | 打破常见误解           | ≥ 5/10 |
| **可操作性**   | 观众看完能立刻做点什么 | ≥ 4/10 |
| **信息密度**   | 每秒有效信息量，无废话 | ≥ 5/10 |
| **证据强度**   | 每个断言有官方来源     | ≥ 7/10 |
| **解读度**     | 每个数据点后有"意味着什么"的判断句 | ≥ 6/10 |
| **逻辑链**     | 每个判断有因果，不跳步不断链 | ≥ 7/10 |
| **引用覆盖**   | 表格行数 = 引用条数（1:1 映射） | = 100% |

### 审计流程

1. **逐论点标注** — 🟢硬核 / 🟡科普 / 🔴水句 / 📢播报
2. **数水句比例** — 🔴 占比 > 20% → 必须重写
3. **数播报比例** — 📢 占比 > 30% → 必须改写为解读型
4. **数据点计数** — 具体数字 < 3 个 → 必须从 sources.json 补充
5. **决策工具检查** — 是否有"你该怎么做"的判断依据
6. **解读句检查** — 每个数据 slide 至少 1 句"意味着/说明/翻译一下"
7. **逻辑链检查** — 逐页检查：前一页的结论是否引出后一页的问题
8. **引用覆盖检查** — 逐表检查：表格行数 = 引用条数，发现 N行1引 立即修复

### 常见水句模式（必须砍掉或替换）

| 模式       | 示例                     | 处理               |
| ---------- | ------------------------ | ------------------ |
| 纯定义句   | "被选中了就叫省提名"     | 删除               |
| 无数据列举 | "通用轮次、项目定向轮次" | 合并为带数据的     |
| 空过渡     | "关键区别来了"           | 删除或替换为信息句 |
| 重复强调   | 同一论点说两次           | 只保留更强版本     |
| 车轱辘话   | A页"25岁以下直接免费" + B页"25岁以下直接免费，不需要学生证明" | **铁律6违规 — 合并到首次出现的 slide，后续 slide 必须换角度** |
| 跨页复读   | 台词和表格说同一件事     | 台词解读，表格展示数据，禁止念表格 |
| 换皮重复   | A页"毕业后还给你12个月缓冲期" + B页"毕业之后还多一年过渡" | **铁律6违规 — 语义相同换说法也是重复，只留一处** |
| 引用页撞车 | 引用来源(1/2)"链接在屏幕上" + 引用来源(2/2)"链接在屏幕上" | **铁律6违规 — 连续 slide 台词不能相同，第二页必须换表述** |

### 常见播报模式（必须改写为解读型）

> ⚠️ **播报有信息量但没有观点，观众感觉在听新闻联播。**

| 模式 | 示例 | 处理 |
| ---- | ---- | ---- |
| 念表格 | "1月8000人511分，2月6000人509分" | 只说结论，数据放画面 |
| 无观点过渡 | "再看趋势" "先看数据" | 替换为判断句 |
| 纯客观陈述 | "IRCC取消了通用轮" | 加"我/你"视角 |
| 罗列不归纳 | "法语393，医疗467，技工477" | 一句话归纳 |
| 无因果数据 | "从561降到507" | 加解读："不是放水，是分流" |

### 逻辑链断裂检测（必须修复）

> ⚠️ **逻辑链断了，视频多短都没用。**

| 断裂类型 | 示例 | 修复 |
| -------- | ---- | ---- |
| 跳步 | 突然提到CEC但没解释是什么 | 首次出现必须 1 句解释 |
| 无因果 | "分数线降了" → 直接下一页 | 必须接"因为……"或"这说明……" |
| 结论无支撑 | "结论很明确，分数线在下降" | 必须有数据或逻辑推导到这个结论 |
| 观点悬空 | 给了判断但没说对观众意味着什么 | 必须接"所以你应该……" |
| **跨页重复（铁律6）** | **两个 slide 的台词传达同一个观点/数据/建议，即使措辞不同** | **合并到首次出现的 slide；后续 slide 必须换角度或删除。写完 storyline 后必须逐页交叉扫描台词，发现语义重复立即修复** |

### 判定等级

| 等级             | 条件                     | 动作                      |
| ---------------- | ------------------------ | ------------------------- |
| 🟢**硬核** | 8 维全部及格 + 🔴 ≤ 10% + 📢 ≤ 20% | 继续 Step 3               |
| 🟡**科普** | 1-2 维不及格             | 修改 storyline 后重新审计 |
| 🔴**水文** | 3+ 维不及格              | 回 Step 2 重写            |

### 完成条件

- 审计结果为 🟢 **硬核**
- 具体数字 ≥ 3 个
- 🔴 水句占比 ≤ 10%
- 📢 播报句占比 ≤ 20%
- 逻辑链无断裂
- 每个数据 slide 至少 1 句解读句

---

## Step 3: 自动解析（Parser 自动完成，无需手动操作）

> ⚠️ **此步骤由 `storyline-parser.js` 自动完成。**
> 用户无需手动创建 slides.json 或 script.txt。

Parser 从 `storyline.md` 自动生成：

| 输出 | 说明 |
|------|------|
| `SlideData[]` | slide 数组（type, title, table, points, content, citation, source） |
| `narration[]` | 台词数组（每个 slide 的逐句台词，用于 TTS + 字幕） |

### Parser 输出 Schema

```javascript
{
  type: "argument",           // ← [type]
  title: "省提名是两级审批",    // ← H2 标题
  subtitle: "选错了要多等半年", // ← **副标题** (cover only)
  table: { headers, rows },   // ← markdown 表格
  points: ["..."],            // ← 列表 (summary only)
  content: "...",             // ← **内容** (cta/preview)
  citation: "...",            // ← **引用**
  source: "https://...",      // ← **来源**
  hookNumber: "600",          // ← **钩子数字** (cover only)
  hookUnit: "CRS加分",        // ← **钩子单位** (cover only)
  narration: [                // ← **台词** 逐行 → 字幕卡数组
    "省提名不是拿到就完事。",
    "它是两级审批。",
  ]
}
```

### 内容规范（在 storyline.md 中遵守）

1. **论点+证据配对** — `[argument]` 后可紧跟 `[evidence]`
2. **每页必须有 `**来源**`** — 完整 URL
3. **禁止 emoji** — 标题、表格、台词不加 emoji
4. **缩写词必须解释** — 首次出现用 `EE（快速通道）` 格式
5. **文本中可用 `**加粗**`** — 渲染时变为金色高亮

---

## Step 4: (已废弃 — 台词已内嵌于 storyline.md)

> `script.txt` 不再手写。台词直接写在 storyline.md 每页的 `**台词**:` 字段中。

### TTS 友好规范（在 storyline.md 台词中遵守）

> ⚠️ **台词质量决定 TTS 质量。合成前自动质检，违规会警告。**

| # | 规则 | 罚则 | 示例 |
|---|------|------|------|
| R1 | **标点间 ≤18 个中文字** | 质检警告 | “这个分数线在跳，510分三月能上四月被刷” → 加逗号拆开 |
| R2 | **禁止破折号** `——` `--` | 质检警告 | “致命缺陷——” → 改逗号 |
| R3 | **每句 ≤50 字符** | 质检警告 | 太长的句子拆成两行 |
| R4 | **长中文句必须有标点** | 质检警告 | “分数线降了但竞争更激烈了” → 加逗号 |
| 5 | **中英文/数字不加空格** | - | `500分` ✅ `500 分` ❌ |
| 6 | **口语数字** | - | 用“两”不用“二” |
| 7 | **每行 = 一句 = 一条字幕卡** | - | 行间自动加停顿 |

> 💡 R1-R4 由 `synthesize.py` 内置 `_precheck_text()` 自动检查，合成前输出警告。
> 参考来源: `ai-video-director` skill 的 `check_script.py` 8 条规则。

---

## Step 5: TTS 语音合成 → `narration/`

**执行脚本**: `synthesize.py` (v2)

```powershell
# Step 5: 合成（火山引擎 咪仔 — 默认）
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend volcano `
  --voice zh_female_mizai_uranus_bigtts `
  --gap 300 `
  --slide-gap 800 `
  --fade 80
```

```powershell
# 降级 1: Edge TTS（免费，无需 API Key）
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend edge `
  --voice zh-CN-XiaoxiaoNeural `
  --gap 300 `
  --slide-gap 800 `
  --fade 80
```

```powershell
# 降级 2: CosyVoice 本地声音复刻
# 先启动服务: uv run .agent/workflows/short-video/scripts/cosyvoice_server.py
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend cosyvoice `
  --gap 300 `
  --slide-gap 800 `
  --fade 80
```

```powershell
# 降级 3: 腾讯云预设音色
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/narration/ `
  --backend tencent --voice 101007
```

### 音频处理管线

```
台词质检 → 逐句 TTS → 重采样 48kHz → 截尾部喘息
  → slide 边界 fade → 拼接(句间 300ms + 换页 800ms)
  → loudnorm -16LUFS(全局) → narration.wav + timestamps.json
```

- **采样率**: 48000Hz（Volcano 24kHz × 2 整数倍重采样）
- **前置静音**: 150ms 防止编码器截掉开头
- **后置静音**: 300ms 防止截断最后一个字
- **时间戳**: 基于每句实际音频时长计算（不再按字数比例估算）
- **字幕清洗**: 只去句末标点和括号，保留逗号和顿号保持可读性

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

### 字号规范（手机端优先）

> ⚠️ 所有字号针对 1920×1080 画布，手机竖屏观看时等效缩小约 50%。

#### CoverSlide（封面页）

| 元素 | 字号 (px) | 字重 | 文件:行 |
|------|-----------|------|---------|
| 钩子大数字 hookNumber | 200 | 900 | CoverSlide.tsx:34 |
| 钩子单位 hookUnit | 32 | 600 | CoverSlide.tsx:46 |
| 主标题 title | 80 | 800 | CoverSlide.tsx:55 |
| 副标题 subtitle | 32 | 400 | CoverSlide.tsx:66 |
| 品牌水印 @作者 | 24 | — | CoverSlide.tsx:79 |

#### ContentSlide（内容页）

| 元素 | 字号 (px) | 字重 | 文件:行 |
|------|-----------|------|---------|
| 标题 heading | 56 | 800 | theme.ts:82 |
| 列表要点 points | 38 | — | ContentSlide.tsx:34 |
| 正文 (CTA/preview) | 48 | 700 | ContentSlide.tsx:49 |
| 正文 (非CTA) | 42 | 400 | ContentSlide.tsx:49 |
| 引用块 citation | 28 | italic | ContentSlide.tsx:69 |
| 品牌水印 @作者 | 24 | — | ContentSlide.tsx:83 |

#### 表格自适应密度（4 级）

| 密度 | 触发条件 | 表头 | 表体 | 行间距 |
|------|---------|------|------|--------|
| normal | 默认 | 32 | 36 | 16px 28px |
| dense | ≥4列 或 >4行 | 30 | 34 | 10px 18px |
| xDense | ≥6列 或 (≥5列×5行) | 26 | 30 | 8px 14px |
| **xxDense** | **≥8行** | **22** | **24** | **4px 10px** |

> slide 区域 880px，标题占 ~84px，表格可用 ~712px。
> xxDense 保证 11+ 行表格不溢出。
> URL 列单元格字号额外 -4px（最小 18px），启用 `word-break: break-all`。

#### SubtitleBar（字幕条）

| 元素 | 字号 (px) | 字重 | 文件:行 |
|------|-----------|------|---------|
| 字幕文字 | 44（固定） | 700 | SubtitleBar.tsx:20 |

> 字幕固定 44px，不随文字长度缩放，避免忽大忽小。

#### 全局

| 元素 | 值 | 文件:行 |
|------|-----|---------|
| 字体族 fontFamily | `'Inter', 'Noto Sans SC', system-ui, sans-serif` | theme.ts:42 |
| 画布宽 | 1920px | theme.ts:45 |
| 画布高 | 1080px | theme.ts:46 |
| 幻灯片区高 | 880px | theme.ts:47 |
| 字幕条高 | 200px | theme.ts:48 |

### 完成条件

- `output/final.mp4` 存在
- `output/final.mp4` 时长合理（无硬上限，逻辑链完整优先）

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
- [ ] **表格引用 1:1** — 每个表格的行数 = 引用条数
- [ ] 声音自然，数字/英文混排无机器人感
- [ ] 来源 URL 水印正确
- [ ] TikTok 字幕逐词高亮同步
- [ ] 结尾 `[preview]` 兼顾互动引导 + 下集预告（无单独 `[cta]` 重复）

### 自动发布到微信视频号

**执行脚本**: `publish_weixin.py`

> ⚠️ **首次使用必须先登录**（只需一次，登录态保存在本地 Chrome 用户数据中）。

```powershell
# Step 1: 首次登录（弹出浏览器，微信扫码）
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/publish_weixin.py --login-only
```

```powershell
# Step 2: 模拟上传（不实际发表，检查标题/描述是否正确）
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/publish_weixin.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --dry-run
```

```powershell
# Step 3: 正式发表
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/publish_weixin.py `
  --video data/short-videos/{slug}/output/final.mp4 `
  --storyline data/short-videos/{slug}/storyline.md `
  --tags "#加拿大移民 #加拿大留学 #留学费用"
```

> 💡 **原理**: 脚本使用 Playwright 操作 `channels.weixin.qq.com` 视频号助手后台。
> 标题/描述/标签从 `storyline.md` 自动提取，无需手动输入。
> 登录态保存在 `.agent/workflows/short-video/browser-data/` 目录，约 30 天有效。

> ⚠️ **注意事项**:
> - 微信视频号没有官方上传 API，脚本通过浏览器自动化实现
> - 微信可能更新页面结构导致选择器失效，需要定期维护
> - 高频自动操作可能触发风控，建议每次上传间隔 ≥ 5 分钟
> - 如果自动发表失败，脚本会保存截图并等待手动操作

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

> `slides.json` 和 `script.txt` **不再手写**，由 `storyline-parser.js` 从 storyline.md 自动生成。

### Scripts

| 脚本                     | 输入              | 输出                            |
| ------------------------ | ----------------- | ------------------------------- |
| `cite_rag.py`          | research.md       | sources.json                    |
| `storyline-parser.js`  | storyline.md      | SlideData[] + narration[]       |
| `register_voice.py`    | voice-sample.wav  | FastVoiceType (腾讯云复刻音色 ID) |
| `synthesize.py`        | storyline.md + .env | narration.wav + timestamps.json |
| `render.mjs`           | storyline.md + narration/ | final.mp4               |
| `publish_weixin.py`    | final.mp4 + storyline.md | 微信视频号发布              |

**脚本间零依赖** — 每个脚本独立运行，通过文件系统通信。

### 已废弃

| 废弃项                | 替代                           |
| --------------------- | ------------------------------ |
| `compose_marp.py`   | Remotion 内置渲染              |
| `assemble_video.py` | Remotion render.mjs            |
| `slides.md` (Marp)  | storyline.md (统一格式)        |
| `slides.json` (手写) | parser 从 storyline.md 自动生成 |
| `script.txt` (手写)  | 台词内嵌于 storyline.md        |

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
│   └── timestamps.json          # 自动拆分多句 → 每条一个短分句
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
│   ├── cite_rag.py              # RAG 检索（--collection 直接指定 ChromaDB collection）
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

### 腾讯云 TTS 配置（降级 / 声音复刻）

1. 开通: https://console.cloud.tencent.com/tts
2. 开通声音复刻: https://console.cloud.tencent.com/tts (需额外开通 VRS 服务)
3. `.env` 添加: `SecretId=AKIDxxxxxx` + `SecretKey=xxxxxxxx`
4. 注册声音: `uv run .agent/workflows/short-video/scripts/register_voice.py`
5. 记录返回的 `FastVoiceType`，在 synthesize.py 中使用 `--backend tencent-clone --voice <ID>`
