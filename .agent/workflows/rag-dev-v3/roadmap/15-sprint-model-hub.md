# Sprint Model Hub — Ollama 模型库浏览 + 一键拉取

> **模块**: `llms` (Engine 子模块)
> **权限**: Admin only — 管理员功能，非用户功能
> **路由**: `/engine/llms`（扩展现有页面，增加 Library 侧栏 Tab）
> **前置**: Sprint Demo ✅, Sprint 2 llms 基础 ✅

---

## 目标

让管理员在现有 `/engine/llms` 页面中：
1. 浏览精选模型目录（含优势、更新时间、推荐用途）
2. 一键 Pull 模型（含 SSE 进度条）
3. Pull 完成后自动注册到 CMS
4. 统一管理已注册/已安装/可用模型的全生命周期

---

## Stories

### 后端 (Engine Python)

| ID | Story | 文件 | 工时 | 状态 |
|----|-------|------|------|------|
| MH-01 | 创建精选模型目录数据 (`catalog.py`) | `engine_v2/llms/catalog.py` | 1h | ❌ |
| MH-02 | 添加 `/engine/llms/models/discover` 端点 — 列出本地已安装模型详情 | `engine_v2/api/routes/llms.py` | 0.5h | ❌ |
| MH-03 | 添加 `/engine/llms/library/search` 端点 — 搜索/过滤精选目录 | `engine_v2/api/routes/llms.py` | 1h | ❌ |
| MH-04 | 添加 `POST /engine/llms/models/pull` 端点 — SSE 流式拉取模型 | `engine_v2/api/routes/llms.py` | 1.5h | ❌ |
| MH-05 | 添加 `DELETE /engine/llms/models/{name}` 端点 — 从 Ollama 删除模型 | `engine_v2/api/routes/llms.py` | 0.5h | ❌ |

### 前端 (React/Payload)

| ID | Story | 文件 | 工时 | 状态 |
|----|-------|------|------|------|
| MH-06 | 新增 `CatalogModel`, `PullProgress` 类型 | `features/engine/llms/types.ts` | 0.5h | ❌ |
| MH-07 | 新增 `searchLibrary()`, `pullModel()` API 函数 | `features/engine/llms/api.ts` | 1h | ❌ |
| MH-08 | `useModels` hook 增加 `catalog`, `pullAndRegister()` 状态/方法 | `features/engine/llms/useModels.ts` | 1h | ❌ |
| MH-09 | `/engine/llms` 页面增加 "Library" 侧栏分组 + CatalogCard 组件 | `app/(frontend)/engine/llms/page.tsx` | 2h | ❌ |
| MH-10 | Pull 进度条 UI + 自动注册流程 | `app/(frontend)/engine/llms/page.tsx` | 1.5h | ❌ |

---

## 总计: 10 stories, ~10.5h

---

## 技术细节

### 数据流

```
Admin 点击 "Pull"
  → 前端 POST /engine/llms/models/pull (SSE)     ← 例外：实时推理类接口
  → Engine 代理到 Ollama POST /api/pull (stream)
  → SSE 进度推送到前端
  → Pull 完成 → 前端调 POST /api/llms (Payload CMS)  ← 标准数据流
  → 模型注册到 CMS → 前端刷新列表
```

> ⚠️ Library 搜索和 Pull 是 **实时 Engine 接口**（类似 `/engine/query`），属于数据流例外。
> 模型注册/删除/读取一律走 **Payload CMS `/api/llms`**，符合数据流规则。

### 权限控制

- 后端: `llms.py` 路由不变（已在 Engine 层，需 admin 访问）
- CMS: `Llms.ts` collection 已有 `create: isEditorOrAdmin`, `delete: isAdmin`
- 前端: `/engine/llms` 页面已在 engine 分区下（admin 路由）

### 精选目录内容 (catalog.py)

14 个精选模型，分 4 类：
- **Recommended**: qwen3:4b, phi4-mini, gemma3:4b, llama3.2:3b
- **Reasoning**: deepseek-r1:1.5b, deepseek-r1:7b
- **Lightweight**: qwen3:1.7b, gemma3:1b, llama3.2:1b, ministral:3b, smollm3
- **Specialized**: qwen2.5-coder:7b, nomic-embed-text, mxbai-embed-large

每个模型包含: name, display_name, family, parameter_size, description, advantages[], best_for[], released, context_window, category

### 新增 Noun

| Noun | 归属模块 | 说明 |
|------|---------|------|
| `Catalog` | llms | 精选模型目录 |
| `Pull` | llms | 模型拉取操作 |
| `Progress` | llms | 拉取进度状态 |
| `Library` | llms | Ollama 模型库 |

### 文件变更清单

**新建:**
| 文件 | 模板 | 说明 |
|------|------|------|
| `engine_v2/llms/catalog.py` | `py-module-impl.md` | 精选模型目录数据 |

**修改:**
| 文件 | 说明 |
|------|------|
| `engine_v2/llms/__init__.py` | re-export catalog |
| `engine_v2/api/routes/llms.py` | +4 端点 (discover/search/pull/delete) |
| `features/engine/llms/types.ts` | +CatalogModel, +PullProgress |
| `features/engine/llms/api.ts` | +searchLibrary(), +pullModel() |
| `features/engine/llms/useModels.ts` | +catalog state, +pullAndRegister() |
| `app/(frontend)/engine/llms/page.tsx` | +Library tab, +CatalogCard, +PullProgress UI |

**文档更新:**
| 文件 | 说明 |
|------|------|
| `module-manifest/llms.md` | +catalog.py 到 Files 树, +新 Noun |
| `module-roadmap.md` | +Sprint Model Hub 索引行 |
