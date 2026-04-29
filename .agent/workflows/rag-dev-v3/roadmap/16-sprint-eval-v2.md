# Sprint Eval-v2 — 四分类评分 + 检索策略溯源 + 自动评估 + Agentic RAG 基座 (TBD)

> 目标：重构评估体系为 RAG/LLM/Answer/Question 四分类；让每条 source 标记来源策略 (BM25/Vector/Both)；每次用户交互自动触发评估；为 Agentic RAG 路由决策提供数据基础。
>
> 前置条件：S2 ✅ evaluation 5 维评估 + 持久化 + history.py 已完成；DM-T5 ✅ Report MVP 已完成。
> 继承关系：本 Sprint 覆盖并替代 Sprint EC (14-sprint-eval-curation.md) 的 T2 自动评估部分，EC-T1 Query 删除和 EC-T3 高分报告保留独立。
> **状态**: ✅ 16/16 完成
> ⚠️ **已知问题**: T1 检索策略溯源中 BM25 在全书搜索时从未触发 (bug)，已在 Sprint 18 (UEP-T1) 中修复计划

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 检索策略溯源 | 3 | 4.5h | 后端标记 BM25/Vector/Both + stats 真实数据 + 前端展示 |
| T2 四分类评分重构 | 4 | 6h | HistoryEvalResult → FullEvalResult + Answer 新 Evaluator |
| T3 自动评估触发 | 3 | 4h | 查询后异步评估 + 达标判定 + 前端状态显示 |
| T4 Agentic RAG 路由基座 | 3 | 7h | Depth→策略路由 + smart_retrieve 接入 + 路由评估 |
| T5 前端评分 UX | 3 | 5.5h | 四分类评分卡 + Source 策略标签 + 诊断面板 |
| **合计** | **16** | **27h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 模块归属 | 检索策略标记在 `engine_v2/retrievers/hybrid.py`；评估重构在 `engine_v2/evaluation/`；自动评估在 `engine_v2/api/routes/query.py`；前端在 `features/engine/evaluation/` |
| G2 | 数据流方向 | 前端读评估数据走 Payload `/api/evaluations`，不直接调 Engine |
| G3 | 不破坏现有 | 现有 evaluate_single / evaluate_batch / query/stream 接口向后兼容 |
| G4 | 零延迟影响 | T1 检索策略标记不增加任何 LLM 调用；T3 自动评估异步执行不阻塞响应 |

---

## [EV2-T1] 检索策略溯源

> 现状：`QueryFusionRetriever` 做完 RRF 融合后丢失了 BM25/Vector 来源信息。前端 `RetrievalStats.fts_hits` / `vector_hits` 已预留字段但后端永远返回 0。

### [EV2-T1-01] Hybrid Retriever 策略标记

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 在 RRF 融合前，对每条 NodeWithScore 的 metadata 注入 `retrieval_source` 字段标记来源。

**当前**: `QueryFusionRetriever` 融合后所有 node 无来源标记。
**改为**: 融合前标记每条 node 来自 `"bm25"` / `"vector"` / `"both"`（两路都命中同一 chunk_id）。

**实现方案**:
- 子类化 `QueryFusionRetriever` 为 `TrackedQueryFusionRetriever`
- Override `_run_nested_retrievers()` 或在融合前 hook
- 计算 vector_ids ∩ bm25_ids 得到 "both" 集合
- 注入 `node.metadata["retrieval_source"]`

**验收标准**:
- [x] `hybrid.py` 新增 `TrackedQueryFusionRetriever` 或在现有代码中注入标记逻辑
- [x] 每条融合后的 NodeWithScore 的 metadata 包含 `retrieval_source: "bm25" | "vector" | "both"`
- [x] 无 book_id_strings 时（vector-only 模式），标记为 `"vector"`
- [x] 不增加任何 LLM 调用或额外延迟
- [x] G1 ✅ 在 `engine_v2/retrievers/`
- [x] G4 ✅ 零延迟影响

