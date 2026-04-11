# `query_engine` — 查询引擎

```
Layout
调试控制台

UI
查询输入
管线流程
结果展示

UX
端到端试
管线可视
耗时统计

Func
全链调试
检索合成
上下文管
结果封装

Noun
QueryEngine
Query
Pipeline
Trace
Result
Latency
Debug
```

```
query_engine
├── engine_v2/query_engine/
│   ├── __init__.py                         re-export 公共 API
│   └── citation.py                         带引用的全链查询
├── engine_v2/api/routes/
│   └── query.py                            查询端点
├── payload-v2/src/collections/
│   └── Queries.ts                          查询记录 Collection
├── payload-v2/src/features/engine/query_engine/
│   ├── index.ts                            barrel export
│   ├── types.ts                            QueryTrace 等类型
│   └── api.ts                              查询 + TOC + PDF URL API
└── payload-v2/src/app/(frontend)/engine/query_engine/
    └── page.tsx                            /engine/query_engine 路由 (占位)
```
