# Sprint EUX — 评估体验增强 (Eval UX Polish)

> 目标：解决三大体验缺陷 — ① Golden Dataset 自动生成解锁 IR 指标 ② 评估元数据透明 ③ 低分改进建议。
>
> 前置条件：EC ✅, EI ✅, EV2 ✅, QD ✅
> **状态**: ✅ 9/9 完成
>
> **参考**: LlamaIndex `llama_index/core/evaluation/` ([dataset_generation.py](../../.github/references/llama_index/llama-index-core/llama_index/core/evaluation/dataset_generation.py), [retrieval/metrics.py](../../.github/references/llama_index/llama-index-core/llama_index/core/evaluation/retrieval/metrics.py))

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Golden Auto-Verify | 2 | 1.5h | QD 生成时自动验证 + 解锁 IR 指标 |
| T2 元数据透明度 | 3 | 3h | 模型信息 + 请求计数 + 前端展示 |
| T3 改进建议 | 3 | 3h | 规则引擎 + 前端提示卡 |
| T4 IR 指标对齐 | 1 | 0.5h | 新增 AveragePrecision 对齐 LlamaIndex |
| **合计** | **9** | **8h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 参考对齐 | LlamaIndex `generate_question_context_pairs()` 的 `relevant_docs` 自动绑定模式 |
| G2 | 不破坏现有 | 现有 QD 生成 / Evaluation / EvalScoreCard 行为不变 |
| G3 | 模块归属 | suggestions 在 `engine_v2/evaluation/`；UI 变更在 `EvalScoreCard.tsx` |

---

## [EUX-T1] Golden Dataset Auto-Verify

> **动机**: 当前 QD 生成的问题需要人工标记 verified 才能计算 IR 指标。但 LlamaIndex 的 `generate_question_context_pairs()` 自动绑定 `relevant_docs`，无需人工审核。我们也应如此 — 生成时就知道来源 chunk，自动设为 verified。

### [EUX-T1-01] QD 生成时 auto-verify sourceChunk

**类型**: Backend · **优先级**: P0 · **预估**: 1h

**描述**: 修改 QD 生成逻辑，生成的问题自动标记 `verified: true`。因为生成的问题本身来自已知 chunk（我们知道 `sourceChunkId`），可以直接认定该 chunk 为 golden reference。

**参考**:
```python
# LlamaIndex (retriever_eval.ipynb L257-259):
qa_dataset = generate_question_context_pairs(nodes, llm=llm, num_questions_per_chunk=2)
# qa_dataset.relevant_docs[query_id] → 自动绑定 chunk IDs，无需人工
```

**当前**: QD 生成 → `verified: false` → 用户手动审核 → 才能计算 IR
**改为**: QD 生成 → `verified: true`（auto-verified）→ 立即可用于 IR 评估

**验收标准**:
- [x] `engine_v2/question_gen/` 生成后自动设置 `verified: true` + `verifiedAt: now`
- [x] 新增 `verificationSource` 字段: `"auto"` (自动) vs `"manual"` (人工)
- [x] 前端 QuestionDataset 页面显示 verification 来源标识（🤖 Auto / 👤 Manual）
- [x] 现有手动 verify 功能不受影响

**文件**: `engine_v2/question_gen/generator.py`, `collections/GoldenDatasets.ts` (或对应集合)

### [EUX-T1-02] 评估时自动匹配 Golden Record

**类型**: Backend · **优先级**: P0 · **预估**: 0.5h

**描述**: `full_evaluate()` 执行时，自动检查当前 query 是否匹配 Golden Dataset 中的 verified 记录。如果匹配则计算 IR 指标。

**当前**: IR 指标只在 `golden_dataset.py` 的独立接口中计算
**改为**: `full_evaluate()` 自动尝试匹配 golden record → 有匹配就计算 IR

**验收标准**:
- [x] `full_evaluate()` 增加 golden record 自动匹配逻辑（基于 question 文本相似度或 exact match）
- [x] 匹配成功时自动计算 HitRate/MRR/Precision/Recall/NDCG
- [x] 匹配失败时 IR 字段保持 null（向后兼容）

**文件**: `engine_v2/evaluation/history.py`

---

## [EUX-T2] 评估元数据透明度

### [EUX-T2-01] Evaluations Schema 增加元数据字段

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**描述**: Evaluations 集合新增 judgeModel / answerModel / llmCalls 字段，记录评估过程的关键元数据。

**Schema 变更**:
```
Evaluations {
  ...existing fields...
  judgeModel: text   — 评审 LLM (e.g. "azure/gpt-4o-mini")
  answerModel: text  — 回答 LLM (e.g. "llama3.2:3b")
  llmCalls: number   — 评估总 LLM 调用次数
}
```

**数据来源**:
- `judgeModel` — `_persist_full_evaluation()` 已传入 `result.judge_model` ✅，但 Collection schema 缺少此字段
- `answerModel` — 从 Queries 的 `model` 字段读取
- `llmCalls` — 在评估过程中累加计数

