# `seed` — 数据播种

```
Layout
分类侧栏
操作面板

UI
模块卡片
执行按钮
日志输出

UX
分类导航
一键执行
进度反馈

Func
用户预置
模型预置
提示预置
引擎同步

Noun
Seed
Preset
Sync
Category
Log
Module
```

```
seed
├── payload-v2/src/features/seed/
│   └── SeedPage.tsx                        播种控制面板
├── payload-v2/src/seed/
│   ├── index.ts                            入口 + 执行编排
│   ├── types.ts                            Seed 类型定义
│   ├── users.ts                            预置用户数据
│   ├── llms.ts                             预置 LLM 模型配置
│   ├── prompt-modes.ts                     预置 Prompt 模式
│   └── prompt-templates.ts                 预置 Prompt 模板
├── payload-v2/src/collections/endpoints/
│   ├── index.ts                            barrel export
│   ├── seed.ts                             seed 端点
│   └── sync-engine.ts                      引擎同步端点
└── payload-v2/src/app/(frontend)/seed/
    └── page.tsx                            /seed 路由薄壳
```
