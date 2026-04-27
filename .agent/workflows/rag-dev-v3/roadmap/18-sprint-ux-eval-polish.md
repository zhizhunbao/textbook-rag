# Sprint UX-Eval-Polish — 评分交互打磨 + BM25 修复 + 双视角模式

> 目标：修复 BM25 检索从未触发的 bug，完善评分数据填充（消灭 "—" 和 "Pending"），在聊天界面提供开发者/用户可切换的评分视图。
>
> 前置条件：EV2 ✅ 四分类评分体系已搭建；Sprint Robustness ✅ structured_predict 已上线。
> **状态**: ✅ 14/14 完成

## 发现的问题

本 Sprint 源于以下实际观测：

| # | 问题 | 严重度 | 根因 |
|---|------|--------|------|
| P1 | 所有 source 均标记 `vector`，无 `bm25` 命中 | **Critical** | BM25 只在有 `book_id_strings` 时才构建（line 236），全书搜索时跳过 |
| P2 | 评分卡大部分维度显示 "—" | High | `full_evaluate()` 未执行或 Completeness/Clarity evaluator 超时静默失败 |
| P3 | "Pending" 状态泄露到用户界面 | Medium | `status` 计算依赖评分完整，缺分时 fallback 到 pending |
| P4 | 评分卡使用 "RAG"、"LLM"、"Faithfulness" 等术语 | Medium | `EvalScoreCard` 为管理后台设计，用户看不懂 |
| P5 | CitationChip 使用 emoji (🔤🧮🔄) | Low | 已修复 → SVG 图标 |

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 BM25 检索修复 | 3 | 4h | 无 book_id 时也启用 BM25 + 分批加载 + 性能保护 |
| T2 评分完整性修复 | 3 | 3h | Evaluator 超时兜底 + status 计算修正 + 数据回填 |
| T3 聊天评分双视角 | 4 | 5h | 开发者/用户模式切换 + 用户友好评分卡 + inline 评分 |
| T4 CitationChip 收尾 | 4 | 2.5h | SVG 策略图标 ✅ + 按钮精简 ✅ + queryId 捕获 ✅ + Evaluate 按钮 ✅ |
| **合计** | **14** | **14.5h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | BM25 必须有效 | 全书搜索时 retrieval provenance log 中 bm25 > 0 |
| G2 | 评分无 "—" | full_evaluate 后所有 6 维度均有分数（0-1 之间） |
| G3 | 用户可读 | 非技术用户能理解评分含义（用户视角无 RAG/LLM 术语） |
| G4 | 开发者可诊断 | 开发者视角保留完整技术指标 + 策略统计 |
| G5 | 不增加延迟 | BM25 加载不阻塞首次查询（lazy init 或后台预热） |

---

## [UEP-T1] BM25 检索修复

> 现状：`hybrid.py` line 236 条件 `if doc_count > 0 and book_id_strings:` 导致无 book_id 过滤时 BM25 被跳过。当用户选择"所有书籍"搜索时（ChatPanel 的 `isAllBooks=true` 路径），`book_id_strings=[]`，BM25 永远不触发。

### [UEP-T1-01] 全书搜索时启用 BM25 ✅

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 修改 BM25 构建逻辑，在无 `book_id_strings` 时也构建 BM25 retriever。需要解决大语料下的内存和性能问题。

**当前代码** (`hybrid.py:236-295`):
```python
if doc_count > 0 and book_id_strings:
    # 只在指定 book_id 时构建 BM25
    ...
elif doc_count > 0:
    logger.info("No book_id filter — skipping BM25 (185k+ nodes too large)")
```

**方案**:
- 无 book_id 时，随机抽样或取最近 N 条（如 `MAX_BM25_NODES=20000`）构建 BM25
- 或者：全量加载但用分批 get + 内存限制
- BM25 构建移到后台线程，首次查询如果 BM25 未就绪则 fallback vector-only

**验收标准**:
- [x] 全书搜索时 BM25 retriever 被构建
- [x] ChromaDB get() 分批拉取，单批不超过 `MAX_BM25_NODES`
- [x] BM25 构建失败时静默 fallback 到 vector-only（不 crash）
- [x] log 输出中可见 `retrieval_mode=hybrid`
- [x] G1 ✅ BM25 命中数 > 0

**文件**: `engine_v2/retrievers/hybrid.py`

### [UEP-T1-02] BM25 Retriever 预热缓存 ✅

**类型**: Backend · **优先级**: P1 · **预估**: 1h

**描述**: BM25 retriever 构建耗时（需从 ChromaDB 拉文本 + rank_bm25 索引），每次查询重建太慢。增加模块级缓存，按 `(collection_name, frozenset(book_ids))` 缓存。