**验收标准**:
- [x] `Evaluations.ts` 新增 3 个字段 (judgeModel / answerModel / llmCalls)
- [x] `_persist_full_evaluation()` 已传 judgeModel ✅，增加 answerModel + llmCalls
- [x] `_persist_evaluation()` 同步增加这 3 个字段
- [x] 前端 `types.ts` EvaluationResult 增加对应类型

**文件**: `collections/Evaluations.ts`, `engine_v2/evaluation/history.py`, `features/engine/evaluation/types.ts`

### [EUX-T2-02] 评估过程 LLM 调用计数

**类型**: Backend · **优先级**: P1 · **预估**: 1h

**描述**: 在 `full_evaluate()` 中跟踪 LLM 调用次数。每次调用 evaluator 记为 1 次 LLM call。

**调用点清单**:
| 评估器 | LLM 调用数 |
|--------|-----------|
| QuestionDepthEvaluator | 1 |
| FaithfulnessEvaluator | 1 |
| AnswerRelevancyEvaluator | 1 |
| ContextRelevancyEvaluator | 1 |
| RelevancyEvaluator | 1 |
| CorrectnessEvaluator | 0-1 (有 reference 时) |
| CompletenessEvaluator | 1 |
| ClarityEvaluator | 1 |
| GuidelinesEvaluator | 1 |
| **典型总计** | **8-9** |

**验收标准**:
- [x] `FullEvalResult` dataclass 新增 `llm_calls: int` 字段
- [x] `full_evaluate()` 中每个 evaluator 调用后累加计数
- [x] 计数传入 `_persist_full_evaluation()` → 写入 Payload

**文件**: `engine_v2/evaluation/history.py`

### [EUX-T2-03] EvalScoreCard 显示模型信息 + 请求统计

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: EvalScoreCard 底部增加一行元数据：评审模型、回答模型、LLM 调用次数。

**UI 设计**:
```
┌──────────────────────────────────────┐
│  ⊘ Fail  44%                    ▼   │
│  [RAG 13%] [LLM 100%] [Answer 25%]  │
│  ...score cards...                   │
│                                      │
│  ⚙ Judge: azure/gpt-4o-mini         │
│  🤖 Answer: llama3.2:3b  │  8 calls │
└──────────────────────────────────────┘
```

**验收标准**:
- [x] EvalScoreCard 底部显示 judgeModel / answerModel
- [x] 显示 llmCalls (若有)
- [x] 字段为空时优雅隐藏
- [x] 文字用 muted 色，不喧宾夺主

**文件**: `features/engine/evaluation/components/EvalScoreCard.tsx`, `features/engine/evaluation/types.ts`

---

## [EUX-T3] 低分改进建议

### [EUX-T3-01] 规则引擎 — 基于分数维度生成建议

**类型**: Backend · **优先级**: P0 · **预估**: 1h

**描述**: 新增 `generate_suggestions()` 函数，根据各维度分数生成改进建议列表。纯规则驱动，不调 LLM。

**规则矩阵**:

| 条件 | Severity | 建议 (中) | 建议 (英) |
|------|----------|-----------|-----------|
| `relevancy < 0.3` | high | 检索来源与问题不匹配。建议：更具体地描述问题关键词 | Retrieved sources don't match. Try more specific keywords. |
| `faithfulness < 0.5` | high | 回答中存在幻觉风险。建议：缩小提问范围 | Hallucination risk detected. Narrow your question scope. |
| `answerRelevancy < 0.5` | medium | 回答偏离问题。建议：重新措辞，聚焦单一主题 | Answer drifts from the question. Rephrase to focus on one topic. |
| `contextRelevancy < 0.3` | medium | 检索到的文档关联度低。可能文档库中缺少相关内容 | Retrieved chunks aren't relevant. Knowledge base may lack coverage. |
| `questionDepth == 'surface'` | low | 尝试提出更深入的问题，如对比、分析或评价类 | Try deeper questions: compare, analyze, or evaluate. |
| `completeness < 0.5` | medium | 回答不够完整。建议拆分为多个子问题分别提问 | Answer is incomplete. Break into sub-questions. |
| `overallScore >= 0.85` | info | 高质量回答！可作为 Golden Dataset 参考 | High-quality answer! Consider adding to Golden Dataset. |

**验收标准**:
- [x] 新文件 `engine_v2/evaluation/suggestions.py`
- [x] `generate_suggestions(eval_result) → list[Suggestion]`
- [x] `Suggestion = { dimension: str, severity: 'high'|'medium'|'low'|'info', message_en: str, message_zh: str }`
- [x] 规则模板在 `evaluation/prompts.py` 中集中管理
- [x] 每条评估最多返回 3 条最相关建议（按 severity 排序）

**文件**: `engine_v2/evaluation/suggestions.py` (新增), `engine_v2/evaluation/prompts.py` (改造)

### [EUX-T3-02] 评估 API 返回建议

**类型**: Backend · **优先级**: P1 · **预估**: 0.5h

**描述**: `full_evaluate()` 返回值和持久化中包含 suggestions 列表。

