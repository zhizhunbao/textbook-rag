# `retrievers` — 检索引擎

```
Layout
配置表单
结果预览

UI
参数滑块
策略选择
片段列表

UX
即调即试
对比查看
相关高亮

Func
向量搜索
BM25 检索
混合融合
重排精选

Noun
Retriever
Query
Result
Score
Node
Strategy
TopK
Reranker
```

```
retrievers
├── engine_v2/retrievers/
│   ├── __init__.py                         re-export 公共 API
│   └── hybrid.py                           混合检索 (FTS + Vector + RRF)
├── engine_v2/api/routes/
│   └── retrievers.py                       检索配置端点
├── payload-v2/src/features/engine/retrievers/
│   ├── index.ts                            barrel export
│   ├── types.ts                            BboxEntry 等类型
│   └── components/
│       ├── PdfViewer.tsx                   PDF 阅读器 + 引用高亮
│       └── BboxOverlay.tsx                 MinerU bbox 叠加层
└── payload-v2/src/app/(frontend)/engine/retrievers/
    └── page.tsx                            /engine/retrievers 路由
```
