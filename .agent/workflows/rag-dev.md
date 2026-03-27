---
description: textbook-rag 项目开发工作流 — 新增功能、修改组件、调试运行。使用 /rag-dev 启动。
---

# Textbook RAG 开发工作流

适用于 textbook-rag 项目的日常开发操作，覆盖前端(Payload/Next.js)、后端(Engine/FastAPI)、数据(SQLite/ChromaDB)三层。

// turbo-all

---

## 🏗️ 项目结构速查

```
textbook-rag/
├── payload/              # 前端 + CMS (Payload + Next.js)
│   ├── src/
│   │   ├── app/
│   │   │   ├── (frontend)/
│   │   │   │   ├── (app)/        # 用户页面 (library, chat, dashboard/*)
│   │   │   │   │   └── {page}/page.tsx  ← 薄壳，import features/ 组件
│   │   │   │   ├── api/           # 自定义 Next.js API routes
│   │   │   │   └── layout.tsx
│   │   │   └── (payload)/         # Payload Admin 自动生成
│   │   ├── collections/           # Payload CMS collections (Books, Chunks, etc.)
│   │   └── features/              # ⭐ 核心前端代码，按功能模块组织
│   │       ├── chat/              # 聊天功能
│   │       ├── library/           # 资料库（BookCard, StatusBadge 等）
│   │       ├── pipeline/          # 流水线操作
│   │       ├── models/            # 模型管理
│   │       ├── shared/            # 公共组件 (SidebarLayout, i18n, utils)
│   │       └── layout/            # 布局 (AppSidebar, AppLayout)
│   └── package.json
├── engine/                # 后端引擎 (FastAPI)
│   ├── api/routes/        # API 路由 (books, query, ingest, sync, etc.)
│   ├── rag/               # RAG 核心 (retrieval, generation, config)
│   ├── ingest/            # 数据摄入 (pipeline, chunk_builder)
│   ├── index/             # 索引 (vector_builder, fts5_builder)
│   └── config.py          # 全局配置
├── scripts/               # 独立脚本 (rebuild_db, sync_to_payload, etc.)
├── data/                  # 数据存储
│   ├── raw_pdfs/          # 原始 PDF (textbooks/, ecdev/, real_estate/)
│   ├── mineru_output/     # MinerU 解析输出
│   └── textbook_rag.sqlite3  # Engine SQLite 数据库
└── .env                   # 环境变量
```

---

## 🔑 核心开发规则

### 1. 前端架构: features/ 模块化

**核心原则: `app/` 目录的 page.tsx 只做薄壳，所有逻辑在 `features/` 下。**

```
✅ 正确做法:
  app/(frontend)/(app)/library/page.tsx     → import LibraryPage from '@/features/library/LibraryPage'
  app/(frontend)/(app)/dashboard/pipeline/page.tsx → import PipelineDashboard from '@/features/pipeline/PipelineDashboard'

❌ 错误做法:
  把 500 行组件直接写在 page.tsx 里
```

### 2. UI 组件规范: 通用布局与模式

为了保持全站 UI 体验一致（如暗黑模式、交互方式），开发新页面时必须：

1. **页面布局**: 使用 `features/shared/components/SidebarLayout.tsx`，它内置了：
   - 通用的响应式带侧边栏布局
   - 自动内置可拖拽边框 (`ResizeHandle`)
   - 树形/列表/卡片等标准化布局属性
2. **面板拖拽**: 需要左右拖拽面板时，复用 `features/shared/ResizeHandle.tsx`。
   - 不要写死灰/蓝的硬编码颜色，该组件已使用 `bg-border` / `bg-primary` 做了主题适配。
3. **样式与类名**: 遵循 TailwindCSS 标准变量（如 `bg-card`, `bg-muted`, `text-muted-foreground` 等），避免 hardcoded 颜色（如 `bg-gray-100`）。

### 3. 后端 API: Payload vs Engine 分工

| 功能类型 | 实现位置 | 原因 |
|---------|---------|------|
| CRUD 操作 (Books/Chunks/Tasks) | Payload REST API (`/api/books`, `/api/pipeline-tasks`) | Payload 自动生成，带认证 |
| 自定义聚合/同步 | Payload Next.js Route (`app/(frontend)/api/`) | 可用 Payload Local API，无需认证 |
| RAG 查询/检索 | Engine FastAPI (`/engine/query`) | 需要 SQLite + ChromaDB 直接访问 |
| PDF 服务/TOC | Engine FastAPI (`/engine/books/`) | 文件系统访问 |
| 数据摄入 Pipeline | Engine FastAPI (`/engine/ingest`) | 重计算任务 |

### 4. i18n: 新增导航/文案必须更新

所有用户可见文字在 `features/shared/i18n/messages.ts` 统一管理:
1. 在 `Messages` interface 添加 key
2. 在 `en` 对象添加英文
3. 在 `zh` 对象添加中文

### 5. 数据一致性: 三层同步

```
Engine SQLite ←sync_to_payload.py→ Payload CMS (PostgreSQL)
     ↑                                    ↓
  rebuild_db.py                    Frontend UI
  (MinerU 输出)
```

