---
description: 短视频生产工作流 v8 — 信任驱动 + Marp + 腾讯云 TTS
name: short-video
version: 8.0.0
trigger: /short-video
---

# 短视频生产工作流 v8 — 信任驱动

从 RAG 知识库一键生成微信视频号竖屏短视频。

## 核心理念：信任 > 时长

> **视频的根本目的是增加用户信任度和专业感。**
> 每个论点必须有数据/事实做支撑。不在乎视频时长，只在乎说清楚。
> 宁可多花 30 秒把证据摆出来，也不要为了控制时长而省略论据。

**幻灯片结构原则**: 论点 → 证据交替
- 一张 slide 说论点/观点
- 下一张 slide 紧跟数据/事实/来源证明
- 每个主张都有出处，每个结论都有依据

**架构**: Trust-First + Marp slides + 腾讯云 TTS（精品音色 101007 智娜）

```
定题 → 故事线 (Skill) → RAG引用 (Script) → AI 设计 slides.md
  → 提取口播脚本 script.txt → Marp 渲染 PNG (Script)
  → TTS (Script) → 视频组装 (Script)
```

**核心特点**:
- **信任驱动**: 论点+证据配对，每个主张都有数据支撑
- **视觉层**: Marp 幻灯片（纯 .md，AI 自由设计样式/布局/配色）
- **TTS**: 腾讯云 TTS（降级: Edge TTS）
- **字幕**: 解耦架构 — 底部独立字幕条（无分隔线），不遮挡幻灯片内容
- **字幕去标点**: 语音保留标点（控制语调停顿），字幕显示去标点（更干净）

---

## Step 0: 定题

Agent 收到主题后，确认参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 画面比例 | 16:9 landscape | 横屏视频号 |
| 时长 | 不限制 | 说清楚为准，信任 > 时长 |
| 受众 | 华人移民/留学 | 内容定位 |
| TTS | 腾讯云 TTS (VoiceType 101007 智娜) | 降级: Edge TTS |

---

## Step 1: 叙事线设计 → `storyline.md`

**触发 Skill**: `video-storyline`

Agent 基于主题和自身知识构建叙事逻辑:
1. 定义核心问题（视频要回答什么）
2. 构建逻辑节点链（钩子 → 解释 → 洞察 → 行动 → 收尾）
3. **每个论点必须配对一个证据节点**（论点 → 证据交替）
4. **所有论点必须使用表格格式** — 每行只描述一个内容项，禁止使用 bullet list 罗列论点
5. **每个章节只能有一个论点表格** — 如果一个主题需要多个表格，必须拆成子章节（如 六A/六B/六C），每个子章节独立配证据和台词，确保 1:1 映射到 slide
6. 在每个数据断言处标注 `[需要引用: 描述]`
7. 生成引用需求清单表格，**RAG 查询建议列必须使用英文**

### 论点表格格式要求

论点部分统一用 markdown 表格，每行一个信息点：
```markdown
### 论点
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 信息点A | 数据A | 说明A |
| 信息点B | 数据B | 说明B |
```
- 列名根据内容自定义（如 指标/数值/含义、学历/分数/备注、策略/提升幅度/说明）
- **禁止** bullet list 罗列论点（`- xxx = **100** 分` ❌）
- 表格后可加 `> blockquote` 补充关键提醒

> ⚠️ **关键规则**: ChromaDB 中的数据全部是英文（来自 canada.ca 等官方网站），
> 中文查询的向量命中率极低（~33%）。`cite_rag.py` 会优先使用表格中的英文 query。
> 如果没有英文 query，将回退到中文 claim（不推荐）。

### 引用需求清单格式

```markdown
| # | 断言 | 需要的引用 | RAG 查询建议 (必须英文) |
|---|------|-----------|----------------------|
| 1 | ... | ... | "English query here" |
```

### 完成条件
- `storyline.md` 存在
- 逻辑节点因果链完整（无跳跃）
- **每个论点都有对应的证据/数据节点**
- **所有论点使用表格格式**（无 bullet list 论点）
- **每个章节只有一个论点表格**（多表格拆子章节）
- **禁止独立"常见误区"章节** — 误区/注意事项直接内联到对应详解章节的表格备注列中，不单独成章（会与前面内容重复）
- 所有数据断言有 `[需要引用]` 标记
- **引用需求清单的 RAG 查询建议列全部使用英文**

---

