# `report` — 报告生成

```
Layout
报告列表侧栏
报告内容主区

UI
会话选择器
报告卡片
Markdown 预览
生成进度条

UX
选择会话生成
实时生成状态
报告内容渲染

Func
LLM 报告生成
会话数据拉取
报告 CRUD
PDF 导出(未来)

Noun
Report
Session
Content
Summary
Finding
Methodology
```

```
report
├── engine_v2/report/
│   ├── __init__.py                         re-export 公共 API
│   ├── generator.py                        LLM 报告生成器 (从 ChatMessages 生成 Markdown 报告)
│   └── export.py                           报告导出 (PDF 等)
├── engine_v2/api/routes/
│   └── report.py                           报告端点 (generate / list / detail)
├── payload-v2/src/collections/
│   └── Reports.ts                          报告 Collection (user/title/content/sessionId/status)
├── payload-v2/src/features/report/
│   ├── index.ts                            barrel export
│   └── ReportPage.tsx                      /reports 路由页面 (侧栏列表 + Markdown 预览)
└── payload-v2/src/app/(frontend)/reports/
    └── page.tsx                            /reports 路由
```