**验收标准**:
- [x] `FullEvalResult` 新增 `suggestions: list[dict]`
- [x] `_persist_full_evaluation()` 将 suggestions 写入 Evaluations
- [x] Evaluations.ts 新增 `suggestions` json 字段
- [ ] 前端 types.ts 增加 Suggestion 类型

**文件**: `engine_v2/evaluation/history.py`, `collections/Evaluations.ts`, `types.ts`

### [EUX-T3-03] EvalScoreCard 显示改进建议

**类型**: Frontend · **优先级**: P0 · **预估**: 1.5h

**描述**: 当评估状态为 Fail 且有 suggestions 时，在评分卡下方展示可折叠的建议面板。

**UI 设计**:
```
┌──────────────────────────────────────┐
│  ⊘ Fail  44%                    ▼   │
│  ...score cards...                   │
│                                      │
│  💡 改进建议 (2)                 ▼   │
│  ┌────────────────────────────────┐  │
│  │ 🔴 检索来源与问题不匹配。      │  │
│  │    建议：更具体地描述问题关键词  │  │
│  │ 🟡 回答偏离问题。              │  │
│  │    建议：重新措辞，聚焦单一主题  │  │
│  └────────────────────────────────┘  │
│                                      │
│  ⚙ Judge: gpt-4o-mini  │  8 calls   │
└──────────────────────────────────────┘
```

**颜色编码**: 🔴 high = red-400, 🟡 medium = amber-400, 🟢 low = emerald-400, ℹ️ info = blue-400

**验收标准**:
- [ ] Fail 状态时自动展开建议面板
- [ ] Pass 状态时折叠隐藏（但可手动展开查看 info 建议）
- [ ] 建议条目按 severity 排序 + 颜色编码
- [ ] 双语 (根据 locale)
- [ ] 无 suggestions 时不渲染

**文件**: `features/engine/evaluation/components/EvalScoreCard.tsx`

---

## [EUX-T4] IR 指标对齐 LlamaIndex

### [EUX-T4-01] 新增 AveragePrecision 指标

**类型**: Backend · **优先级**: P2 · **预估**: 0.5h

**描述**: 对齐 LlamaIndex `METRIC_REGISTRY` 补充 AveragePrecision (AP) 指标。

**参考实现** ([metrics.py L275-334](../../.github/references/llama_index/llama-index-core/llama_index/core/evaluation/retrieval/metrics.py)):
```python
# LlamaIndex AveragePrecision — 遍历 retrieved_ids，累加 precision at each relevant hit
relevant_count, total_precision = 0, 0.0
for i, retrieved_id in enumerate(retrieved_ids, start=1):
    if retrieved_id in expected_set:
        relevant_count += 1
        total_precision += relevant_count / i
average_precision = total_precision / len(expected_set)
```

**验收标准**:
- [ ] `engine_v2/evaluation/golden_dataset.py` 新增 `_compute_average_precision()`
- [ ] Evaluations schema + types.ts 新增 `averagePrecision` 字段
- [ ] EvalScoreCard IR 卡片增加 AP 维度行
- [ ] 对齐 LlamaIndex `METRIC_REGISTRY` 的 6 种指标: hit_rate ✅, mrr ✅, precision ✅, recall ✅, ndcg ✅, **ap ✅**

**文件**: `engine_v2/evaluation/golden_dataset.py`, `collections/Evaluations.ts`, `EvalScoreCard.tsx`

---

## 模块文件变更

```
engine_v2/
├── evaluation/
│   ├── history.py             ← 改造 (llmCalls + answerModel + auto-golden-match)
│   ├── suggestions.py         ← 新增 (规则引擎)
│   ├── golden_dataset.py      ← 改造 (AveragePrecision)
│   └── prompts.py             ← 改造 (建议模板)
├── question_gen/
│   └── generator.py           ← 改造 (auto-verify)
└── api/routes/
    └── evaluation.py          ← (无需改造，suggestions 随 evaluation 返回)

payload-v2/
├── collections/
│   ├── Evaluations.ts         ← 改造 (新增 judgeModel/answerModel/llmCalls/suggestions/averagePrecision)
│   └── GoldenDatasets.ts      ← 改造 (新增 verificationSource)
└── src/features/engine/evaluation/
    ├── types.ts               ← 改造 (新增类型)
    └── components/
        └── EvalScoreCard.tsx  ← 改造 (元数据行 + 建议面板 + AP 维度)
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 1** | EUX-T1-01 (Auto-Verify) | 1h | 无 | 最高 ROI — 立即解锁 IR 指标 |
| **Phase 2** | EUX-T2-01 (Schema) + EUX-T3-01 (规则引擎) | 2h | 无 | 可并行 |
| **Phase 3** | EUX-T1-02 (Auto-Match) + EUX-T2-02 (计数) + EUX-T3-02 (API) | 2h | Phase 1+2 |
| **Phase 4** | EUX-T2-03 + EUX-T3-03 (前端) | 2.5h | Phase 3 | UI 收尾 |
| **Phase 5** | EUX-T4-01 (AP 指标) | 0.5h | Phase 3 | 可选对齐 |