## Step 1.5: RAG 质量门禁 (Quality Gate)

**执行脚本**: `diagnose_rag_quality.py`

在生成 `sources.json` 之前，必须先验证 ChromaDB 数据质量。
此步骤确保所需的 book_ids 已入库、向量检索能命中正确文档。

```powershell
# // turbo
# cwd: textbook-rag/
uv run python scripts/diag/diagnose_rag_quality.py `
  --queries-file data/short-videos/{slug}/storyline.md `
  --output data/short-videos/{slug}/rag_report.json
```

### 通过条件 (全部满足才能继续)
- Phase 1: 期望 book_ids **全部存在** (0 missing)
- Phase 2: 向量命中率 ≥ 50%
- Phase 3/4: Engine API 返回的 `no_data_flag` 数量 = 0

### 不通过时
1. 检查 `rag_report.json` 中 `missing_books` 列表
2. 用 `ingest_urls.py` 或 `batch_ingest.py` 补充缺失数据
3. 重新跑 `diagnose_rag_quality.py` 直到通过
4. **禁止跳过此步骤直接生成 sources.json**

---

## Step 2: RAG 引用查找 → `sources.json`

**前置条件**: Step 1.5 质量门禁通过

**执行脚本**: `cite_rag.py`

从 storyline.md 的 `[需要引用]` 标记提取查询 → 精确搜索 RAG → 获取来源 URL。

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/cite_rag.py `
  --storyline data/short-videos/{slug}/storyline.md `
  --persona live-study-immigration `
  --output data/short-videos/{slug}/sources.json
```

