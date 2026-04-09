# Sprint Demo — 展示日冲刺 (2026-04-10)

> 目标：明天展示前的高优先级冲刺。按 **impact/effort** 排序，聚焦 6 个任务让 demo 效果最大化。
>
> 前置条件：S1 ✅ + S2 🚧 (21/30) + Hotfix 🚧 (6/7) + Acquisition 🚧 (5/13) 已具备基本可用的 RAG 管线。
>
> Project Brief 对齐：`docs/project-brief.md` 中明确要求「每个回答包含 source tracking + trustability indicator」「产出 narrative summaries + tables + graphs」

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 全书搜索 | 3 | 2h | 新对话默认扫描所有 PDF，通过 citation 跳转 |
| T2 暖色主题 | 1 | 0.5h | DeepTutor `#FAF9F6` 米色 light 主题迁移 |
| T3 建议问题 | 2 | 2h | Ottawa RAG-Project 120+ 问题 → WelcomeScreen |
| T4 Citation 统一 | 3 | 2.5h | 合并 SourceCard/CitationChip + Score 徽章 |
| T5 Report 精简版 | 4 | 3h | S8 17 stories 精简到 4 stories MVP |
| T6 Admin/User 分离 | 1 | 0.5h | 侧栏按角色显隐 |
| **合计** | **14** | **10.5h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 模块归属 | 新文件在 `features/` 对应模块下；Report 模块新建 `features/report/` |
| G2 | Project Brief 对齐 | T4 score → trustability indicator；T5 report → narrative summaries |
| G3 | 不破坏现有功能 | 保留 book picker 作为可选过滤，不删除 |

---

## [DM-T1] 全书搜索（新对话默认扫描全部 PDF）

### [DM-T1-01] ChatPage 默认全书模式

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: 新对话时默认 `sessionBookIds = 所有已 ingest 书籍`，跳过强制选书步骤。保留 BookPicker 作为可选过滤器（用户可点击收窄范围）。

**当前**: `ChatPage.tsx` 要求先选书再对话；`sessionBookIds` 为空时显示 BookPicker。
**改为**: 页面加载时 `sessionBookIds = books.map(b => b.id)`；BookPicker 变为收缩/筛选工具。

**验收标准**:
- [ ] 进入 `/chat` 后直接进入对话模式，无需选书
- [ ] `sessionBookIds` 默认包含所有已 ingest 的书
- [ ] ChatHeader 显示 "Searching all N documents" 或列出具体书名
- [ ] 旧有 BookPicker 按钮保留但改为可选 Filter

**文件**: `features/chat/ChatPage.tsx`

### [DM-T1-02] ChatPanel 引擎全书查询

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**描述**: 当 `sessionBookIds` 包含全部书时，`filters` 不传 `book_id_strings`（让后端搜索全库）。

**当前**: `ChatPanel.tsx:217-220` 总是传 `filters.book_id_strings`。
**改为**: 当 `sessionBookIds` 等于全部 `books` 时，`filters = undefined`（搜全库）。

**验收标准**:
- [ ] 全书模式下后端搜索不限定 book_id
- [ ] 筛选模式下仍然按选定书籍过滤

**文件**: `features/chat/panel/ChatPanel.tsx`

### [DM-T1-03] WelcomeScreen 全库提示

**类型**: Frontend · **优先级**: P1 · **预估**: 0.5h

**描述**: 更新 WelcomeScreen 文案，显示全库搜索状态和文档数量。

**当前**: "answers are grounded in your selected N books"
**改为**: "Searching across all N Ottawa Economic Development reports (Q1 2022 – Q4 2024)"

**验收标准**:
- [ ] 显示文档总数和覆盖范围
- [ ] 当用户筛选后显示 "Searching N of M documents"

**文件**: `features/chat/panel/WelcomeScreen.tsx`

---

## [DM-T2] 暖色 Light 主题（DeepTutor 米色迁移）

### [DM-T2-01] Light 主题 CSS 变量更新

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**描述**: 将 `:root` light 主题从冷白色切换为 DeepTutor 的暖米色方案。保留 Ottawa 蓝 `#004890` 作为 primary（政府品牌色）。Dark 主题不变。

