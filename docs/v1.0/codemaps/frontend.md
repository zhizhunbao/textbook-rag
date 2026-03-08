# Textbook RAG — 前端代码地图 (Frontend Codemap)

## 文档信息

- 版本: 1.0
- 角色: Senior Frontend Engineer
- 日期: 2026-03-07
- 输入: `docs/architecture/system-architecture.md`, `docs/sprints/sprint-plan.md`, `docs/codemaps/backend.md`

---

## 1. 技术栈

| 层 | 选型 |
|---|------|
| 框架 | React 18 |
| 语言 | TypeScript 5 |
| 构建 | Vite 5 |
| 样式 | Tailwind CSS 3 |
| PDF 渲染 | react-pdf (pdf.js) |
| 状态 | React Context + useReducer |
| HTTP | fetch API |

---

## 2. 目录结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── public/
└── src/
    ├── main.tsx                  ← React 入口
    ├── App.tsx                   ← 双栏布局 + AppContext provider
    ├── index.css                 ← Tailwind directives
    ├── vite-env.d.ts
    ├── api/
    │   └── client.ts            ← fetch 封装: queryTextbook, fetchBooks, fetchBook
    ├── context/
    │   └── AppContext.tsx        ← 全局状态: currentBookId, currentPage, selectedSource
    ├── types/
    │   └── api.ts               ← 响应类型: BookSummary, QueryResponse, SourceInfo
    ├── components/
    │   └── Loading.tsx           ← 共享 loading spinner
    └── features/
        ├── chat/
        │   ├── ChatPanel.tsx     ← 问题输入 + 消息列表
        │   └── MessageBubble.tsx ← 单条消息（问/答）
        ├── pdf-viewer/
        │   ├── PdfViewer.tsx     ← PDF 渲染 + 页码导航
        │   └── BboxOverlay.tsx   ← bbox 高亮覆盖层
        ├── source/
        │   └── SourceCard.tsx    ← 可点击来源索引卡片
        └── book-selector/
            └── BookSelector.tsx  ← 书籍下拉选择
```

---

## 3. Story → 文件映射

| Story | 文件 |
|-------|------|
| INFRA-002 | package.json, vite.config.ts, tailwind.config.js, index.html, main.tsx |
| FE-001 App Shell | App.tsx, context/AppContext.tsx, index.css |
| FE-002 API Client | api/client.ts, types/api.ts |
| FE-003 ChatPanel | features/chat/ChatPanel.tsx |
| FE-004 MessageBubble | features/chat/MessageBubble.tsx |
| FE-005 SourceCard | features/source/SourceCard.tsx |
| FE-006 PdfViewer | features/pdf-viewer/PdfViewer.tsx |
| FE-007 PDF 跳转 | context/AppContext.tsx (selectedSource 触发跳转) |
| FE-008 BboxOverlay | features/pdf-viewer/BboxOverlay.tsx |
| FE-009 状态反馈 | components/Loading.tsx, ChatPanel.tsx (error/empty) |
| FE-010 BookSelector | features/book-selector/BookSelector.tsx |

---

## 4. 状态模型

```typescript
interface AppState {
  currentBookId: number | null;
  currentPage: number;
  selectedSource: SourceInfo | null;
  books: BookSummary[];
}
```

通过 `AppContext` 提供, `useReducer` 管理状态转换:
- `SET_BOOK` → 切换当前书籍, 重置页码
- `SET_PAGE` → 跳转到指定页
- `SELECT_SOURCE` → 设置选中来源 → 触发 PDF 跳转 + bbox 高亮
- `SET_BOOKS` → 加载书籍列表

---

## 5. 数据流

### 5.1 问答流程

```
ChatPanel (question input)
  → api/client.ts → POST /api/v1/query
  → ChatPanel 展示 answer + sources
  → 用户点击 SourceCard
  → dispatch SELECT_SOURCE
  → PdfViewer 跳转到 source.page_number
  → BboxOverlay 渲染 source.bbox
```

### 5.2 书籍浏览

```
App mount → fetchBooks() → dispatch SET_BOOKS
BookSelector → dispatch SET_BOOK
  → PdfViewer 加载 /api/v1/books/{id}/pdf
```

---

## 6. 后端 API 契约

| 前端调用 | 后端端点 | 响应类型 |
|---------|---------|---------|
| `fetchBooks()` | GET /api/v1/books | BookSummary[] |
| `fetchBook(id)` | GET /api/v1/books/{id} | BookDetail |
| `getPdfUrl(id)` | GET /api/v1/books/{id}/pdf | PDF binary stream |
| `queryTextbook(q, filters, topK)` | POST /api/v1/query | QueryResponse |

---

## 7. 教材依据

| 决策 | 教材 |
|------|------|
| 模块化组件结构 | Flanagan, *JS Definitive Guide* Ch10 — 模块封装相关功能 |
| TypeScript 类型安全 | Basarat, *TypeScript Deep Dive* — 接口设计 |
| 异步数据加载 | Simpson, *YDKJS: Async & Performance* — Promise 模式 |
| 双栏布局可用性 | Krug, *Don't Make Me Think* — 导航一致性 |
| Feature-based 组织 | React 社区最佳实践 — 按功能区域分组 |