### 完成条件
- `sources.json` 存在
- 每个 `[需要引用]` 标记都有对应来源（或标记为"未找到"）
- **如果有"未找到"或"低质量"的引用，必须暂停并提醒用户用 `ingest_urls.py` 入库缺失数据** — 不允许在缺少证据的情况下继续生产视频：
  ```powershell
  # 单页入库
  uv run python scripts/ingest/ingest_urls.py `
    --category federal-ircc --collection ca_federal --force `
    "https://www.canada.ca/en/..."
  # EE 轮次 JSON 数据入库
  uv run python scripts/ingest/ingest_urls.py `
    --ee-rounds --category federal-ircc --collection ca_federal --force
  ```
- 入库完成后重新跑 `cite_rag.py`，直到所有引用都有来源

---

## Step 3: AI 设计 Marp Slides → `slides/slides.md`

**执行者**: AI Agent（使用稳定模板 + 自由设计内容）

Agent 基于 `storyline.md` + `sources.json` 设计 Marp 幻灯片：
1. **论点 → 证据交替**: 一张 slide 说论点，下一张 slide 展示支撑数据/事实
2. 将 storyline 的每个逻辑节点转化为 slide 对（论点页 + 证据页）
3. **使用下方稳定模板**的 CSS 样式（Indigo-Violet 浅色主题），不要自行发明新样式
4. 横屏 16:9 尺寸 (`size: 1920x1080`)
5. **每一页都必须有来源 URL 水印**（包括总结页、互动页、预告页）
6. 总页数 **不限制**（说清楚为准，信任 > 时长）

### slides.md 稳定模板（强制使用）

复制以下 frontmatter + CSS 作为 `slides.md` 的开头，**不要修改样式部分**：

````markdown
---
marp: true
size: 1920x1080
theme: default
paginate: false
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&family=Noto+Sans+SC:wght@400;700;900&display=swap');
  /* ── 全局布局 ── */
  /* ══════ 页面：CSS Grid 五区布局（垂直居中） ══════
     画布 1920×1080  padding 60px 100px 20px
     URL 水印绝对定位，不占 Grid
     ─────────────────────────────────────
     Row 1  上方弹性留白    1fr    吸收多余空间（上）
     Row 2  标题 h2          auto   按内容
     Row 3  内容 table/ul    auto   按内容
     Row 4  下方弹性留白    1fr    吸收多余空间（下）
     Row 5  引用 blockquote  auto   贴底，自适应高度
     ════════════════════════════════════ */
  section {
    font-family: 'Inter', 'Noto Sans SC', sans-serif;
    background: linear-gradient(180deg, #ffffff 0%, #f5f7fb 100%); color: #1e293b;
    padding: 60px 100px 20px;
    display: grid !important;
    grid-template-rows: 1fr auto auto 1fr auto;
    grid-template-columns: 1fr;
    gap: 6px;
    overflow: hidden;
  }
  /* ── URL 水印（绝对定位，居中） ── */
  .source {
    position: absolute; top: 16px; left: 100px; right: 100px;
    text-align: center;
    font-size: 16px; color: rgba(100,116,139,0.4);
    font-family: 'Inter', monospace; letter-spacing: 0.5px;
    white-space: nowrap;
  }
  /* ── Zone 2: 标题 (Row 2, auto) ── */
  h1 {
    grid-row: 2; grid-column: 1;
    font-size: 56px; font-weight: 900; line-height: 1.15;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
    margin: 0; align-self: end;
  }
  h2 {
    grid-row: 2; grid-column: 1;
    font-size: 48px; font-weight: 800; color: #0f172a;
    padding-left: 0;
    margin: 0 0 16px 0; align-self: end;
  }
  h3 {
    grid-row: 3; grid-column: 1;
    font-size: 36px; font-weight: 700; color: #6366f1;
    margin: 0; align-self: start;
  }
  /* ── 强调 ── */
  strong { color: #6366f1 !important; -webkit-text-fill-color: #6366f1 !important; background: none !important; font-weight: 800; }
  em { color: #8b5cf6; font-style: normal; font-weight: 600; }
  /* ── Zone 3: 内容 (Row 3, auto) ── */
  table {
    grid-row: 3; grid-column: 1;
    width: 100% !important; min-width: 100%; border-collapse: collapse;
    margin: 0; background: transparent !important;
    align-self: start;
    border-radius: 8px; overflow: hidden;
  }
  th {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: #ffffff !important;
    padding: 8px 20px; font-size: 26px; font-weight: 700;
    text-align: left; border-bottom: none !important;
  }
  td {
    background: rgba(241,245,249,0.6) !important; color: #334155 !important;
    padding: 6px 20px; font-size: 26px;
    border-bottom: 1px solid #e2e8f0 !important;
  }
  td strong { color: #7c3aed !important; -webkit-text-fill-color: #7c3aed !important; background: none !important; }
  tr { background: transparent !important; }
  tr:nth-child(even) td { background: rgba(248,250,252,0.8) !important; }
  ul, ol {
    grid-row: 3; grid-column: 1;
    font-size: 32px; line-height: 1.8; margin: 0;
    align-self: start;
  }
  li { margin: 4px 0; }
  li::marker { color: #6366f1; }
  /* ── Zone 5: 引用 (Row 5, auto) ── */
  blockquote {
    grid-row: 5; grid-column: 1;
    border-left: 3px solid #8b5cf6; margin: 0;
    padding: 10px 20px; border-radius: 0 8px 8px 0;
    background: rgba(99,102,241,0.06);
    color: #64748b; font-size: 24px; line-height: 1.5;
    align-self: end; overflow: hidden;
  }
  blockquote::before, blockquote::after { content: none !important; display: none !important; }
  .accent { color: #f59e0b; }
  .green { color: #10b981; }
  /* ── 封面模式（H1 整页居中） ── */
  section.cover {
    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 50%, #f5f3ff 100%) !important;
    display: flex !important; justify-content: center; align-items: center;
    text-align: center;
  }
  section.cover h1 { font-size: 72px; align-self: center; }
  /* ── 紧凑模式（大表格，缩小 Zone 3 字号） ── */
  section.dense { padding: 100px 80px 16px; gap: 4px; }
  section.dense h2 { font-size: 40px; }
  section.dense th { padding: 4px 16px; font-size: 20px; }
  section.dense td { padding: 3px 16px; font-size: 20px; }
---
````

> **参考实现**: `data/short-videos/ee-crs-scoring/slides/slides.md`

### 内容规范（强制）
1. **论点+证据配对** — 每个论点 slide 后面紧跟一张证据 slide（数据表/对照表/来源原文摘要）
2. **论点 slide 必须用表格** — 论点页的核心信息用 markdown 表格呈现（每行一个内容项），与 storyline.md 格式一致，禁止 bullet list 罗列
3. **证据 slide 必须包含**: 具体数字、对照表、或官方来源原文摘要
3. **禁止 emoji** — 标题、表格、正文不加任何 emoji 图标
4. **缩写词必须解释** — 首次出现用 `EE（快速通道）`、`PNP（省提名）` 格式
5. **禁止未解释术语** — “交叉分”“NOC 00/0” 等必须换成大白话
6. **每页必须有来源 URL** — 用 `<div class="source">完整URL</div>` 放在每页末尾。**无例外**，包括总结页、互动页、预告页。没有具体 RAG 来源的页面使用该主题最相关的官方页面 URL
7. **来源 URL 完整** — 必须是完整 URL（`https://www.canada.ca/en/...`），禁止缩写
8. **来源水印位置** — CSS 已定义 `position: absolute; top: 16px; left/right: 100px`（居中半透明小字）
9. **一页一个概念** — 每个加分项/策略单独一页，不合并
10. **先讲前提** — 涉及资格要求时，先讲门槛再讲加分
11. **CTA 和预告分页** — 评论区互动和下期预告各占一页
12. **每页必须有 citation 文本** — 用 blockquote (`>`) 引用官方英文原文（不加中文翻译），从 `sources.json` 的 `source_context` 提取关键段落。每条引用至少 2-4 句官方原文，让观众可以直接验证
13. **URL 必须以 `.html` 结尾** — canada.ca 页面都有 `.html` 后缀，禁止省略
14. **数据必须交叉验证** — 所有数字（分数、满分、分数线）必须与 `sources.json` 中的 `source_context` 官方原文交叉核实，禁止凭记忆写数字
15. **重大政策变化单独一页** — 如 LMIA 取消加分、新增类别等影响广泛的政策变更必须单独一页重点说明，不能夹在其他内容里一笔带过

