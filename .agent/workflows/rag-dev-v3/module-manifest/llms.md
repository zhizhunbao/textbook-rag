# `llms` — 模型管理

```
Layout
模型列表
模型库浏览 (Admin)
配置详情

UI
模型卡片
目录卡片 (CatalogCard)
拉取进度条 (PullProgress)
参数表单
状态指示

UX
一键切换
一键拉取+注册
参数微调
连通测试

Func
多厂适配
模型目录 (Catalog)
SSE 拉取流 (Pull)
参数管理
令牌统计
故障降级

Noun
Llm
Model
Provider
Param
Token
Fallback
Endpoint
Catalog
Pull
Progress
Library
```

```
llms
├── engine_v2/llms/
│   ├── __init__.py                         re-export 公共 API
│   ├── resolver.py                         多厂 LLM 解析 (Ollama / Azure)
│   └── catalog.py                          精选模型目录数据 (Sprint MH)
├── engine_v2/api/routes/
│   └── llms.py                             模型列表 + 状态 + 库搜索 + 拉取端点
├── payload-v2/src/collections/
│   └── Llms.ts                             LLM 配置 Collection
├── payload-v2/src/features/engine/llms/
│   ├── index.ts                            barrel export
│   ├── types.ts                            ModelConfig + CatalogModel + PullProgress
│   ├── api.ts                              模型 CRUD + searchLibrary + pullModel
│   ├── useModels.ts                        模型管理 hook + catalog + pullAndRegister
│   └── ModelContext.tsx                    当前模型 Context
└── payload-v2/src/app/(frontend)/engine/llms/
    └── page.tsx                            /engine/llms 路由 (含 Library Tab)
```
