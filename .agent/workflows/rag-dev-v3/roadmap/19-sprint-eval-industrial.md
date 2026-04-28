# Sprint Eval-Industrial — 工业级 RAG 评估升级

> 目标：将评估体系从纯 LLM-as-Judge 升级到 RAGAS 等效工业级标准。引入检索硬指标（纯数学计算、不依赖 LLM）、Golden Dataset、GuidelineEvaluator、CorrectnessEvaluator（F1）、PairwiseComparison。
>
> 前置条件：Sprint EV2 ✅ 四分类评分 + 检索策略溯源 + 自动评估已完成。
> 参考源码：`.github/references/llama_index/llama-index-core/llama_index/core/evaluation/`
> **状态**: ✅ 14/14 完成 (EI-T1-01 ✅ EI-T1-02 ✅ EI-T1-03 ✅ EI-T2-01 ✅ EI-T2-02 ✅ EI-T2-03 ✅ EI-T3-01 ✅ EI-T3-02 ✅ EI-T3-03 ✅ EI-T4-01 ✅ EI-T4-02 ✅ EI-T5-01 ✅ EI-T5-02 ✅ EI-T5-03 ✅)

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Golden Dataset 基建 | 3 | 5h | 数据集生成 + 存储 + 管理 |
| T2 检索硬指标 | 3 | 5h | HitRate/MRR/Precision/Recall/NDCG (纯数学) |
| T3 生成质量升级 | 3 | 4h | GuidelineEvaluator + CorrectnessEvaluator |
| T4 A/B 比较评估 | 2 | 4h | PairwiseComparison + 历史对比 |
| T5 前端评分卡升级 | 3 | 4.5h | 第 5 卡片 (IR) + Guidelines 展示 + 指标说明 |
| **合计** | **14** | **22.5h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 模块归属 | Golden Dataset 在 `engine_v2/evaluation/`；检索指标在 `engine_v2/evaluation/retrieval_metrics.py` |
| G2 | 数据流方向 | Golden Dataset 存储在 Payload `GoldenDataset` 集合；前端读取走 `/api/golden-dataset` |
| G3 | 不破坏现有 | 现有 `full_evaluate()` 保持向后兼容；新指标为增量扩展 |
| G4 | 零依赖 | 所有工具使用 LlamaIndex 内置评估器，不引入 ragas 等外部库 |
| G5 | 硬指标优先 | 检索指标 (HitRate/MRR/P@K/R@K/NDCG) 为纯数学计算，不依赖 LLM 调用 |

---

## [EI-T1] Golden Dataset 基建

> 现状：所有评估都是 LLM-as-Judge（LLM 给自己打分），无标准答案对比。工业级评估的前提是 Golden Dataset。

### [EI-T1-01] Golden Dataset 自动生成

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 使用 LlamaIndex `DatasetGenerator` 从已入库的 textbook chunks 自动生成 QA 对（问题 + 标准答案 + 来源 chunk IDs）。

**参考源码**: `evaluation/dataset_generation.py` — `DatasetGenerator.from_documents()`

**实现方案**:
- 从 ChromaDB 按 book_id 拉取已有 TextNode
- `DatasetGenerator(nodes=nodes, num_questions_per_chunk=3)` 生成 QA 对
- 每条记录包含：`question`, `expected_answer`, `expected_chunk_ids[]`, `book_id`, `source_page`
- 生成后需人工审核（标记 `verified: true/false`）

**验收标准**:
- [ ] 新增 `engine_v2/evaluation/golden_dataset.py`
- [ ] `generate_golden_dataset(book_id, n_questions=50)` 异步函数
- [ ] 输出 JSON 格式，包含 question + expected_answer + expected_chunk_ids
- [ ] 支持按 book_id 过滤生成范围
- [ ] G1 ✅ 在 `engine_v2/evaluation/`
- [ ] G4 ✅ 使用 LlamaIndex 内置 `DatasetGenerator`

**文件**: `engine_v2/evaluation/golden_dataset.py` (新增)

### [EI-T1-02] Payload GoldenDataset 集合

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1.5h

**描述**: 新增 Payload CMS 集合存储 Golden Dataset 记录。

**Schema**:
```
GoldenDataset {
  question: text (required)
  expectedAnswer: textarea (required)
  expectedChunkIds: json (array of string)
  bookRef: relationship → Books
  sourcePage: text
  verified: checkbox (default: false)
  tags: json (optional, e.g. ["factual", "synthesis"])
}
```