**变更** (globals.css `:root`):
```css
/* Before */                     /* After (DeepTutor warm) */
--background: #ffffff;       →   --background: #FAF9F6;
--card: #ffffff;             →   --card: #FFFFFF;  /* 保持，卡片稍亮于背景 */
--secondary: #f1f5f9;        →   --secondary: #F0EDE7;
--muted: #f1f5f9;            →   --muted: #F0EDE7;
--muted-foreground: #64748b; →   --muted-foreground: #8B8580;
--accent: #f1f5f9;           →   --accent: #F0EDE7;
--border: #e2e8f0;           →   --border: #E8E4DE;
--input: #e2e8f0;            →   --input: #E8E4DE;
--sidebar: #f8fafc;          →   --sidebar: #FAF9F6;
--sidebar-accent: #f1f5f9;   →   --sidebar-accent: #F0EDE7;
--sidebar-border: #e2e8f0;   →   --sidebar-border: #E8E4DE;
```

**验收标准**:
- [ ] Light 主题下背景为暖米色 `#FAF9F6`
- [ ] 卡片/popover 仍为白色，与背景有层次感
- [ ] Primary 色保持 Ottawa 蓝 `#004890`
- [ ] Dark 主题不受影响

**文件**: `app/(frontend)/globals.css`

---

## [DM-T3] Ottawa 建议问题（WelcomeScreen 升级）

### [DM-T3-01] 建议问题数据迁移

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**描述**: 从 Ottawa RAG-Project 的 `suggested_questions.json` 迁移 7 类 120+ 条结构化问题到本项目。

**来源**: `RAG-Project/frontend/src/data/suggested_questions.json`
**目标**: `payload-v2/src/features/chat/data/suggested_questions.json`

**验收标准**:
- [ ] 7 个类别: Labour Market, Housing Starts, Resale Market, Inflation & CPI, Commercial Vacancy, Construction & Permits, Policy & Highlights
- [ ] 120+ 条真实 Ottawa 经济问题
- [ ] JSON 结构: `{ categories: [{ id, label, icon, questions: string[] }] }`

**文件**: `features/chat/data/suggested_questions.json`

### [DM-T3-02] WelcomeScreen 问题卡片

**类型**: Frontend · **优先级**: P0 · **预估**: 1.5h

**描述**: 升级 WelcomeScreen 从空白状态变为类似 Ottawa `SuggestedQuestionsPanel` 的分类问题展示。但不用独立 panel，而是直接在 WelcomeScreen 中展示。

**设计**:
- 标题: "What would you like to know about Ottawa's economy?"
- 7 个分类按钮（horizontal scroll / wrap）
- 点击分类展开 3-5 个随机问题
- 点击问题直接提交到 chat

**验收标准**:
- [ ] 问题按类别分组，每类显示 emoji 图标 + 标签
- [ ] 每次随机展示 3-5 个问题（不重复）
- [ ] 点击问题调用 `onSubmitQuestion(question)`
- [ ] 响应式: 移动端垂直排列，桌面端网格

**参考**: `RAG-Project/frontend/src/components/SuggestedQuestionsPanel.tsx`
**文件**: `features/chat/panel/WelcomeScreen.tsx`

---

## [DM-T4] Citation 统一 + Score 徽章

### [DM-T4-01] CitationChip 添加 Score 徽章

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: 在 CitationChip 上添加 score 显示，颜色编码表示引用质量。对应 Project Brief 的 "trustability indicator" 要求。

**设计**:
```
[1] Ottawa ED Q4 2024 · p.12  0.92    ← 绿色高分
[2] Ottawa ED Q3 2024 · p.5   0.67    ← 黄色中等
```

**颜色规则**:
- `score ≥ 0.8` → `bg-green-500/20 text-green-600` (高相关)
- `0.5 ≤ score < 0.8` → `bg-amber-500/20 text-amber-600` (中等)
- `score < 0.5` → `bg-gray-500/20 text-gray-500` (低相关)