### 样式一致性规范（强制）
1. **总结/重点行必须用 `>` 引用** — 所有表格下方的总结文字、行动号召、提示信息统一用 blockquote 格式，不用裸文本或 `**bold**`
2. **大表格用 `dense` 类** — 超过 6 行的表格加 `<!-- _class: dense -->`，缩小 padding/字体防溢出
3. **禁止裸文本段落** — 幻灯片中所有信息必须装在组件内（标题/表格/列表/引用），不留裸的 `<p>` 段落
4. **证据页视觉区分** — 证据 slide 用不同背景色或边框，让观众一眼识别"这是数据支撑"

### 完成条件
- `slides/slides.md` 存在
- **每个论点 slide 后紧跟证据 slide**
- **每一页都有 `<div class="source">URL</div>` 水印**
- **每一页都有 blockquote citation 文本**（英文官方原文，无中文翻译）
- **所有 URL 以 `.html` 结尾**
- **所有数字已与 source_context 交叉验证**
- 含 Marp frontmatter (`marp: true`, `size: 1920x1080`)
- 使用稳定模板 CSS（不自行修改样式）

---

## Step 4: 提取口播脚本 → `script.txt`

**执行者**: Agent 直接编写（无 Skill 依赖）

Agent 从 `slides/slides.md` 提取每页的核心信息，编写 TTS 口播旁白：

### 编写规则
1. **一行 = 一段字幕** — 每行独立合成语音、独立显示字幕
2. **有 `|` 的行开新幻灯片，没有 `|` 的行延续上一张** — 多行共享同一张 slide，适合短视频字幕断句
3. **论点行 + 证据行配对** — 论点 slide 的口播说观点，证据 slide 的口播说"数据显示…"、"根据官方数据…"、"具体来说…"
4. **句间必须有衔接** — 每句话开头要有过渡词/引导词，形成自然对话流，禁止信息点硬切。示例：
   - "先来搞懂…"、"那这个分怎么算呢？"、"不过先别急"
   - "为什么这么低？"、"那怎么办？"、"还有一招"
   - "另外提醒一下"、"所以总结一下"、"下期咱们聊"
   - 论点→证据过渡: "具体数据是这样的"、"来看一下官方数据"、"有图有真相"
5. **说清楚、说明白** — 宁可多几个字也不要含糊。观点必须有结论，误区必须说清"错在哪、对的是什么"
6. **关键论点带原因** — 雅思口语风格：结论 + 简短原因，但不重复已知信息。`别为了加分去读博，因为硕士博士只差十五分` ✅ 。`加六百分，为什么这么猛？因为总分直接破千` ❌（废话）
7. 语气自然、口语化，像在跟朋友聊天
8. 有 RAG 来源的行标注 `[来源:URL]`（从 `sources.json` 取）
9. 无来源的常识行不标注
10. **幻灯片数 = 带 `|` 的行数**（不限制总数，说清楚为准）