**验收标准**:
- [ ] 新增 `payload-v2/src/collections/GoldenDataset.ts`
- [ ] Admin UI 可 CRUD Golden Dataset 记录
- [ ] 支持按 book、verified 状态过滤
- [ ] G2 ✅ 前端通过 `/api/golden-dataset` 读取

**文件**: `payload-v2/src/collections/GoldenDataset.ts` (新增)

### [EI-T1-03] Golden Dataset 生成 API + 管理页面

**类型**: Backend + Frontend · **优先级**: P1 · **预估**: 1.5h

**描述**: Engine API 端点触发生成；Admin 管理页面审核/编辑 Golden Dataset。

**验收标准**:
- [ ] Engine API: `POST /engine/evaluation/generate-golden-dataset` (book_id, n_questions)
- [ ] 生成结果自动写入 Payload GoldenDataset 集合
- [ ] Admin 页面：列表 + 编辑 + 标记 verified + 删除
- [ ] 进度显示（生成中 / 完成 / 失败）

**文件**: `engine_v2/api/routes/evaluation.py`, Admin UI 组件

---

## [EI-T2] 检索硬指标（纯数学，不依赖 LLM）

> 现状：检索质量仅有 LLM-judge 的 Context Relevancy (0-1)。无法准确衡量"检索到的 chunk 对不对"。

### [EI-T2-01] 检索指标计算模块

**类型**: Backend · **优先级**: P0 · **预估**: 2h

**描述**: 封装 LlamaIndex 内置的 5 个检索指标，统一接口。

**参考源码**: `evaluation/retrieval/metrics.py` — HitRate, MRR, Precision, Recall, NDCG

**实现方案**:
```python
from llama_index.core.evaluation.retrieval.metrics import (
    HitRate, MRR, Precision, Recall, NDCG,
)

def compute_retrieval_metrics(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> dict[str, float]:
    """计算 5 个检索硬指标。纯数学计算，零 LLM 调用。"""
    return {
        "hit_rate": HitRate().compute(retrieved_ids=retrieved_ids, expected_ids=expected_ids).score,
        "mrr": MRR().compute(retrieved_ids=retrieved_ids, expected_ids=expected_ids).score,
        "precision": Precision().compute(retrieved_ids=retrieved_ids, expected_ids=expected_ids).score,
        "recall": Recall().compute(retrieved_ids=retrieved_ids, expected_ids=expected_ids).score,
        "ndcg": NDCG().compute(retrieved_ids=retrieved_ids, expected_ids=expected_ids).score,
    }
```

**验收标准**:
- [ ] 新增 `engine_v2/evaluation/retrieval_metrics.py`
- [ ] `compute_retrieval_metrics(retrieved_ids, expected_ids)` 返回 5 个分数
- [ ] 零 LLM 调用（纯数学计算）
- [ ] G5 ✅ 硬指标优先

**文件**: `engine_v2/evaluation/retrieval_metrics.py` (新增)

### [EI-T2-02] 检索指标集成到 full_evaluate()

**类型**: Backend · **优先级**: P0 · **预估**: 1.5h

**描述**: 在 `full_evaluate()` 中，当 Golden Dataset 有对应记录时，自动计算检索硬指标并写入 FullEvalResult。

**实现方案**:
1. `full_evaluate(query_id)` 内部查 GoldenDataset 集合，匹配 question (semantic similarity > 0.9)
2. 如果找到匹配的 golden record → 从 stored sources 提取 retrieved_ids
3. 调用 `compute_retrieval_metrics(retrieved_ids, expected_ids)`
4. 写入 `FullEvalResult` 新字段

**FullEvalResult 新增字段**:
```python
# IR 检索硬指标（需要 Golden Dataset）
hit_rate: float | None = None
mrr: float | None = None
precision_at_k: float | None = None
recall_at_k: float | None = None
ndcg: float | None = None
ir_score: float | None = None  # mean of above
golden_match_id: int | None = None  # 匹配到的 GoldenDataset record ID
```

**验收标准**:
- [ ] `FullEvalResult` 新增 IR 指标字段
- [ ] `full_evaluate()` 自动匹配 Golden Dataset
- [ ] 无 Golden Dataset 匹配时，IR 字段为 None（不影响现有评分）
- [ ] `compute_aggregate_scores()` 更新：overall 加入 IR 权重
- [ ] G3 ✅ 无 Golden Dataset 时完全向后兼容

**文件**: `engine_v2/evaluation/evaluator.py`, `engine_v2/evaluation/history.py`

