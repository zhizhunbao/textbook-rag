# Sprint Eval-Curation — 回答筛选 + 自动评估 + 高分报告 (TBD)

> 目标：用户可以删除低质量回答，系统自动评估新回答，基于高评分回答历史生成质量报告。
>
> 前置条件：S2 ✅ evaluation 5 维评估 + 持久化 + history.py 已完成；DM-T5 ✅ Report MVP 已完成。
> **状态**: ❌ 0/9 完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Query 删除 | 2 | 2h | 前后端支持单条 Query 删除 |
| T2 自动评估触发 | 3 | 4h | 新回答自动触发评估 + 不达标标记 |
| T3 高分报告生成 | 4 | 5h | 按评分过滤 + 仅高分回答生成报告 |
| **合计** | **9** | **11h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 模块归属 | 删除 API 在 `engine_v2/api/routes/evaluation.py`；前端在 `features/engine/evaluation/`；报告逻辑在 `engine_v2/report/` |
| G2 | 数据流方向 | 前端删除走 Payload `/api/queries/{id}` (DELETE)，不直接调 Engine |
| G3 | 不破坏现有 | 现有 evaluate_single / evaluate_batch / report generate 接口不变 |

---

## [EC-T1] Query 级别删除

### [EC-T1-01] 前端 Query 删除 API + UI

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: 在 EvaluationPage 的 Query 列表中，每条记录添加删除按钮。点击后调用 Payload REST API 删除对应 Queries 记录。

**当前**: EvaluationPage 可以浏览 Queries 列表、触发评估，但不能删除单条 Query。
**改为**: 每条 Query 行增加 🗑️ 删除按钮，点击后 `DELETE /api/queries/{id}`，并同步删除关联的 Evaluations。

**验收标准**:
- [ ] `evaluation/api.ts` 新增 `deleteQuery(id: number)` — 调用 `DELETE /api/queries/${id}`
- [ ] `evaluation/api.ts` 新增 `deleteEvaluationsByQuery(queryId: number)` — 删除关联评估
- [ ] EvaluationPage Query 列表每行增加删除按钮（hover 时显示）
- [ ] 删除前 confirm 对话框："删除此回答及其评估数据？"
- [ ] 删除后自动刷新列表
- [ ] G2 ✅ 走 Payload `/api/*` REST，不调 Engine

**文件**: `features/engine/evaluation/api.ts`, `features/engine/evaluation/components/EvaluationPage.tsx`

### [EC-T1-02] 批量删除 + 按分数过滤删除

**类型**: Frontend · **优先级**: P2 · **预估**: 1h

**描述**: 支持批量选择 + 一键删除低分回答。提供分数阈值过滤器，用户可以快速筛选并批量删除不满足阈值的回答。

**验收标准**:
- [ ] EvaluationPage 增加分数过滤器（滑块或输入框，设置最低分阈值）
- [ ] 支持多选 checkbox + "删除选中" 按钮
- [ ] "删除低分回答" 快捷按钮（删除所有低于阈值的已评估回答）
- [ ] 批量删除走 `Promise.all(ids.map(deleteQuery))`
- [ ] 操作完成后显示 toast 通知："已删除 N 条回答"

**文件**: `features/engine/evaluation/components/EvaluationPage.tsx`, `features/engine/evaluation/api.ts`

---

## [EC-T2] 自动评估触发

### [EC-T2-01] 查询后自动触发评估

**类型**: Backend · **优先级**: P1 · **预估**: 2h

**描述**: 在 `/engine/query/stream` 完成后，自动异步触发 `evaluate_single_from_query()` 对刚产生的回答进行 5 维评估。评估结果写入 Payload Evaluations 集合。

**当前**: 评估需要用户在 EvaluationPage 手动点击"Evaluate"按钮触发。
**改为**: 每次查询完成后，后台自动异步评估。用户仍可在 EvaluationPage 查看/重新评估。

**验收标准**:
- [ ] `query.py` 的 `_stream_generator()` 在 `done` event 之后，通过 `asyncio.create_task()` 异步触发评估
- [ ] 评估在后台执行，不阻塞 SSE 流响应
- [ ] 评估结果自动写入 Payload Evaluations 集合（复用 `history.py` 的 `_persist_evaluation()`）
- [ ] 可通过 `settings.py` 的 `AUTO_EVAL_ENABLED` 环境变量控制开关（默认关闭）
- [ ] 评估失败不影响查询响应（静默捕获异常，仅 log）

**文件**: `engine_v2/api/routes/query.py`, `engine_v2/settings.py`

### [EC-T2-02] 评估结果标记不达标

**类型**: Backend · **优先级**: P2 · **预估**: 1h

**描述**: 在 `_persist_evaluation()` 中增加"达标/不达标"判定逻辑。将判定结果作为 `status` 字段写入 Evaluations 集合。

**阈值规则** (可通过 settings.py 配置):
- `faithfulness ≥ 0.7` AND `answer_relevancy ≥ 0.6` → `status: "pass"`
- 否则 → `status: "fail"`

**验收标准**:
- [ ] `evaluation/history.py` 的 `_persist_evaluation()` 增加 `status` 字段计算
- [ ] `settings.py` 新增 `EVAL_PASS_THRESHOLDS` 配置 (dict)
- [ ] Payload Evaluations 集合新增 `status` select 字段: `pass | fail | pending`
- [ ] 前端 EvaluationPage 显示 ✅/❌ 图标标记达标状态