**验收标准**:
- [ ] `score` prop 可选，有值时显示数字徽章
- [ ] 颜色按规则编码
- [ ] Tooltip 显示 "Relevance Score: 0.92"
- [ ] SourceInfo 类型添加 `score?: number` 字段

**文件**: `features/chat/panel/CitationChip.tsx`, `features/shared/types.ts`

### [DM-T4-02] SourceCard 合并到 CitationChip

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: SourceCard 和 CitationChip 的 hover popover 逻辑重复。合并为: CitationChip 统一包含 hover 预览（当前由 AnswerBlockRenderer 内联面板 + CitationPopover 两套并存）。

**验收标准**:
- [ ] CitationChip 支持 `variant: 'inline' | 'standalone'` 两种模式
- [ ] inline 模式: 在 AnswerBlockRenderer 中使用，click 展开内联面板
- [ ] standalone 模式: 在 MessageBubble 底部使用，hover 显示 popover
- [ ] 删除 SourceCard.tsx 中与 CitationChip 重复的渲染逻辑

**文件**: `features/chat/panel/CitationChip.tsx`, `features/chat/panel/SourceCard.tsx`

### [DM-T4-03] 后端 Score 透传

**类型**: Backend · **优先级**: P0 · **预估**: 0.5h

**描述**: 确保 ChromaDB 检索的距离分数 (distance) 转换为 0-1 normalized score 并透传到前端 `SourceInfo.score`。

**当前状态**: `citation.py` 中 `NodeWithScore.score` 已可用（LlamaIndex 默认返回），需确认 API response 序列化时包含 `score` 字段。

**验收标准**:
- [ ] `/engine/query/stream` response 中每个 source 包含 `score` 字段
- [ ] `score` 范围 0.0 – 1.0（归一化）
- [ ] 前端 SourceInfo 类型已包含 `score?: number`

**文件**: `engine_v2/api/routes/query.py`, `engine_v2/rag/citation.py`

---

## [DM-T5] Report 模块 MVP（S8 精简版）

> S8 原始设计 17 stories / 56h，此处精简为 4 stories / 3h 的可展示 MVP。
> 仅实现：报告列表 + 从聊天历史生成简要报告 + Markdown 渲染预览。
> 不实现：模板 Registry、code_executor 图表、PDF 导出。

### [DM-T5-01] Reports Payload 集合

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 0.5h

**描述**: 精简版 Reports 集合。仅存储报告内容 + 关联的 session。

**数据模型**:
```
Reports (slug: 'reports')
├── user         → relationship → users
├── title        → text
├── content      → textarea (Markdown)
├── sessionId    → text (关联的聊天会话 ID)
├── model        → text (使用的 LLM)
├── stats        → json ({ messageCount, sourceCount, avgScore })
├── status       → select: generating | completed | failed
├── createdAt / updatedAt
```

**验收标准**:
- [ ] 创建 `collections/Reports.ts`
- [ ] access: 用户只能读写自己的报告
- [ ] admin group: 'Reports'

**文件**: `collections/Reports.ts`, `payload.config.ts`

### [DM-T5-02] 报告生成 API

**类型**: Backend · **优先级**: P0 · **预估**: 1h

**描述**: 基于聊天历史 + 评估数据生成报告的 API。MVP 不用 Templates，直接硬编码报告结构。

**报告结构**:
1. Executive Summary — 对话主题概要
2. Key Findings — 基于 chat sources 提取核心发现
3. Source Analysis — 引用频率 + 相关性分数统计
4. Methodology — 使用的模型 + 检索引擎信息

**验收标准**:
- [ ] `POST /engine/report/generate` — body: `{ sessionId, userId }`
- [ ] 从 Payload ChatMessages 拉取指定 session 的对话
- [ ] 用 LLM 生成 Markdown 格式报告
- [ ] 结果存入 Reports 集合
- [ ] `GET /engine/report/list` — 返回当前用户的报告列表
- [ ] `GET /engine/report/{id}` — 返回报告详情