### TTS 友好规范（强制）
1. **数字可用阿拉伯** — 现代 TTS（腾讯云 101007）能自然朗读阿拉伯数字，`500分`、`1200分` 均可直接使用
2. **中英文/数字不加空格** — `500分` ✅ `500 分` ❌；`搞懂CRS` ✅ `搞懂 CRS` ❌。空格会导致 TTS 卡顿停顿
3. **口语数字** — 用"两"不用"二"：`200` 读"两百" ✅；如手动写中文也用 `两百` 而非 `二百`
4. **用句号控制停顿** — 长句拆短句用句号，不要全用逗号：`入池是有门槛的。至少一年工作经验` ✅
5. **冒号改句号** — 冒号断句不稳定，改用句号：`有门槛的。至少…` ✅ `有门槛的：至少…` ❌

### 禁止事项
- ❌ 信息点罗列式旁白（"策略一…策略二…策略三…" 无衔接）
- ❌ 含糊结论（"常见误区：A和B" → 没说误区是什么）
- ❌ 问隐私信息（不要让用户在评论区分享年龄/学历/成绩）
- ❌ 数字格式不统一（同一个数在不同行一会儿写"五百"一会儿写"500"，保持一致即可）

### script.txt 格式

```
# 主题名
旁白文本 | [钩子]
旁白续行（同一张幻灯片，独立字幕）
旁白续行（同一张幻灯片，独立字幕）
旁白文本 | [来源:https://www.canada.ca/en/...]
旁白续行
旁白文本 | [数据]
旁白文本 | [洞察]
旁白文本 | [要点]
旁白文本 | [结尾]
旁白文本 | [互动]
旁白文本 | [预告]
```

> **规则**: 有 `|` 的行开新幻灯片（第 N 张），没有 `|` 的行延续上一张幻灯片。
> 每行独立合成语音 + 独立显示字幕，但共享同一张 slide 画面。

标签说明：`[钩子]` 开场、`[来源:URL]` RAG引用、`[数据]` 数据展示、`[洞察]` 分析、`[要点]` 重点、`[结尾]` 总结、`[互动]` 评论区引导、`[预告]` 下期预告

### 完成条件
- `script.txt` 存在
- 带 `|` 的行数 = slides.md 页数
- 格式: 有 `|` 的行为 `旁白文本 | [视觉提示]`，无 `|` 的行为纯旁白续行
- 每句开头有衔接词，整体读起来像一段连贯的口播

---

## Step 5: Marp 渲染 PNG

**执行脚本**: `compose_marp.py`

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/compose_marp.py `
  --slides data/short-videos/{slug}/slides/slides.md
```

### 完成条件
- `slides/slides.001.png` ~ `slides.0XX.png` 存在
- PNG 数量 = slides.md 页数

---

## Step 6: TTS 语音合成 → `narration/`

**执行脚本**: `synthesize.py`

默认使用**腾讯云 TTS**（精品音色 101007 智娜），双停顿模式：

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend tencent `
  --voice 101007 `
  --gap 300 `
  --slide-gap 800
```

### 音色选择

| 类型 | VoiceType | 名称 | 免费额度 | 适用场景 |
|------|-----------|------|----------|----------|
| 精品 | **101007** | 智娜（广告女声） | 800 万字 | 推荐，免费额度大，质量稳定 |
| 精品 | 101001 | 智瑜（温柔女声） | 800 万字 | 备选 |
| 大模型 | 301015 | 智小柔（温柔女声） | 10 万字 | 数字/英文混排更自然，额度少 |

> **环境变量**: 需要在 `.env` 中配置 `SecretId` 和 `SecretKey`（腾讯云 API 密钥）

降级方案（无网络/API）:
```powershell
uv run .agent/workflows/short-video/scripts/synthesize.py `
  --script data/short-videos/{slug}/script.txt `
  --output data/short-videos/{slug}/narration/ `
  --backend edge