### [EI-T2-03] Payload Evaluations 集合扩展 (IR)

**类型**: Backend (Payload) · **优先级**: P1 · **预估**: 1.5h

**描述**: Evaluations 集合新增 IR 检索硬指标字段。

**验收标准**:
- [ ] 新增字段：`hitRate`, `mrr`, `precisionAtK`, `recallAtK`, `ndcg`, `irScore` (number, 0-1)
- [ ] 新增字段：`goldenMatchRef` (relationship → GoldenDataset, optional)
- [ ] `_persist_full_evaluation()` 写入新字段
- [ ] G3 ✅ 现有字段不变

**文件**: `payload-v2/src/collections/Evaluations.ts`

---

## [EI-T3] 生成质量升级

> 现状：Completeness + Clarity 用自定义 CorrectnessEvaluator 继承，太泛且容易偏高。缺少 ground-truth 对比的 Correctness。

### [EI-T3-01] GuidelineEvaluator 替换 Completeness + Clarity

**类型**: Backend · **优先级**: P1 · **预估**: 1.5h

**描述**: 用 LlamaIndex 内置 `GuidelineEvaluator` 替换自定义的 Completeness + Clarity。一次 LLM 调用同时评估多条规则。

**参考源码**: `evaluation/guideline.py` — `GuidelineEvaluator`

**自定义 Guidelines**:
```python
QUALITY_GUIDELINES = (
    "The response MUST directly answer the user's question.\n"
    "The response MUST cite specific evidence from the provided context.\n"
    "The response MUST NOT include information not supported by the context.\n"
    "The response MUST use professional, clear language.\n"
    "The response MUST include quantitative data when available in the context.\n"
    "The response MUST acknowledge when the context does not contain sufficient information.\n"
)
```

**验收标准**:
- [ ] `full_evaluate()` 中用 `GuidelineEvaluator(guidelines=QUALITY_GUIDELINES)` 替换 `CompletenessEvaluator` + `ClarityEvaluator`
- [ ] 2 次 LLM 调用 → 1 次（节省 token）
- [ ] `FullEvalResult` 新增 `guidelines_pass: bool`, `guidelines_feedback: str`
- [ ] Guidelines 内容可通过 `settings.py` / 环境变量配置
- [ ] 评分卡 Answer 组中显示 Guidelines Pass/Fail + 具体反馈
- [ ] G4 ✅ 减少 LLM 调用

**文件**: `engine_v2/evaluation/history.py`, `engine_v2/evaluation/prompts.py`, `engine_v2/settings.py`

### [EI-T3-02] CorrectnessEvaluator 集成 (需 Ground Truth)

**类型**: Backend · **优先级**: P1 · **预估**: 1.5h

**描述**: 当 Golden Dataset 有匹配时，用 `CorrectnessEvaluator` 做 answer vs expected_answer 的 F1 对比。

**参考源码**: `evaluation/correctness.py` — CorrectnessEvaluator (score 1-5 + reasoning)

**实现方案**:
```python
from llama_index.core.evaluation import CorrectnessEvaluator

correctness_eval = CorrectnessEvaluator()
result = await correctness_eval.aevaluate(
    query=question,
    response=actual_answer,
    reference=golden_answer,  # from GoldenDataset
)
# result.score: 1.0-5.0 → normalize to 0-1
```

**验收标准**:
- [ ] `full_evaluate()` 中有 Golden Dataset 匹配时运行 `CorrectnessEvaluator`
- [ ] `FullEvalResult` 新增 `correctness: float | None` (0-1, normalized from 1-5)
- [ ] 无 Golden Dataset 时 correctness = None
- [ ] Answer Score 聚合中加入 correctness（有时参与加权）

**文件**: `engine_v2/evaluation/history.py`, `engine_v2/evaluation/evaluator.py`

### [EI-T3-03] Cross-Model Evaluation（可选）

**类型**: Backend · **优先级**: P2 · **预估**: 1h

**描述**: 支持用不同 LLM 做 judge（消除"自己评自己"的偏差）。例如用 gpt-4o-mini 生成回答，用 llama3.2:3b 做评分。

**验收标准**:
- [x] `full_evaluate()` 新增 `judge_model: str | None` 参数
- [x] `judge_model` 与 `model` 不同时，log 标记为 cross-model evaluation
- [x] `FullEvalResult` 新增 `judge_model: str | None` 字段
- [x] 默认不启用（向后兼容）

**文件**: `engine_v2/evaluation/history.py`

---