**文件**: `engine_v2/retrievers/hybrid.py`

### [EV2-T1-02] build_source + _build_stats 填充策略数据

**类型**: Backend · **优先级**: P0 · **预估**: 1h

**描述**: `schema.py` 的 `build_source()` 提取 `retrieval_source` 字段；`query.py` 的 `_build_stats()` 计算真实的 BM25/Vector 命中数。

**当前**: `_build_stats()` 返回 `fts_hits: 0, vector_hits: 0` 硬编码。
**改为**: 从 sources 列表的 `retrieval_source` 字段统计真实数据。

**验收标准**:
- [x] `schema.py` 的 `build_source()` 返回 dict 包含 `"retrieval_source"` 字段
- [x] `query.py` 的 `_build_stats()` 统计真实的 `fts_hits`、`vector_hits`、`both_hits`
- [x] `_build_stats()` 新增 `retrieval_mode: "hybrid" | "vector_only"` 字段
- [x] 与前端 `RetrievalStats` 接口对齐
- [x] G3 ✅ 向后兼容（新增字段，不删除旧字段）

**文件**: `engine_v2/schema.py`, `engine_v2/api/routes/query.py`

### [EV2-T1-03] 前端 Source Chip 策略标签

**类型**: Frontend · **优先级**: P1 · **预估**: 1.5h

**描述**: CitationChip 组件显示每条 source 的检索策略来源标签 (🔤 BM25 / 🧮 Vector / 🔄 Both)。RetrievalStats 区域显示真实命中统计。

**验收标准**:
- [x] `types.ts` 的 `SourceInfo` 新增 `retrieval_source?: "bm25" | "vector" | "both"` 字段
- [x] CitationChip 显示小标签标记来源策略
- [x] RetrievalStats 区域显示 "N BM25 · M Vector · K Both"
- [x] 配色方案：BM25=蓝色 / Vector=紫色 / Both=绿色
- [x] G2 ✅ 数据从 Payload 读取

**文件**: `features/shared/types.ts`, `features/chat/panel/` (CitationChip 相关组件)

---

## [EV2-T2] 四分类评分重构

> 现状：`HistoryEvalResult` 平铺 5 维评分，用户无法快速判断"是检索差还是回答差"。缺少 Answer 独立评分维度。

### [EV2-T2-01] Answer Evaluators — Completeness + Clarity

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 新增两个自定义 Evaluator，继承 `CorrectnessEvaluator` 使用自定义 eval_template：
- `CompletenessEvaluator` — 回答是否完整覆盖了问题的所有要点 (1-5)
- `ClarityEvaluator` — 回答表达是否清晰、结构是否合理 (1-5)

**验收标准**:
- [x] 新增 `engine_v2/evaluation/answer_evaluators.py`
- [x] `CompletenessEvaluator` — 自定义 prompt 评估回答完整度，输入 (query, response, contexts)
- [x] `ClarityEvaluator` — 自定义 prompt 评估回答清晰度，输入 (response)
- [x] 两者均继承 `CorrectnessEvaluator`，输出 1-5 分 + reasoning
- [x] 单元级验证：用一个简单 query/answer 对调用，确认输出格式正确
- [x] G1 ✅ 在 `engine_v2/evaluation/`
- [x] Prompt 模板集中管理于 `evaluation/prompts.py`

**文件**: `engine_v2/evaluation/answer_evaluators.py` (新增)

### [EV2-T2-02] FullEvalResult 数据结构

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: 新增 `FullEvalResult` dataclass 替代 `HistoryEvalResult`，将评分分为四组：

| 组 | 维度 | 说明 |
|----|------|------|
| 🔍 RAG Score | `context_relevancy` · `relevancy` · `retrieval_coverage` | 检索质量 |
| 🤖 LLM Score | `faithfulness` | 模型忠实度（不幻觉） |
| 📝 Answer Score | `correctness` · `answer_relevancy` · `completeness` · `clarity` | 回答质量 |
| ❓ Question Score | `depth` · `dedup` | 问题质量（路由用） |

