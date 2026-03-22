# Textbook RAG v2.0 — Frontend Codemap (Payload + Next.js)

> **版本**: 2.0 | **日期**: 2026-03-22
> **技术栈**: Payload CMS 3.x + Next.js 15 + PostgreSQL

---

## 1. 目录结构

```
payload/                          # Payload CMS + Next.js 一体化项目
├── package.json
├── tsconfig.json
├── next.config.ts
├── .env.example
│
└── src/
    ├── payload.config.ts          # Payload 总配置 (DB, collections, plugins)
    │
    ├── collections/               # Payload Collections (自动生成 REST + GraphQL)
    │   ├── Books.ts               # P1-02
    │   ├── Chapters.ts            # P1-03
    │   ├── Chunks.ts              # P1-04
    │   ├── Users.ts               # P2-01
    │   ├── PipelineTasks.ts       # P1-05
    │   └── QueryLogs.ts           # P1-06
    │
    ├── hooks/                     # Payload Hooks
    │   └── books/
    │       └── afterChange.ts     # P3-01: trigger Engine ingest
    │
    ├── access/                    # Access Control
    │   ├── isAdmin.ts             # P2-02
    │   ├── isEditorOrAdmin.ts     # P2-02
    │   └── isOwnerOrAdmin.ts      # P2-02
    │
    └── app/                       # Next.js App Router
        ├── layout.tsx             # Root layout
        ├── page.tsx               # Home → redirect to /ask
        │
        ├── (frontend)/            # User-facing pages
        │   ├── ask/
        │   │   └── page.tsx       # P6-01: Ask (PDF + Chat 双栏)
        │   ├── library/
        │   │   └── page.tsx       # P6-04: Book selector
        │   └── reports/
        │       └── page.tsx       # P6-08: EcDev reports
        │
        ├── (admin)/               # Payload Admin (自动挂载)
        │   └── admin/[[...segments]]/page.tsx
        │
        └── components/            # 共享 React 组件
            ├── ChatPanel.tsx      # P6-02
            ├── PdfViewer.tsx      # P6-03
            ├── BookSelector.tsx   # P6-04
            ├── TracePanel.tsx     # P6-05
            ├── RetrievalConfig.tsx # P6-06
            ├── GenerationConfig.tsx # P6-06
            └── ResizeHandle.tsx   # P6-07
```

---

## 2. Story → 文件映射

| Story | 目标文件 | 操作 |
|-------|---------|------|
| P1-01 | payload/ 全部骨架 | create |
| P1-02 | src/collections/Books.ts | create |
| P1-03 | src/collections/Chapters.ts | create |
| P1-04 | src/collections/Chunks.ts | create |
| P1-05 | src/collections/PipelineTasks.ts | create |
| P1-06 | src/collections/QueryLogs.ts | create |
| P2-01 | src/collections/Users.ts | create |
| P2-02 | src/access/*.ts | create |
| P2-03 | Payload auth 内置，无需额外页面 | config |
| P3-01 | src/hooks/books/afterChange.ts | create |
| P3-02 | PipelineTasks 轮询 | via API |
| P6-01 | src/app/(frontend)/ask/page.tsx | create |
| P6-02 | src/app/components/ChatPanel.tsx | create |
| P6-03 | src/app/components/PdfViewer.tsx | create |
| P6-04 | src/app/components/BookSelector.tsx | create |
| P6-05 | src/app/components/TracePanel.tsx | create |
| P6-06 | src/app/components/*Config.tsx | create |
| P6-07 | src/app/components/ResizeHandle.tsx | create |

---

## 3. 关键数据流

### 3.1 入库流 (Payload Hook → Engine)
```
Admin 上传 PDF
  → Books.afterChange hook (file 字段 + status=pending)
  → POST /engine/ingest { book_id, file_url, category, task_id }
  → Engine IngestPipeline (background)
  → PATCH /api/pipeline-tasks/:id (progress updates)
  → PATCH /api/books/:id { status: "indexed" }
```

### 3.2 查询流 (Next.js → Engine)
```
User 输入问题
  → ChatPanel → Server Action / Route Handler
  → POST /engine/query { question, filters, config }
  → Engine RAGCore → answer + sources + trace
  → ChatPanel 显示答案 + TracePanel 展开证据链
```

---

## 4. 环境变量

| 变量 | 用途 |
|------|------|
| DATABASE_URI | PostgreSQL 连接 (data/postgres/) |
| PAYLOAD_SECRET | JWT 签名密钥 |
| ENGINE_URL | Engine FastAPI 地址 |
| NEXT_PUBLIC_ENGINE_URL | 浏览器端访问 Engine |