## [EI-T4] A/B 比较评估

> 现状：改了 retriever 参数后无法量化对比新旧 pipeline 的差异。

### [EI-T4-01] PairwiseComparison 集成

**类型**: Backend · **优先级**: P2 · **预估**: 2.5h

**描述**: 集成 LlamaIndex 内置 `PairwiseComparisonEvaluator`，支持两套 pipeline 答案的 A/B 对比。

**参考源码**: `evaluation/pairwise.py` — `PairwiseComparisonEvaluator(enforce_consensus=True)`

**实现方案**:
```python
from llama_index.core.evaluation import PairwiseComparisonEvaluator

pairwise_eval = PairwiseComparisonEvaluator(enforce_consensus=True)
result = await pairwise_eval.aevaluate(
    query=question,
    response=new_answer,
    second_response=old_answer,
    reference=golden_answer,
)
# enforce_consensus=True → 翻转顺序跑两次，消除位置偏差
```

**验收标准**:
- [x] 新增 `engine_v2/evaluation/pairwise.py`
- [x] `compare_answers(question, answer_a, answer_b, reference=None)` 异步函数
- [x] 返回 winner ("A"/"B"/"tie") + reasoning
- [x] `enforce_consensus=True` 消除位置偏差
- [x] API 端点 `POST /engine/evaluation/compare` 暴露

**文件**: `engine_v2/evaluation/pairwise.py` (新增)

### [EI-T4-02] A/B 批量对比 API

**类型**: Backend + Frontend · **优先级**: P2 · **预估**: 1.5h

**描述**: 用 Golden Dataset 批量跑 A/B 对比，输出汇总报告。

**验收标准**:
- [x] API: `POST /engine/evaluation/compare-batch` (items + judge_model)
- [x] 批量跑 A/B 对比，对比两套答案
- [x] 输出汇总：A 胜 N 条 / B 胜 M 条 / 平手 K 条
- [x] 前端 Admin 页面展示对比结果（API ready，前端延后）

**文件**: `engine_v2/api/routes/evaluation.py`, Admin UI 组件

---

## [EI-T5] 前端评分卡升级

### [EI-T5-01] EvalScoreCard 第 5 卡片 (IR 检索硬指标)

**类型**: Frontend · **优先级**: P1 · **预估**: 1.5h

**描述**: EvalScoreCard 新增第 5 个卡片显示检索硬指标。

**展示格式**:
```
┌─────────────────────────┐
│ 📊 IR (Retrieval)   0.76 │
│ HitRate         ████ 1.00 │
│ MRR             ███  0.50 │
│ Precision@5     ██   0.40 │
│ Recall@5        ████ 1.00 │
│ NDCG            ███▌ 0.83 │
└─────────────────────────┘
```

> 当无 Golden Dataset 匹配时，显示 "No golden data — IR metrics unavailable"

**验收标准**:
- [x] EvalScoreCard `CATEGORIES` 新增 IR 类别（颜色: cyan/teal）
- [x] 5 个 IR 维度各有进度条
- [x] 无 Golden Dataset 时显示占位提示
- [x] 顶部摘要条新增 IR 百分比
- [x] 对齐现有 RAG/LLM/Answer/Question 卡片布局

**文件**: `features/engine/evaluation/components/EvalScoreCard.tsx`, `features/engine/evaluation/types.ts`

### [EI-T5-02] Guidelines 反馈展示

**类型**: Frontend · **优先级**: P1 · **预估**: 1.5h

**描述**: Answer 卡片中显示 GuidelineEvaluator 的 pass/fail 结果和具体反馈文本。

**验收标准**:
- [x] Answer 卡片新增 "Guidelines" 行：Pass/Fail badge
- [x] 点击展开显示 GuidelineEvaluator 的 feedback 文本
- [x] Fail 时高亮显示哪条规则未通过
- [x] 配色与 Answer 组一致（绿色系）

**文件**: `features/engine/evaluation/components/EvalScoreCard.tsx`

### [EI-T5-03] 指标解释 Tooltip

**类型**: Frontend · **优先级**: P2 · **预估**: 1.5h

**描述**: 每个指标名称旁增加 info icon，hover 显示解释 tooltip。