```

### 音频参数
- **句间停顿**: 默认 300ms（`--gap 300`）— 同一张幻灯片内句子之间
- **换页停顿**: 默认 800ms（`--slide-gap 800`）— 切换幻灯片时
- **前置静音**: 自动加 150ms 防止 MP3 编码器截掉开头
- **拼接方式**: 全部转 44100Hz WAV，无损拼接后统一编码 MP3
- **字幕去标点**: 语音保留标点（控制语调），字幕文本自动去除中文标点

### 完成条件
- `narration/narration.mp3` 存在
- `narration/timestamps.json` 存在

---

## Step 7: 视频组装 → `output/final.mp4`

**执行脚本**: `assemble_video.py`

三步分离式组装（字幕与幻灯片完全解耦）：
1. 幻灯片 concat → 纯视频轨（无音频） + **底部 200px 字幕条**
2. 视频 + 音频 → 中间文件（无字幕）
3. ASS 字幕渲染到底部字幕条 → 最终 MP4

> **字幕解耦架构**: 幻灯片保持原始尺寸完整不动，底部加 200px 浅色字幕条（无分隔线）。字幕使用 ASS 格式精确定位，**FontSize=64**。分句后去除标点显示更干净。
> **字幕持续显示**: 每条字幕持续到下一条出现（无空白间隙），切换瞬间替换。

### 幻灯片切换
- **多行对应一张幻灯片** — 有 `|` 的行切换 slide，无 `|` 的行保持当前 slide
- 幻灯片在音频停顿期间**保持显示**，不插入暗场帧
- 停顿结束后直接切换到下一张，与下一句语音同步开始

```powershell
# // turbo
# cwd: textbook-rag/
uv run .agent/workflows/short-video/scripts/assemble_video.py `
  data/short-videos/{slug}/
```

> ⚠️ 目录结构约定:
> ```
> {slug}/
> ├── script.txt
> ├── narration/
> │   ├── narration.mp3
> │   └── timestamps.json
> └── slides/
>     ├── slides.001.png
>     ├── slides.002.png
>     └── ...
> ```

### 完成条件
- `output/final.mp4` 存在
- 时长不限（信任 > 时长）

---

## Step 8: 检查 & 发布

```powershell
# // turbo
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 `
  data/short-videos/{slug}/output/final.mp4
```

- [ ] 每个论点都有证据 slide 支撑
- [ ] 声音自然，数字/英文混排无机器人感
- [ ] 来源 URL 水印正确
- [ ] 字幕同步无偏移
- [ ] 观众看完会觉得"这个人很专业、有理有据"

上传微信视频号 → 标签 `#加拿大移民` `#程序员移民`

---

## 架构说明

### Skills (Agent 智能层)

| Skill | 职责 |
|-------|------|
| `video-storyline` | 叙事线设计 + 逻辑链构建 + 引用需求标注 |

> **Note**: `slides.md` 和 `script.txt` 均由 Agent 直接编写（规则内联于 Step 3/4），无独立 Skill。

### Scripts (自动化工具)

| 脚本 | 输入 | 输出 |
|------|------|------|
| `cite_rag.py` | storyline.md | sources.json (引用URL) |
| `synthesize.py` | script.txt + .env (腾讯云密钥) | narration.mp3 + timestamps.json |
| `compose_marp.py` | slides.md (AI 写的) | slides/*.png |
| `assemble_video.py` | script.txt + slides/ + narration/ | final.mp4 |

**脚本间零依赖** — 每个脚本独立运行，通过文件系统通信。

---

## 文件结构

```text
data/short-videos/{slug}/
├── storyline.md                 # Step 1: 叙事逻辑 (Skill)
├── sources.json                 # Step 2: RAG 引用 URL (Script)
├── slides/                      # Step 3-5: Marp 幻灯片
│   ├── slides.md                #   AI 自由设计的 Marp 源文件 (Step 3)
│   ├── slides.001.png           #   渲染后的 slide 图片 (Step 5)
│   └── ...
├── script.txt                   # Step 4: 口播脚本 (从 slides 提取)
├── narration/                   # Step 6: TTS
│   ├── narration.mp3
│   └── timestamps.json
└── output/                      # Step 7: 最终视频
    ├── final.mp4
    └── subtitles.srt
```

---

## 依赖

```powershell
npm install -g @marp-team/marp-cli   # Marp 渲染 (或 npx 自动安装)
pip install tencentcloud-sdk-python  # 腾讯云 TTS (推荐)
pip install edge-tts                 # Edge TTS (降级方案)
pip install loguru python-dotenv     # 日志 + 环境变量
# ffmpeg 必须在 PATH 中
```

### 腾讯云 TTS 配置

1. 开通语音合成: https://console.cloud.tencent.com/tts
2. 领取免费资源包（精品 800 万字 + 大模型 10 万字）
3. 创建 API 密钥: https://console.cloud.tencent.com/cam/capi
4. 在 `.env` 中添加:
```
SecretId=AKIDxxxxxx
SecretKey=xxxxxxxx
```