新增聚合字段：`rag_score`、`llm_score`、`answer_score`、`overall_score`。
新增检索策略字段：`retrieval_mode`、`bm25_hit_count`、`vector_hit_count`、`both_hit_count`。

**验收标准**:
- [x] `engine_v2/evaluation/evaluator.py` 中定义 `FullEvalResult` dataclass
- [x] 包含四组评分 + 聚合分数 + 检索策略统计 + `status` 字段
- [x] `HistoryEvalResult` 保留向后兼容
- [x] G3 ✅ 不破坏现有 evaluate_single / evaluate_batch 接口
- [x] 新增 `compute_aggregate_scores()` 计算聚合分数

**文件**: `engine_v2/evaluation/evaluator.py`

### [EV2-T2-03] full_evaluate() 四分类评估 pipeline

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: 新增 `full_evaluate(query_id)` 函数，执行完整四分类评估：
1. 🔍 RAG: `ContextRelevancyEvaluator` + `RelevancyEvaluator` + 策略统计
2. 🤖 LLM: `FaithfulnessEvaluator`
3. 📝 Answer: `CorrectnessEvaluator` + `AnswerRelevancyEvaluator` + `CompletenessEvaluator` + `ClarityEvaluator`
4. ❓ Question: `QuestionDepthEvaluator`
5. 聚合: `rag_score` = mean(ctx, rel), `answer_score` = mean(cor, ar, comp, cla), `overall` = weighted_sum

**验收标准**:
- [x] `engine_v2/evaluation/history.py` 新增 `full_evaluate(query_id, model=None)` 异步函数
- [x] 返回 `FullEvalResult`
- [x] 聚合权重可配置（`compute_aggregate_scores()` 支持自定义 weights）
- [x] 提取检索策略统计从 stored sources
- [x] 向后兼容：现有 `evaluate_single_from_query()` 不受影响

**文件**: `engine_v2/evaluation/history.py`, `engine_v2/settings.py`

### [EV2-T2-04] Payload Evaluations 集合扩展

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**描述**: Evaluations 集合新增四分类评分字段 + 检索策略统计字段。

**验收标准**:
- [x] Evaluations 集合新增：`ragScore`, `llmScore`, `answerScore`, `overallScore` (number)
- [x] 新增：`completeness`, `clarity` (number, 0-1)
- [x] 新增：`correctness` (number, 0-1) — 已存在
- [x] 新增：`retrievalMode` (select: hybrid | vector_only)
- [x] 新增：`bm25Hits`, `vectorHits`, `bothHits` (number)
- [x] 新增：`status` (select: pass | fail | pending)
- [x] 现有字段保留不变
- [x] G3 ✅ 向后兼容

**文件**: `payload-v2/src/collections/Evaluations.ts`

---

## [EV2-T3] 自动评估触发

> 现状：评估需要用户在 EvaluationPage 手动点击触发。每次查询后应自动异步评估。

### [EV2-T3-01] 查询后自动触发四分类评估

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 在 `/engine/query/stream` 完成后，自动异步触发 `full_evaluate()` 对刚产生的回答进行四分类评估。评估在后台执行，不阻塞 SSE 流响应。

**当前**: 评估需要用户在 EvaluationPage 手动点击"Evaluate"按钮。
**改为**: 每次查询完成后，后台自动异步评估。用户仍可在 EvaluationPage 查看/重新评估。

