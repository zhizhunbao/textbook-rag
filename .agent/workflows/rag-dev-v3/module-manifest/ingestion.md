# `ingestion` — 数据摄取

```
Layout
流程面板
任务列表

UI
管线步骤
进度条形
状态徽章

UX
实时轮询
批量操作
错误重试

Func
管线编排
分块切片
向量入库
增量更新

Noun
Pipeline
Task
Chunk
Vector
Batch
Progress
Status
```

```
ingestion
├── engine_v2/ingestion/
│   ├── __init__.py                         re-export 公共 API
│   ├── pipeline.py                         LlamaIndex IngestionPipeline
│   └── transformations.py                  分块转换器
├── engine_v2/api/routes/
│   └── ingest.py                           触发 pipeline 端点
├── payload-v2/src/collections/
│   ├── IngestTasks.ts                      摄取任务 Collection
│   └── Chunks.ts                           分块 Collection
├── payload-v2/src/features/engine/ingestion/
│   ├── index.ts                            barrel export
│   ├── types.ts                            TaskType · PipelinePreview 等类型
│   ├── api.ts                              Pipeline 触发 + 预览 API
│   └── components/
│       ├── PipelineDashboard.tsx            三栏管线面板 (书本树 + 步骤 + 详情)
│       └── PipelineActions.tsx             批量操作按钮组
└── payload-v2/src/app/(frontend)/engine/ingestion/
    └── page.tsx                            /engine/ingestion 路由薄壳
```