**验收标准**:
- [x] 新增 `_BM25_CACHE: dict[str, BM25Retriever]` 模块缓存
- [x] 相同 book_id 组合复用已构建的 BM25 retriever
- [x] 缓存 TTL 或 LRU 限制（防止内存无限增长）
- [x] G5 ✅ 第二次查询不重建 BM25

**文件**: `engine_v2/retrievers/hybrid.py`

### [UEP-T1-03] 前端 "全书搜索" 时传递正确参数 ✅

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: 确认 `ChatPanel.tsx` 中 `isAllBooks=true` 时不传空 `book_id_strings`，让后端知道是全书搜索而不是"无过滤"。

**当前** (`ChatPanel.tsx:249-255`):
```typescript
const isAllBooks = sessionBookIds.length === books.length;
const engineBookIdStrings = isAllBooks
  ? []  // ← 传空数组，后端视为"无过滤"→ 跳过 BM25
  : sessionBookIds.map(...)
```

**方案**:
- 方案 A: 全书时仍传所有 book_id → 后端 BM25 按正常逻辑构建
- 方案 B: 前端不改，后端修复"无 book_id 也启用 BM25"（T1-01 已处理）

**验收标准**:
- [x] 全书搜索时后端收到的 filters 能触发 BM25 构建
- [x] 与 T1-01 方案保持一致（方案 B：后端已修复，前端不改）
- [x] G1 ✅

**文件**: `payload-v2/src/features/chat/panel/ChatPanel.tsx`

---

## [UEP-T2] 评分完整性修复

> 现状：Completeness 和 Clarity 显示 "—"，`status` 永远是 "Pending"。原因可能是 Evaluator 超时、LLM 响应解析失败、或 `full_evaluate()` 未被完整执行。

### [UEP-T2-01] Evaluator 超时兜底 + 错误隔离

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: `full_evaluate()` 中每个 Evaluator 独立 try/except，单个 Evaluator 超时或失败不影响其他维度。

**当前**: `full_evaluate()` 如果某个 evaluator 抛异常，可能导致整个评估中断，后续维度不执行。

**方案**:
```python
async def full_evaluate(query_id: int, model: str | None = None) -> FullEvalResult:
    ...
    # 每个 evaluator 独立执行，单个失败不影响其他
    with contextlib.suppress(Exception):
        rag_scores = await _eval_rag(query, contexts, llm)
    with contextlib.suppress(Exception):
        llm_scores = await _eval_llm(query, answer, contexts, llm)
    with contextlib.suppress(Exception):
        answer_scores = await _eval_answer(query, answer, contexts, llm)
    ...
```

**验收标准**:
- [ ] 每个 evaluator 调用 wrapped in try/except
- [ ] 失败的维度记录为 `null`（不是 0）+ 在 `feedback` dict 中记录错误原因
- [ ] 至少 faithfulness + answer_relevancy 成功时，仍然计算 `overall_score`
- [ ] G2 ✅ 正常情况下所有维度有分数

**文件**: `engine_v2/evaluation/history.py`

### [UEP-T2-02] Status 计算修正

**类型**: Backend · **优先级**: P1 · **预估**: 0.5h

**描述**: 当前 `status` 计算逻辑在关键分数缺失时 fallback 到 `"pending"`，导致几乎所有评估都显示 Pending。

**方案**: 
- 有 `faithfulness` 且 `answer_relevancy` → 可计算 status
- 缺分但有 `overall_score` → 用 overall 阈值判定
- 完全无分 → `pending`

**验收标准**:
- [ ] 有足够分数时 status 为 `pass` 或 `fail`（不再是永远 pending）
- [ ] 阈值从 `settings.py` 读取（`EVAL_PASS_FAITHFULNESS`, `EVAL_PASS_ANSWER_SCORE`）
- [ ] Pending 仅在评估未执行或全部 evaluator 失败时出现

**文件**: `engine_v2/evaluation/history.py`, `engine_v2/settings.py`

### [UEP-T2-03] 历史评估数据回填 ✅

**类型**: Backend · **优先级**: P2 · **预估**: 1h

**描述**: 提供脚本重新评估已有的 Payload Evaluations 记录中缺失维度的数据。

**验收标准**:
- [x] 新增 `scripts/eval/backfill_evaluations.py`
- [x] 遍历 status=pending 的记录，重新执行 `full_evaluate()`
- [x] 支持 `--dry-run` 模式预览将要更新的记录数
- [x] 支持 `--limit N` 限制处理数量

**文件**: `scripts/eval/backfill_evaluations.py` (新增)

---

## [UEP-T3] 聊天评分双视角

> 现状：`EvalScoreCard` 使用 "RAG"、"LLM"、"Faithfulness" 等专业术语，用户无法理解。但开发者需要这些技术指标做诊断。需要可切换的双视角模式。

### [UEP-T3-01] 用户友好评分卡组件 ✅