**文件**: `engine_v2/evaluation/history.py`, `engine_v2/settings.py`, Payload `collections/Evaluations.ts`

### [EC-T2-03] 前端评估状态显示

**类型**: Frontend · **优先级**: P2 · **预估**: 1h

**描述**: EvaluationPage 的 Query 列表中显示评估状态（pass/fail/pending），并支持按状态过滤。

**验收标准**:
- [ ] Query 列表增加状态列（✅ Pass / ❌ Fail / ⏳ Pending）
- [ ] 状态过滤器：All / Pass Only / Fail Only / Pending
- [ ] 状态对应颜色编码（绿/红/灰）
- [ ] `types.ts` 的 `EvaluationResult` 增加 `status: 'pass' | 'fail' | 'pending'`

**文件**: `features/engine/evaluation/types.ts`, `features/engine/evaluation/components/EvaluationPage.tsx`

---

## [EC-T3] 高分报告生成

### [EC-T3-01] ReportGenerator 支持分数过滤

**类型**: Backend · **优先级**: P1 · **预估**: 1.5h

**描述**: `ReportGenerator` 增加可选的 `min_score` 参数。生成报告时，只纳入评估分数达标（status=pass）的 Q&A 对，自动排除低质量回答。

**当前**: `ReportGenerator.collect_data()` 拉取 session 的所有 messages + evaluations。
**改为**: 增加 `min_score` / `status_filter` 参数，仅纳入高分回答。

**验收标准**:
- [ ] `ReportGenerator.generate()` 新增 `quality_filter: "all" | "pass_only"` 参数
- [ ] `_fetch_evaluations()` 支持 `status` 过滤
- [ ] 当 `quality_filter="pass_only"` 时，只纳入 `status=pass` 的 Q&A
- [ ] 报告中注明 "Based on N high-quality responses (M total)"

**文件**: `engine_v2/report/generator.py`

### [EC-T3-02] 报告生成 API 扩展

**类型**: Backend · **优先级**: P1 · **预估**: 0.5h

**描述**: `/engine/report/generate` 接口增加 `quality_filter` 参数。

**验收标准**:
- [ ] `POST /engine/report/generate` body 新增 `quality_filter: "all" | "pass_only"` (默认 "all")
- [ ] 透传到 `ReportGenerator.generate(quality_filter=...)`

**文件**: `engine_v2/api/routes/report.py`

### [EC-T3-03] 前端报告生成选项

**类型**: Frontend · **优先级**: P1 · **预估**: 1.5h

**描述**: ReportPage 的"Generate Report"对话框中增加质量过滤选项。让用户选择"基于全部回答"或"仅基于高分回答"生成报告。

**验收标准**:
- [ ] 生成报告对话框增加 Radio: "All responses" / "High-quality only (pass)"
- [ ] 选择 "High-quality only" 时，显示当前 session 的 pass/fail 统计
- [ ] API 调用携带 `quality_filter` 参数
- [ ] 生成的报告 card 上标注 filter 模式

**文件**: `features/report/ReportPage.tsx`

### [EC-T3-04] 全局高分回答历史报告

**类型**: Backend + Frontend · **优先级**: P2 · **预估**: 1.5h

**描述**: 新增"全局报告"模式 — 不限于单个 session，跨所有 session 收集高分回答，生成综合质量报告。包括整体评估指标趋势、最佳回答案例、常见弱项分析。

**验收标准**:
- [ ] `ReportGenerator` 新增 `generate_global_report()` 方法
- [ ] 从 Evaluations 集合拉取所有 `status=pass` 的记录
- [ ] 报告包含：总体评估分布、Top-10 高分回答、低分模式分析、改进建议
- [ ] `POST /engine/report/generate-global` — body: `{ n_recent, quality_filter }`
- [ ] ReportPage 增加 "Generate Global Report" 按钮

**文件**: `engine_v2/report/generator.py`, `engine_v2/api/routes/report.py`, `features/report/ReportPage.tsx`

---

## 模块文件变更

```
engine_v2/
├── api/routes/
│   ├── query.py                    ← 改造 (自动评估触发)
│   └── report.py                   ← 改造 (quality_filter 参数)
├── evaluation/
│   └── history.py                  ← 改造 (status 判定)
├── report/
│   └── generator.py                ← 改造 (分数过滤 + 全局报告)
└── settings.py                     ← 改造 (AUTO_EVAL_ENABLED + EVAL_PASS_THRESHOLDS)

payload-v2/
├── collections/
│   └── Evaluations.ts              ← 改造 (新增 status 字段)
└── src/features/
    ├── engine/evaluation/
    │   ├── api.ts                   ← 改造 (deleteQuery + status 过滤)
    │   ├── types.ts                 ← 改造 (status 类型)
    │   └── components/
    │       └── EvaluationPage.tsx   ← 改造 (删除按钮 + 状态过滤)
    └── report/
        └── ReportPage.tsx           ← 改造 (quality_filter 选项)
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 备注 |
|-------|-------|-----------|------|
| **Phase 1** | EC-T1-01 (Query 删除) | 1h | 立即可用的管理功能 |
| **Phase 2** | EC-T2-01/02 (自动评估 + 达标判定) | 3h | 后端核心 |
| **Phase 3** | EC-T2-03 + EC-T1-02 (前端状态 + 批量删除) | 2h | 前端体验完善 |
| **Phase 4** | EC-T3-01/02/03/04 (高分报告) | 5h | 报告闭环 |