**文件**: `engine_v2/api/routes/report.py`, `engine_v2/report/generator.py`

### [DM-T5-03] 报告页面 (前端)

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: `/reports` 路由页面。左侧报告列表，右侧 Markdown 预览。

**设计参考**: Ottawa RAG-Project `ReportPage.tsx` 的布局（sidebar + main content）。

**验收标准**:
- [ ] 创建 `features/report/ReportPage.tsx`
- [ ] 左侧: 报告列表卡片（标题 + 日期 + 状态）
- [ ] 右侧: Markdown 渲染（复用 AnswerBlockRenderer 的 Markdown 样式）
- [ ] "Generate Report" 按钮（选择一个 chat session → 生成）
- [ ] 路由注册: `/reports`

**文件**: `features/report/ReportPage.tsx`, `app/(frontend)/reports/page.tsx`

### [DM-T5-04] 侧栏报告入口

**类型**: Frontend · **优先级**: P1 · **预估**: 0.5h

**描述**: 在 AppSidebar 的 Resources 分组下添加 Report 链接。

**验收标准**:
- [ ] 在 `navGroupResources` 下添加 `{ titleKey: 'navReports', icon: FileText, href: '/reports' }`
- [ ] 翻译: `navReports: 'Reports'` (en) / `'报告'` (zh)

**文件**: `features/layout/AppSidebar.tsx`, `features/shared/i18n/`

---

## [DM-T6] Admin/User 侧栏分离

### [DM-T6-01] 基于角色的侧栏显隐

**类型**: Frontend · **优先级**: P1 · **预估**: 0.5h

**描述**: 将 `AppSidebar.tsx:90` 的 `const isAdmin = true` 改为从 `useAuth()` 读取用户角色。

**用户侧栏**: Chat History + Suggested Questions + Reports + Settings
**管理员侧栏**: + Data Pipeline + Query Pipeline + Quality 三个分组

**验收标准**:
- [ ] `const isAdmin = user?.role === 'admin'` (或 Payload 等效检查)
- [ ] 普通用户只看到 Chat / Reports / Settings
- [ ] 管理员额外看到 Data Pipeline / Query Pipeline / Quality
- [ ] 默认 demo 账户设为 admin（保证展示时能看到全部）

**文件**: `features/layout/AppSidebar.tsx`

---

## 模块文件结构变更

```
payload-v2/src/
├── features/
│   ├── chat/
│   │   ├── data/
│   │   │   └── suggested_questions.json    ← 新建 (from Ottawa)
│   │   └── panel/
│   │       ├── WelcomeScreen.tsx           ← 改造 (问题卡片)
│   │       ├── ChatPanel.tsx               ← 改造 (全书搜索)
│   │       ├── CitationChip.tsx            ← 改造 (score + variant)
│   │       └── SourceCard.tsx              ← 改造 (合并到 CitationChip)
│   ├── report/                             ← 新建模块
│   │   ├── ReportPage.tsx
│   │   └── types.ts
│   └── layout/
│       └── AppSidebar.tsx                  ← 改造 (role check + Report link)
├── app/(frontend)/
│   ├── globals.css                         ← 改造 (暖色主题)
│   └── reports/
│       └── page.tsx                        ← 新建路由

engine_v2/
├── report/                                 ← 新建 (MVP)
│   ├── __init__.py
│   └── generator.py                       ← 报告生成逻辑
└── api/routes/
    └── report.py                          ← 新建 API 端点

collections/
└── Reports.ts                             ← 新建集合
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 备注 |
|-------|-------|-----------|------|
| **Phase 1** | DM-T2-01 (暖色主题) + DM-T1-01/02/03 (全书搜索) | 2.5h | 立即见效 |
| **Phase 2** | DM-T3-01/02 (建议问题) + DM-T6-01 (Admin 分离) | 2.5h | 功能完善 |
| **Phase 3** | DM-T4-01/02/03 (Citation + Score) | 2.5h | 打磨 trustability |
| **Phase 4** | DM-T5-01/02/03/04 (Report MVP) | 3h | 闭环展示 |