**类型**: Frontend · **优先级**: P0 · **预估**: 2h

**描述**: 新增 `InlineEvalCard.tsx`，为聊天界面设计的用户友好版评分卡。

**用户视角术语映射**:

| 技术术语 | 用户友好 (EN) | 用户友好 (CN) | 说明 |
|----------|--------------|--------------|------|
| RAG Score | Source Quality | 来源质量 | 找到的参考资料有多相关 |
| LLM Score (Faithfulness) | Accuracy | 准确度 | 回答是否忠于原文、不编造 |
| Answer Score | Answer Quality | 回答质量 | 回答是否完整、清晰 |
| Question Depth | Question Depth | 问题深度 | Surface → Understanding → Synthesis |
| Overall Score | Overall | 综合评分 | 加权总分 |
| Pass/Fail | ✅ Good / ⚠️ Needs Improvement | ✅ 优 / ⚠️ 待改进 | 用户友好的状态描述 |

**展示格式**:
```
综合评分: 78% ✅ 优
[来源质量 ████████░░ 0.75] [准确度 █████████░ 0.88] [回答质量 ████████░░ 0.76]
问题深度: 理解层
```

**验收标准**:
- [x] 新增 `features/chat/panel/InlineEvalCard.tsx`
- [x] 输入 `EvaluationResult`，输出用户友好的紧凑评分卡
- [x] 无 "RAG"、"LLM"、"Faithfulness" 等术语出现
- [x] 进度条 + 颜色编码（≥0.85 绿, ≥0.7 蓝, ≥0.5 黄, <0.5 红）
- [x] G3 ✅ 用户可读

**文件**: `payload-v2/src/features/chat/panel/InlineEvalCard.tsx` (新增)

### [UEP-T3-02] 开发者/用户视角切换 ✅

**类型**: Frontend · **优先级**: P0 · **预估**: 1.5h

**描述**: 在 `MessageBubble.tsx` 的内联评分区域增加视角切换 toggle。

**方案**:
- 默认显示用户友好版 (`InlineEvalCard`)
- 切换到开发者模式时显示技术版 (`EvalScoreCard`)
- 切换状态存 localStorage，跨 session 保持
- 头部显示小切换按钮: `👤 User` / `🔧 Dev`

**验收标准**:
- [x] Toggle 按钮在评分卡操作栏（scores 展开时可见）
- [x] 切换 User / Dev 视图（User = InlineEvalCard, Dev = EvalScoreCard）
- [x] 状态持久化到 `localStorage('eval-view-mode')`
- [x] 默认 `user` 模式
- [x] G3 ✅ + G4 ✅

**文件**: `payload-v2/src/features/chat/panel/MessageBubble.tsx`

### [UEP-T3-03] Evaluate 按钮状态优化

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: 当前 Evaluate 按钮在评估完成后变成 "Scores" toggle。优化状态流：
- 未评估: `[Evaluate]` 按钮（灰色）
- 评估中: `[Evaluating…]` + spinner（disabled）
- 已评估: `[78% ✅]` 紧凑 badge（点击展开评分卡）
- 已评估 + 展开: 显示评分卡 + `[收起]` 按钮

**验收标准**:
- [ ] 四种状态视觉区分明确
- [ ] 已评估时 badge 颜色反映 overall score 等级
- [ ] 展开/收起有滑动动画
- [ ] G3 ✅ 状态一目了然

**文件**: `payload-v2/src/features/chat/panel/MessageBubble.tsx`

### [UEP-T3-04] 自动加载已有评估

**类型**: Frontend · **优先级**: P1 · **预估**: 0.5h

**描述**: 加载历史消息时，如果该 queryId 已有评估结果，自动显示评分 badge（无需用户点击 Evaluate）。

**验收标准**:
- [ ] `MessageBubble` mount 时检查 `queryId` → fetch existing evaluation
- [ ] 有已有评估时直接显示 badge，无需手动触发
- [ ] 请求失败或无评估时静默（不显示 Evaluate 按钮直到 queryId 可用）

**文件**: `payload-v2/src/features/chat/panel/MessageBubble.tsx`

---

## [UEP-T4] CitationChip 收尾

> 本轮对话已完成的工作，记录在 Sprint 中追踪。

### [UEP-T4-01] Emoji → SVG 图标迁移 ✅

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**描述**: 将 CitationChip 中的 emoji 策略标签 (🔤🧮🔄) 替换为自定义 SVG 图标组件。

**验收标准**:
- [x] `IconBM25` — 放大镜 + T 字图标
- [x] `IconVector` — 神经网络节点图标
- [x] `IconHybrid` — 合流箭头图标
- [x] `IconDocument` — 文件图标（PDF 按钮）
- [x] 策略标签显示 SVG 图标 + 文字标签（小屏隐藏文字）