**验收标准**:
- [x] Payload Queries `afterChange` hook 触发 `auto_evaluate_query()` via `/engine/evaluation/auto-evaluate`
- [x] `auto-evaluate` 端点通过 `asyncio.create_task()` 异步触发，不阻塞响应
- [x] 评估结果自动写入 Payload Evaluations 集合（`_persist_full_evaluation()`）
- [x] 可通过 `settings.py` 的 `AUTO_EVAL_ENABLED` 环境变量控制开关（默认关闭）
- [x] 评估失败不影响查询响应（静默捕获异常，仅 log）
- [x] G4 ✅ 不增加查询延迟

**文件**: `engine_v2/api/routes/evaluation.py`, `engine_v2/evaluation/history.py`, `engine_v2/settings.py`, `payload-v2/src/hooks/queries/afterChange.ts`, `payload-v2/src/collections/Queries.ts`

### [EV2-T3-02] 评估结果达标判定

**类型**: Backend · **优先级**: P1 · **预估**: 1h

**描述**: 在 `_persist_evaluation()` 中增加 `status` 计算逻辑。

**阈值规则** (可通过 settings.py 配置):
- `faithfulness ≥ 0.7` AND `answer_score ≥ 0.6` → `status: "pass"`
- 否则 → `status: "fail"`

**验收标准**:
- [x] `evaluation/history.py` 的 `full_evaluate()` 内置 `_compute_status()` 逻辑
- [x] `settings.py` 新增 `EVAL_PASS_FAITHFULNESS` + `EVAL_PASS_ANSWER_SCORE` 配置
- [x] 向后兼容：未触发自动评估的记录 `status = "pending"`

**文件**: `engine_v2/evaluation/history.py`, `engine_v2/settings.py`

### [EV2-T3-03] 前端评估状态显示

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: EvaluationPage 的 Query 列表中显示评估状态（pass/fail/pending），并支持按状态过滤。

**验收标准**:
- [x] Query 列表增加状态列（✅ Pass / ❌ Fail / ⏳ Pending）
- [x] 状态过滤器：All / Pass Only / Fail Only / Pending
- [x] 状态对应颜色编码（绿/红/灰）
- [x] `types.ts` 的 `EvaluationResult` 增加 `status: 'pass' | 'fail' | 'pending'`
- [x] Overall score 百分比显示

**文件**: `features/engine/evaluation/types.ts`, `features/engine/evaluation/components/EvaluationPage.tsx`

---

## [EV2-T4] Agentic RAG 路由基座

> 目标：基于四分类评分数据 + 检索策略统计，建立 Depth→策略 路由机制。为 Sprint 5 (Deep Solve) 打基础。

### [EV2-T4-01] Depth→检索策略路由器

**类型**: Backend · **优先级**: P1 · **预估**: 3h

**描述**: 新增路由层，根据 `QuestionDepthEvaluator` 的评分决定检索策略：

| Depth | 路由 | 策略 |
|-------|------|------|
| surface (1-2) | Standard RAG | 现有 `get_query_engine()` |
| understanding (3) | Smart Retrieve | 多查询并行检索 (Sprint 5 `smart_retrieve.py`) |
| synthesis (4-5) | Deep Solve | Plan→ReAct→Write (Sprint 5 `agents/solve.py`) |

**当前**: 所有问题走同一条 Standard RAG 路径。
**改为**: 先快速评估问题深度，再路由到合适的检索策略。

**验收标准**:
- [x] 新增 `engine_v2/query_engine/router.py`
- [x] `QueryRouter.route(question)` 返回 `RoutingDecision(strategy, depth, reasoning)`
- [x] 路由决策不阻塞（depth 评估用轻量 prompt）
- [x] `query.py` 的 `QueryRequest` 新增 `retrieval_mode` 参数 (`standard` | `smart` | `deep` | `auto`)
- [x] `auto` 模式使用路由器，其余模式直接指定
- [x] 当 smart_retrieve / deep_solve 未实现时，fallback 到 standard
- [x] G3 ✅ 默认 `standard`，现有行为不变

**文件**: `engine_v2/query_engine/router.py` (新增), `engine_v2/api/routes/query.py`

