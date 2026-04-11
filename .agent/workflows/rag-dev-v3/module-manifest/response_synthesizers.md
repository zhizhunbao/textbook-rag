# `response_synthesizers` — 回答合成

```
Layout
配置表单
输出预览

UI
模板编辑
参数调节
结果展示

UX
实时预览
模板切换
质量对比

Func
提示拼装
流式生成
来源注入
格式标准

Noun
Synthesizer
Prompt
Template
Response
Citation
Format
Stream
```

```
response_synthesizers
├── engine_v2/response_synthesizers/
│   ├── __init__.py                         re-export 公共 API
│   └── citation.py                         带引用的回答合成
├── payload-v2/src/collections/
│   └── Prompts.ts                          Prompt 模式 Collection
├── payload-v2/src/features/engine/response_synthesizers/
│   ├── index.ts                            barrel export
│   ├── types.ts                            PromptMode · PromptModeUpdatePayload 等类型
│   ├── api.ts                              Prompt 模式 CRUD API (Payload CMS)
│   ├── usePromptModes.ts                   Prompt 模式 hook (只读)
│   └── components/
│       └── PromptEditorPage.tsx            Prompt 编辑 + 实时预览页面
└── payload-v2/src/app/(frontend)/engine/response_synthesizers/
    └── page.tsx                            /engine/response_synthesizers 路由薄壳
```