**文件**: `payload-v2/src/features/chat/panel/CitationChip.tsx`

### [UEP-T4-02] 多余按钮精简 ✅

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**描述**: 移除用户不需要的 Preview (眼睛) 和 Copy (剪贴板) 按钮，只保留 PDF 按钮。

**验收标准**:
- [x] 移除 `IconExpand`、`IconCopy`、`IconCheck` 组件
- [x] 移除 `handleCopy`、`handlePreview` handlers
- [x] 只保留 PDF 查看器按钮

**文件**: `payload-v2/src/features/chat/panel/CitationChip.tsx`

### [UEP-T4-03] QueryId 捕获 + Evaluate 按钮 ✅

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: 在 ChatPanel 中捕获 `/api/queries` POST 响应的 ID，注入到 Message 中，在 MessageBubble 中显示 Evaluate 按钮触发内联评估。

**验收标准**:
- [x] `Message` 类型新增 `queryId?: number` 字段
- [x] `ChatPanel.tsx` 捕获 POST response 的 `doc.id` → 更新 message
- [x] `MessageBubble.tsx` 新增 Evaluate 按钮 + `EvalScoreCard` 内联显示
- [x] 评估加载中显示 spinner

**文件**: `payload-v2/src/features/chat/types.ts`, `payload-v2/src/features/chat/panel/ChatPanel.tsx`, `payload-v2/src/features/chat/panel/MessageBubble.tsx`

### [UEP-T4-04] Score 颜色系统优化 ✅

**类型**: Frontend · **优先级**: P2 · **预估**: 0.5h

**描述**: 统一 CitationChip 和 EvalScoreCard 的配色系统，使用一致的 emerald/amber/red 三级色阶。

**验收标准**:
- [x] `scoreStyle()` 使用 ring-1 + 透明背景 + 4 级色阶（emerald/blue/amber/red）
- [x] 评分数字颜色与进度条颜色一致
- [x] 与 `EvalScoreCard` 的 `GRADE_CLS` 对齐

**文件**: `payload-v2/src/features/chat/panel/CitationChip.tsx`

---

## 模块文件变更

```
engine_v2/
├── retrievers/
│   └── hybrid.py                       ← 改造 (BM25 全书搜索 + 缓存)
├── evaluation/
│   └── history.py                      ← 改造 (evaluator 错误隔离 + status 修正)
└── settings.py                         ← 改造 (EVAL_PASS 阈值调整)

payload-v2/
├── src/features/
│   ├── chat/
│   │   ├── types.ts                    ← 改造 ✅ (queryId 字段)
│   │   └── panel/
│   │       ├── CitationChip.tsx        ← 改造 ✅ (SVG 图标 + 精简按钮)
│   │       ├── MessageBubble.tsx       ← 改造 ✅ (Evaluate 按钮 + 双视角)
│   │       ├── InlineEvalCard.tsx      ← 新增 (用户友好评分卡)
│   │       └── ChatPanel.tsx           ← 改造 ✅ (queryId 捕获)
│   └── engine/evaluation/
│       └── components/
│           └── EvalScoreCard.tsx       ← 不改 (开发者视角保留原样)

scripts/
└── eval/
    └── backfill_evaluations.py         ← 新增 (回填缺失评估)
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 0** | UEP-T4-01~03 (CitationChip 收尾) | — | — | ✅ 已完成 |
| **Phase 1** | UEP-T1-01 (BM25 全书搜索) | 2h | 无 | **最高优先级** — 修复核心检索 bug |
| **Phase 2** | UEP-T1-03 (前端参数修正) | 1h | Phase 1 | 确保前后端配合 |
| **Phase 3** | UEP-T2-01, T2-02 (评估完整性 + status) | 2h | 无 | 消灭 "—" 和 "Pending" |
| **Phase 4** | UEP-T3-01 (用户友好评分卡) | 2h | Phase 3 | 用户看得懂的评分 |
| **Phase 5** | UEP-T3-02, T3-03 (双视角 + 按钮优化) | 2.5h | Phase 4 | 开发者/用户切换 |
| **Phase 6** | UEP-T1-02, T3-04, T4-04 (缓存 + 自动加载 + 配色) | 2h | Phase 1,5 | 打磨 |
| **Phase 7** | UEP-T2-03 (数据回填) | 1h | Phase 3 | 清理历史数据 |

---

## 与其他 Sprint 的关系

| Sprint | 关系 | 说明 |
|--------|------|------|
| Sprint EV2 (16) | **修复** | T1 修复了 EV2-T1 检索策略溯源的 BM25 缺陷；T2 修复了 EV2-T2/T3 评估数据不完整 |
| Sprint Robustness (17) | **独立** | structured_predict 已完成，不受影响 |
| Sprint EC (14) | **协同** | T2-03 回填脚本可配合 EC-T3 高分报告使用 |