**Tooltip 内容**:
| 指标 | Tooltip |
|---|---|
| HitRate | "检索结果中是否包含正确答案 (1=命中, 0=未命中)" |
| MRR | "第一个正确结果的排名倒数 (1=排第一, 0.5=排第二)" |
| Precision@K | "Top-K 结果中正确的比例" |
| Recall@K | "正确答案被检索到的比例" |
| NDCG | "正确结果是否排在前面 (考虑排序质量)" |
| Faithfulness | "回答是否基于给定 context，无幻觉" |
| Context Relevancy | "检索到的内容与问题是否相关" |
| Guidelines | "回答是否符合预设质量规则" |
| Correctness | "回答与标准答案的事实重合度 (F1)" |

**验收标准**:
- [x] 每个维度标签旁有 info SVG icon (lucide `Info`)
- [x] Hover 显示 tooltip，包含中英文解释
- [x] 不影响现有布局

**文件**: `features/engine/evaluation/components/EvalScoreCard.tsx`

---

## 模块文件变更

```
engine_v2/evaluation/
├── evaluator.py              ← 改造 (FullEvalResult 新增 IR + correctness + guidelines 字段)
├── history.py                ← 改造 (full_evaluate 集成 IR + Guideline + Correctness)
├── golden_dataset.py         ← 新增 (Golden Dataset 生成 + 匹配)
├── retrieval_metrics.py      ← 新增 (HitRate/MRR/Precision/Recall/NDCG)
├── pairwise.py               ← 新增 (PairwiseComparison 封装)
└── prompts.py                ← 改造 (新增 QUALITY_GUIDELINES)

engine_v2/api/routes/
└── evaluation.py             ← 改造 (新增 generate-golden-dataset + compare 端点)

engine_v2/settings.py         ← 改造 (QUALITY_GUIDELINES 配置)

payload-v2/src/collections/
├── Evaluations.ts            ← 改造 (新增 IR 字段)
└── GoldenDataset.ts          ← 新增

payload-v2/src/features/engine/evaluation/
├── types.ts                  ← 改造 (新增 IR + guidelines 类型)
└── components/
    └── EvalScoreCard.tsx      ← 改造 (第 5 卡片 + Guidelines + Tooltip)
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 1** | EI-T1-01, T1-02 (Golden Dataset 生成 + 存储) | 3.5h | 无 | 基建优先 |
| **Phase 2** | EI-T2-01, T2-02 (检索硬指标 + 集成) | 3.5h | Phase 1 | 纯数学，零 LLM |
| **Phase 3** | EI-T3-01, T3-02 (Guideline + Correctness) | 3h | Phase 1 | 替换低质量指标 |
| **Phase 4** | EI-T2-03, T5-01 (Payload 扩展 + 前端 IR 卡片) | 3h | Phase 2 | 前端展示 |
| **Phase 5** | EI-T5-02, T5-03 (Guidelines 展示 + Tooltip) | 3h | Phase 3 | UX 打磨 |
| **Phase 6** | EI-T4-01, T4-02 (Pairwise + A/B 批量) | 4h | Phase 1 | 进阶功能 |
| **Phase 7** | EI-T3-03 (Cross-Model) | 1h | 无 | 可选增强 |
| **Phase 8** | EI-T1-03 (Golden Dataset 管理页面) | 1.5h | Phase 1 | Admin UX |

---

## LLM 调用次数对比

| 版本 | LLM 调用 | 硬指标 | 总维度 | 可信度 |
|------|----------|--------|--------|--------|
| 当前 (EV2) | 7 次 | 0 | 7 | LLM-judge only |
| 升级后 (EI) | 5 次 | 5 | 10+ | 数学 + LLM 混合 |

**调用分解 (升级后)**:
1. FaithfulnessEvaluator — 1 次 LLM
2. ContextRelevancyEvaluator — 1 次 LLM
3. AnswerRelevancyEvaluator — 1 次 LLM
4. GuidelineEvaluator — 1 次 LLM (替代 Completeness + Clarity 的 2 次)
5. CorrectnessEvaluator — 1 次 LLM (需 Golden Dataset)
6. HitRate/MRR/P@K/R@K/NDCG — 0 次 LLM (纯数学)
7. QuestionDepth — 1 次 LLM (保留为参考指标)

---

## 与其他 Sprint 的关系

| Sprint | 关系 | 说明 |
|--------|------|------|
| Sprint EV2 (16) | **继承** | EI 在 EV2 四分类基础上增量升级 |
| Sprint QD (13) | **互补** | QD 的 Question Dataset 可转化为 Golden Dataset |
| Sprint EC (14) | **增强** | EC-T3 高分报告可消费 IR 硬指标数据 |
| Sprint S5 (06) | **协同** | Pairwise 对比可用于评估 smart_retrieve vs standard 的效果 |