修改数据分类/字段时，检查并更新:
- `scripts/rebuild_db.py` (Engine SQLite schema)
- `scripts/sync_to_payload.py` (同步脚本 + registry)
- `payload/src/collections/Books.ts` (CMS schema)
- `app/(frontend)/api/sync-engine/route.ts` (Payload API sync)

---

## 📋 开发流程

### 新增前端功能

1. **创建 feature 模块** (如不存在):
   ```
   payload/src/features/{feature_name}/
   ├── index.ts              # barrel export
   ├── types.ts              # 类型定义
   ├── api.ts                # API 调用
   └── {FeatureName}Page.tsx # 主组件
   ```

2. **创建路由页面** (薄壳):
   ```tsx
   // app/(frontend)/(app)/dashboard/{feature}/page.tsx
   'use client'
   import FeaturePage from '@/features/{feature}/FeaturePage'
   export default function Page() {
     return <FeaturePage />
   }
   ```

3. **添加导航** (如需要):
   - `features/layout/AppSidebar.tsx` — 添加 navLink
   - `features/shared/i18n/messages.ts` — 添加 i18n key

4. **更新 barrel export**:
   ```ts
   // features/{feature}/index.ts
   export * from './types'
   export * from './api'
   export { default as FeaturePage } from './FeaturePage'
   ```

### 新增后端 API (Payload 侧)

```
payload/src/app/(frontend)/api/{endpoint}/route.ts
```

```ts
import { NextResponse } from 'next/server'
import { getPayload } from 'payload'
import config from '@payload-config'

export async function GET(req: Request) {
  const payload = await getPayload({ config })
  // 使用 payload.find / payload.create / payload.update
  const data = await payload.find({ collection: 'books', limit: 10 })
  return NextResponse.json(data)
}
```

### 新增后端 API (Engine 侧)

```python
# engine/api/routes/{feature}.py
from fastapi import APIRouter
router = APIRouter(tags=["{feature}"])

@router.get("/{feature}/endpoint")
def my_endpoint():
    ...
```

注册路由: `engine/api/routes/__init__.py` 或 `engine/api/app.py`

### 修改数据字段

1. 修改 Payload collection: `payload/src/collections/Books.ts`
2. 修改 Engine schema: `scripts/rebuild_db.py` (SCHEMA 常量)
3. 修改同步脚本: `scripts/sync_to_payload.py` (detect_category, registry)
4. 修改 Payload sync route: `app/(frontend)/api/sync-engine/route.ts`
5. 运行: `--fix-subcategory` 或 `--fix-pipeline` 回填现有数据

---

## 🚀 启动 / 运行

### 启动 Engine (FastAPI)

```powershell
# cwd: textbook-rag
uv run uvicorn engine.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 启动 Payload (Next.js)

```powershell
# cwd: textbook-rag/payload
npm run dev
```

### 环境检查

```powershell
# Engine health
Invoke-WebRequest -Uri 'http://localhost:8000/engine/health' -UseBasicParsing | Select-Object StatusCode

# Payload health
Invoke-WebRequest -Uri 'http://localhost:3000/api/books?limit=1' -UseBasicParsing | Select-Object StatusCode
```

### 数据重建

```powershell
# 重建 Engine SQLite (全量)
uv run python scripts/rebuild_db.py

# 重建单本书
uv run python scripts/rebuild_db.py --book ramalho_fluent_python

# 同步到 Payload CMS
uv run python scripts/sync_to_payload.py

# 回填子分类
uv run python scripts/sync_to_payload.py --fix-subcategory

# 重建向量
uv run python scripts/build_vectors.py
```

---

## 🔍 调试技巧

### 前端编译错误

```powershell
# cwd: textbook-rag/payload
npx tsc --noEmit                # 类型检查
npm run build                    # 完整构建
```

### Python 类型检查

```powershell
# cwd: textbook-rag
uv run python -m pyright engine/
```

### 查看 Payload 数据

```powershell
# 列出所有 books
Invoke-WebRequest -Uri 'http://localhost:3000/api/books?limit=100' -UseBasicParsing | ConvertFrom-Json | ConvertTo-Json -Depth 5

# 查看特定 book
Invoke-WebRequest -Uri 'http://localhost:3000/api/books?where[engineBookId][equals]=ramalho_fluent_python' -UseBasicParsing
```

### 查看 Engine SQLite

```powershell
uv run python -c "import sqlite3; conn = sqlite3.connect('data/textbook_rag.sqlite3'); print([r[0] for r in conn.execute('SELECT book_id FROM books').fetchall()])"
```

---

## 📦 Git 提交规范

```
feat: add pipeline dashboard with book selector
fix: move Ready badge to bottom-right of BookCard
refactor: extract PipelineDashboard to features/pipeline
chore: add subcategory registry for textbooks
```

提交前检查:
1. `npx tsc --noEmit` (payload/ 目录)
2. 确认 i18n messages 完整
3. page.tsx 只是薄壳
4. 新组件已加入 barrel export
