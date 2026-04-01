---
description: textbook-rag v2 核心开发规则 — 模块命名、前端架构、API 分工、数据库
---

# 🔑 v2 核心开发规则

## 1. 模块命名: 跟随 LlamaIndex 命名空间

**核心原则: engine_v2 子包名必须对齐 `llama_index.core.*` 模块名。**

```
✅ 正确:
  engine_v2/readers/         → 对齐 llama_index.core.readers
  engine_v2/retrievers/      → 对齐 llama_index.core.retrievers
  engine_v2/response_synthesizers/ → 对齐 llama_index.core.response_synthesizers

❌ 错误:
  engine_v2/rag/             → v1 风格，不对齐
  engine_v2/search/          → 自创名，不对齐
  engine_v2/generate/        → 自创名，不对齐
```

新增子包时：
1. 先在 `.github/references/llama_index/llama-index-core/llama_index/core/` 查找对应模块
2. 使用相同目录名
3. 内部类继承或使用 LlamaIndex 基类

## 2. 前端架构: features/ 三层对齐

**核心原则: payload-v2 的 `features/engine/` 子目录与 engine_v2 子包 1:1 映射。**

```
✅ 正确:
  features/engine/retrievers/  → 对应 engine_v2/retrievers/
  features/engine/evaluation/  → 对应 engine_v2/evaluation/
  每个子目录有: index.ts (barrel), types.ts, api.ts, components/

❌ 错误:
  features/dashboard/search/   → 不对齐 engine_v2 命名
  把所有 engine API 调用放在一个 api.ts 里
```

## 3. 前端 page.tsx 薄壳规则 (与 v1 相同)

```tsx
// app/(frontend)/engine/evaluation/page.tsx  — 薄壳
'use client'
import { EvaluationPage } from '@/features/engine/evaluation'
export default function Page() {
  return <EvaluationPage />
}
```

## 4. 后端 API: Payload vs Engine v2 分工

| 功能类型 | 实现位置 | 原因 |
|---------|---------|------|
| CRUD (Books/Chunks/Users/...) | Payload REST API (`/api/books`) | Payload 3 自动生成，带认证 + 权限 |
| 自定义聚合/同步 | Payload endpoints (`collections/endpoints/`) | 可用 Payload Local API |
| RAG 查询 | Engine v2 (`POST /engine/query`) | 需要 LlamaIndex QueryEngine |
| 检索调试 | Engine v2 (`POST /engine/retrievers/search`) | 直接返回 NodeWithScore |
| 数据摄入 | Engine v2 (`POST /engine/ingest`) | IngestionPipeline + ChromaDB |
| 评估 | Engine v2 (`POST /engine/evaluation/*`) | LlamaIndex Evaluators |
| 问题生成 | Engine v2 (`POST /engine/questions/generate`) | Settings.llm + ChromaDB |
| LLM 管理 | Engine v2 (`GET /engine/llms/*`) | 查询 LLM 配置 |

## 5. 数据库: PostgreSQL (Payload v2)

v2 使用 PostgreSQL 替代 SQLite:
```
DATABASE_URI=postgresql://payload:payload@127.0.0.1:5432/payload
```

- Payload v2 的 `payload.config.ts` 使用 `@payloadcms/db-postgres`
- 本地开发需要运行 PostgreSQL (Docker 或本机安装)
- Engine v2 **不使用** SQLite，数据完全在 ChromaDB + Payload CMS 中

## 6. UI 组件规范

### Tailwind CSS v4
payload-v2 使用 TailwindCSS v4 (通过 `@tailwindcss/postcss`):
- 使用语义 token: `bg-card`, `bg-sidebar`, `text-foreground`, `text-muted-foreground`
- 不使用 hardcoded 颜色: ~~`bg-gray-800`~~ → `bg-card`
- 暗色主题通过 `globals.css` 中的 CSS 变量自动支持

### shadcn/ui 组件
共用组件在 `features/shared/components/ui/`:
- Tooltip, Dialog, DropdownMenu, Tabs, Progress, etc.
- 基于 Radix UI primitives + CVA

### 侧边栏布局
GPT 风格侧边栏 `features/layout/AppSidebar.tsx`:
- 聊天历史列表 (Today / Yesterday / This Week 分组)
- 可折叠 (collapsed state)
- 底部: Library + Admin nav + Settings

## 7. i18n: 新增文案必须更新

所有用户可见文字在 `features/shared/i18n/` 统一管理。
新增导航/功能时必须同步更新 messages 文件。

## 8. 环境变量

v1 和 v2 共用根目录 `.env` 文件。关键差异:

| 变量 | v1 用途 | v2 用途 |
|------|---------|---------|
| `ENGINE_URL` | Payload v1 调 Engine v1 (port 8000) | — |
| `NEXT_PUBLIC_ENGINE_URL` | — | Payload v2 调 Engine v2 (port **8001**) |
| `DATABASE_URI` | — | PostgreSQL 连接串 |
| `PAYLOAD_URL` | v1 CMS URL (port 3000) | v2 也从此读取 |

## 9. Package 管理

- **Python**: `pyproject.toml` + `uv` (单一 venv，engine/ 和 engine_v2/ 共用)
- **Node.js**: `payload-v2/package.json` 独立于 `payload/package.json`
- Engine v2 的 LlamaIndex 依赖:
  ```
  llama-index-core >= 0.12.42
  llama-index-embeddings-huggingface
  llama-index-llms-ollama
  llama-index-llms-azure-openai
  llama-index-vector-stores-chroma
  llama-index-retrievers-bm25
  ```
