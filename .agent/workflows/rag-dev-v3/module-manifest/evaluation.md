# `evaluation` — 质量评估

```
Layout
评估面板
指标图表

UI
评分卡片
雷达图表
对比表格

UX
批量评测
历史对比
导出报告

Func
忠实度评
相关性评
指标计算
报告汇总

Noun
Evaluation
Metric
Faithfulness
Relevancy
Score
Report
Benchmark
Comparison
```

```
evaluation
├── engine_v2/evaluation/
│   ├── __init__.py                         re-export 公共 API
│   └── evaluator.py                        忠实度 + 相关性评估器
├── engine_v2/api/routes/
│   └── evaluation.py                       评估端点
├── payload-v2/src/collections/
│   └── Evaluations.ts                      评估结果 Collection
├── payload-v2/src/features/engine/evaluation/
│   ├── index.ts                            barrel export
│   ├── types.ts                            EvalResult 等类型
│   ├── api.ts                              评估 API
│   └── components/
│       ├── TracePanel.tsx                  执行追踪面板
│       ├── TraceComponents.tsx             TraceStat · TraceHitList 子组件
│       └── ThinkingProcessPanel.tsx        思维过程展示面板
└── payload-v2/src/app/(frontend)/engine/evaluation/
    └── page.tsx                            /engine/evaluation 路由
```