### [EV2-T4-02] 路由评估 — 路由决策是否正确

**类型**: Backend · **优先级**: P2 · **预估**: 2h

**描述**: 新增路由评估维度：对比路由决策 vs 实际评估结果，判断路由是否合理。

**评估逻辑**:
- 路由到 standard 但 rag_score 低 → 应该升级到 smart
- 路由到 smart 但 rag_score 已经很高 → 浪费资源，standard 就够
- answer_score 低但 rag_score 高 → 不是检索问题，是 LLM 能力问题

**验收标准**:
- [x] `FullEvalResult` 新增 `routing_decision` 字段（记录路由选择）
- [x] `FullEvalResult` 新增 `routing_correct` 字段（bool，事后评估路由是否合理）
- [x] 路由正确性判定规则写入 `settings.py`
- [x] 积累数据后可用于优化路由阈值

**文件**: `engine_v2/evaluation/evaluator.py`, `engine_v2/evaluation/history.py`, `engine_v2/settings.py`, `payload-v2/src/collections/Evaluations.ts`

### [EV2-T4-03] QueryRequest 扩展 — retrieval_mode 参数

**类型**: Backend + Frontend · **优先级**: P1 · **预估**: 2h

**描述**: `QueryRequest` 新增 `retrieval_mode` 字段。前端 ChatInput 增加模式选择 UI。

**验收标准**:
- [x] `QueryRequest` 新增 `retrieval_mode: str | None = None` (standard | smart | deep | auto)
- [x] 前端 ChatInput 增加下拉/toggle 选择检索模式（默认 standard）
- [x] 选择 "auto" 时，后端使用路由器自动决策
- [x] 当 smart/deep 未实现时，UI 显示 "Coming Soon" 并 fallback
- [x] G3 ✅ 默认 None → standard，向后兼容

**文件**: `engine_v2/api/routes/query.py`, `features/chat/panel/ChatInput.tsx`

---

## [EV2-T5] 前端评分 UX

### [EV2-T5-01] 四分类评分卡组件

**类型**: Frontend · **优先级**: P1 · **预估**: 2h

**描述**: EvaluationPage 中每条评估记录显示四分类评分卡，分组展示 RAG/LLM/Answer/Question 评分。

**展示格式**:
```
Overall: 0.79 ✅ Pass
🔍 RAG: 0.75  |  🤖 LLM: 0.88  |  📝 Answer: 0.76  |  ❓ Depth: understanding
```

**验收标准**:
- [x] 新增 `EvalScoreCard.tsx` 组件
- [x] 四组评分分色展示（RAG=蓝, LLM=紫, Answer=绿, Question=灰）
- [x] 点击展开详细维度分数
- [x] Overall 分数 + Pass/Fail 状态 badge
- [x] 响应式布局（移动端竖排）

**文件**: `features/engine/evaluation/components/EvalScoreCard.tsx` (新增)

### [EV2-T5-02] 检索策略诊断面板

**类型**: Frontend · **优先级**: P2 · **预估**: 2h

**描述**: 在 ThinkingProcessPanel 或独立面板中展示检索策略分析：BM25 vs Vector 命中分布、策略建议。

**验收标准**:
- [x] 新增 `RetrievalDiagnostics.tsx` 组件
- [x] 饼图/条形图展示 BM25/Vector/Both 命中比例
- [x] 基于分布给出策略建议文案（e.g. "BM25 命中率高→关键词检索有效"）
- [x] 可嵌入 TracePanel 或 EvaluationPage
- [x] 集成到 EvalScoreCard 替换原有的简易检索统计行
- [x] 包含路由决策展示 (EV2-T4-02 routing_decision + routing_correct)

**文件**: `features/engine/evaluation/components/RetrievalDiagnostics.tsx` (新增)

### [EV2-T5-03] 评分趋势对比

**类型**: Frontend · **优先级**: P2 · **预估**: 1.5h

