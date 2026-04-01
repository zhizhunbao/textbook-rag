---
description: textbook-rag v2 开发流程模板 — 新增 Engine 模块、Payload Collection、前端功能
---

# 📋 v2 开发流程

## 新增 Engine v2 子模块 (对齐 LlamaIndex)

### 1. 确认 LlamaIndex 对应模块

```powershell
# 查找 llama_index.core 中对应目录
ls .github\references\llama_index\llama-index-core\llama_index\core\{module_name}\
```

### 2. 创建 engine_v2 子包

```
engine_v2/{module_name}/
├── __init__.py         # barrel export + docstring
└── {implementation}.py # 继承/使用 LlamaIndex 基类
```

**`__init__.py` 模板:**
```python
"""Module description — aligns with llama_index.core.{module_name}."""

from engine_v2.{module_name}.{impl} import MyClass  # noqa: F401
```

**实现文件模板:**
```python
"""Implementation — aligns with llama_index.core.{module_name}.

Reference: .github/references/llama_index/llama-index-core/
           llama_index/core/{module_name}/
"""

from __future__ import annotations

import logging
from llama_index.core.{module_name} import BaseClass  # 继承或使用

logger = logging.getLogger(__name__)

# ... implementation
```

### 3. 注册 API 路由 (如需要)

```python
# engine_v2/api/routes/{module_name}.py
from fastapi import APIRouter
router = APIRouter(prefix="/{module_name}", tags=["{module_name}"])

@router.post("/endpoint")
async def my_endpoint():
    ...
```

在 `engine_v2/api/app.py` 注册:
```python
from engine_v2.api.routes import {module_name}
app.include_router({module_name}.router, prefix="/engine")
```

### 4. 创建前端对应模块

```
payload-v2/src/features/engine/{module_name}/
├── index.ts        # barrel export
├── types.ts        # TypeScript 类型
├── api.ts          # API 调用 (fetch engine v2)
└── components/     # React 组件
    └── {ModuleName}Page.tsx
```

### 5. 创建前端路由页面

```tsx
// payload-v2/src/app/(frontend)/engine/{module_name}/page.tsx
'use client'
import { ModuleNamePage } from '@/features/engine/{module_name}'
export default function Page() {
  return <ModuleNamePage />
}
```

### 6. 更新 barrel export

```ts
// payload-v2/src/features/engine/index.ts
export * from './{module_name}'
```

### 7. 添加侧边栏导航 (如需要)

在 `features/layout/AppSidebar.tsx` 的 `adminLinks` 数组添加:
```ts
{ titleKey: 'navModuleName', icon: SomeIcon, href: '/engine/{module_name}' },
```

同步更新 i18n messages。

---

## 新增 Payload Collection

### 1. 创建 Collection 定义

```ts
// payload-v2/src/collections/{CollectionName}.ts
import type { CollectionConfig } from 'payload'

export const CollectionName: CollectionConfig = {
  slug: 'collection-name',
  admin: {
    useAsTitle: 'title',
  },
  fields: [
    { name: 'title', type: 'text', required: true },
    // ...
  ],
}
```

### 2. 注册到 payload.config.ts

```ts
import { CollectionName } from './collections/CollectionName'
// 添加到 collections 数组
collections: [..., CollectionName],
```

### 3. 生成类型

```powershell
cd payload-v2
npm run generate:types
```

---

## 新增前端聊天功能

### 1. 修改 ChatPage / 添加 panel 组件

```
payload-v2/src/features/chat/
├── ChatPage.tsx           # 主聊天页面
├── types.ts               # 聊天类型
├── history/               # 聊天历史上下文
│   ├── ChatHistoryContext.tsx
│   └── useChatHistory.ts
└── panel/                 # 聊天面板子组件
    └── {NewPanel}.tsx
```

### 2. API 调用 Engine v2

```ts
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://127.0.0.1:8001'

export async function queryEngine(question: string) {
  const res = await fetch(`${ENGINE_URL}/engine/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return res.json()
}
```

注意: v2 的 Engine URL 走 `NEXT_PUBLIC_ENGINE_URL` (port 8001)，不是 v1 的 `ENGINE_URL` (port 8000)。

---

## 修改数据流 (v2)

v2 的数据流比 v1 简化:

```
                 ┌─ Payload CMS (PostgreSQL)
                 │   Collections: Books, Chunks, ...
                 │   自动 CRUD API
Ingest Pipeline ─┤
                 │   Engine v2 (ChromaDB)
                 └─  向量 + BM25 检索
```

修改数据字段时:
1. 修改 Payload Collection: `payload-v2/src/collections/Books.ts`
2. 修改 Engine v2 schema: `engine_v2/schema.py` (如涉及)
3. 修改 MinerU reader metadata: `engine_v2/readers/mineru_reader.py`
4. 修改 ingestion pipeline: `engine_v2/ingestion/pipeline.py` (Payload 推送)
5. 运行 `npm run generate:types` 重新生成 TypeScript 类型
