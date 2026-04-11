# `llms` — 模型管理

```
Layout
模型列表
配置详情

UI
模型卡片
参数表单
状态指示

UX
一键切换
参数微调
连通测试

Func
多厂适配
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
```

```
llms
├── engine_v2/llms/
│   ├── __init__.py                         re-export 公共 API
│   └── resolver.py                         多厂 LLM 解析 (Ollama / Azure)
├── engine_v2/api/routes/
│   └── llms.py                             模型列表 + 状态端点
├── payload-v2/src/collections/
│   └── Llms.ts                             LLM 配置 Collection
├── payload-v2/src/features/engine/llms/
│   ├── index.ts                            barrel export
│   ├── types.ts                            ModelConfig 等类型
│   ├── api.ts                              模型 CRUD API
│   ├── useModels.ts                        模型管理 hook
│   └── ModelContext.tsx                    当前模型 Context
└── payload-v2/src/app/(frontend)/engine/llms/
    └── page.tsx                            /engine/llms 路由
```