**描述**: 评估趋势图按 RAG/LLM/Answer 三组分别绘线，帮助用户判断哪个维度在改善/恶化。

**验收标准**:
- [x] 更新现有趋势图组件，支持三线对比（RAG/LLM/Answer）
- [x] 颜色与评分卡一致（蓝/紫/绿）
- [x] 支持时间范围筛选（最近 10/50/100 条）
- [x] 新增 EvalTrendChart.tsx 组件，集成到 EvaluationPage 右侧面板
- [x] 纯 SVG 实现，支持 hover tooltip 和趋势方向指示器

**文件**: `features/engine/evaluation/components/EvaluationPage.tsx`

---

## 模块文件变更

```
engine_v2/
├── retrievers/
│   └── hybrid.py                       ← 改造 (检索策略标记)
├── evaluation/
│   ├── evaluator.py                    ← 改造 (FullEvalResult + 聚合计算)
│   ├── history.py                      ← 改造 (full_evaluate + 持久化)
│   └── answer_evaluators.py            ← 新增 (Completeness + Clarity)
├── query_engine/
│   └── router.py                       ← 新增 (Depth→策略路由器)
├── api/routes/
│   └── query.py                        ← 改造 (自动评估 + retrieval_mode + stats)
├── schema.py                           ← 改造 (build_source 增加 retrieval_source)
└── settings.py                         ← 改造 (AUTO_EVAL + EVAL_WEIGHTS + EVAL_PASS_THRESHOLDS)

payload-v2/
├── src/collections/
│   └── Evaluations.ts                  ← 改造 (新增四分类字段)
└── src/features/
    ├── shared/types.ts                 ← 改造 (SourceInfo + EvalResult 新字段)
    ├── chat/panel/
    │   └── ChatInput.tsx               ← 改造 (retrieval_mode 选择)
    └── engine/evaluation/components/
        ├── EvalScoreCard.tsx            ← 新增
        ├── RetrievalDiagnostics.tsx     ← 新增
        └── EvaluationPage.tsx           ← 改造 (四分类展示 + 状态过滤)
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 1** | EV2-T1-01, T1-02 (检索策略后端) | 3h | 无 | 纯代码，零 LLM 调用，立即可做 |
| **Phase 2** | EV2-T2-01, T2-02 (Answer Evaluator + FullEvalResult) | 3.5h | 无 | 评估核心重构 |
| **Phase 3** | EV2-T2-03, T2-04 (full_evaluate + Payload 扩展) | 2.5h | Phase 2 | 评估 pipeline 闭环 |
| **Phase 4** | EV2-T3-01, T3-02 (自动评估 + 达标判定) | 3h | Phase 3 | 后端核心 |
| **Phase 5** | EV2-T1-03, T3-03, T5-01 (前端策略标签 + 状态 + 评分卡) | 4.5h | Phase 1,4 | 前端体验 |
| **Phase 6** | EV2-T4-01, T4-03 (路由器 + retrieval_mode) | 5h | Phase 4 | Agentic 基座 |
| **Phase 7** | EV2-T4-02, T5-02, T5-03 (路由评估 + 诊断 + 趋势) | 5.5h | Phase 6 | 数据驱动优化 |

---

## 与其他 Sprint 的关系

| Sprint | 关系 | 说明 |
|--------|------|------|
| Sprint EC (14) | **部分替代** | EC-T2 自动评估被 EV2-T3 替代（更完整）；EC-T1 Query 删除和 EC-T3 高分报告保留独立 |
| Sprint 5 (06) | **前置依赖** | EV2-T4 路由器为 S5 smart_retrieve 和 Deep Solve 提供路由入口；S5 反过来填充 EV2 路由的具体策略 |
| Sprint 3 (03) | **协同** | S3 评估图表可直接消费四分类评分数据，按 RAG/LLM/Answer 分组展示 |
