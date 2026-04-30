# Sprint Model Hub — Ollama 模型库浏览 + 一键拉取 + 性能测试

> **模块**: `llms` (Engine 子模块)
> **权限**: Admin only — 管理员功能，非用户功能
> **路由**: `/engine/llms`（扩展现有页面，增加 Library + Benchmark 侧栏 Tab）
> **前置**: Sprint Demo ✅, Sprint 2 llms 基础 ✅

---

## 目标

让管理员在现有 `/engine/llms` 页面中：
1. 浏览精选模型目录（含优势、更新时间、推荐用途）
2. 一键 Pull 模型（含 SSE 进度条）
3. Pull 完成后自动注册到 CMS
4. 串行运行模型基准测试（标准问题 + 自定义问题）
5. 对比模型性能：延迟、Token 用量、费用

---

## Stories

### 后端 (Engine Python)

| ID | Story | 文件 | 工时 | 状态 |
|----|-------|------|------|------|
| MH-01 | 创建精选模型目录数据 (`catalog.py`) | `engine_v2/llms/catalog.py` | 1h | ✅ |
| MH-02 | 添加 `/engine/llms/models/discover` 端点 — 列出本地已安装模型详情 | `engine_v2/api/routes/llms.py` | 0.5h | ✅ |
| MH-03 | 添加 `/engine/llms/library/search` 端点 — 搜索/过滤精选目录 | `engine_v2/api/routes/llms.py` | 1h | ✅ |
| MH-04 | 添加 `POST /engine/llms/models/pull` 端点 — SSE 流式拉取模型 | `engine_v2/api/routes/llms.py` | 1.5h | ✅ |
| MH-05 | 添加 `DELETE /engine/llms/models/{name}` 端点 — 从 Ollama 删除模型 | `engine_v2/api/routes/llms.py` | 0.5h | ✅ |
| MH-11 | 创建标准测试问题 (`prompts.py`) | `engine_v2/llms/prompts.py` | 0.5h | ✅ |
| MH-12 | 创建测试执行逻辑 (`benchmark.py`) | `engine_v2/llms/benchmark.py` | 1h | ✅ |
| MH-13 | 添加 `POST /engine/llms/models/test` + `/test-batch` (SSE) 端点 | `engine_v2/api/routes/llms.py` | 1h | ✅ |
| MH-14 | 添加 `GET /engine/llms/benchmark/questions` 端点 | `engine_v2/api/routes/llms.py` | 0.5h | ✅ |

### 前端 (React/Payload)

| ID | Story | 文件 | 工时 | 状态 |
|----|-------|------|------|------|
| MH-06 | 新增 `CatalogModel`, `BenchmarkResult`, `PullProgress` 类型 | `features/engine/llms/types.ts` | 0.5h | ✅ |
| MH-07 | 新增 `searchLibrary()`, `pullModel()`, `testModel()`, `testBatch()` API 函数 | `features/engine/llms/api.ts` | 1h | ✅ |
| MH-08 | `useModels` hook 增加 `catalog`, `pullAndRegister()` 状态/方法 | `features/engine/llms/useModels.ts` | 1h | ✅ |
| MH-09 | `/engine/llms` 页面增加 "Library" 侧栏 Tab + CatalogCard 组件 | `components/CatalogCard.tsx` + `page.tsx` | 2h | ✅ |
| MH-10 | Pull 进度条 UI + 自动注册流程 | `components/CatalogCard.tsx` | 1.5h | ✅ |
| MH-15 | Benchmark Console 组件 — 模型选择 + 问题选择 + 串行测试 + 结果对比表 | `components/BenchmarkConsole.tsx` + `page.tsx` | 3h | ✅ |

---

## 总计: 16 stories, 16/16 completed (~15h)

> MH-08 已收口 — catalog 加载、刷新、Pull 进度、Pull 完成后的 CMS 自动注册统一由 `useModels` hook 管理，
> `/engine/llms` 页面只负责展示和触发回调。

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

### Benchmark 串行执行 (4060 8GB VRAM 约束)

```
Admin 选择 N 个模型 + M 个问题 → Run Benchmark
  → 前端 POST /engine/llms/models/test-batch (SSE)
  → Engine 串行执行：
      for model in models:
        for question in questions:
          - 加载模型到 VRAM (Ollama 自动处理)
          - 执行推理 → 收集 latency, tokens, cost
          - SSE 推送 result 到前端
          - 0.1s delay 让 Ollama 卸载
  → 前端实时渲染结果对比表
```

### 权限控制

- 后端: `llms.py` 路由不变（已在 Engine 层，需 admin 访问）
- CMS: `Llms.ts` collection 已有 `create: isEditorOrAdmin`, `delete: isAdmin`
- 前端: `/engine/llms` 页面已在 engine 分区下（admin 路由）

### 精选目录内容 (catalog.py)

14 个精选模型，分 4 类：
- **Recommended**: qwen3:4b, phi4-mini, gemma3:4b, llama3.2:3b
- **Reasoning**: deepseek-r1:1.5b, deepseek-r1:7b
- **Lightweight**: qwen3:1.7b, gemma3:1b, llama3.2:1b, smollm2:1.7b
- **Specialized**: qwen2.5-coder:7b, nomic-embed-text, mxbai-embed-large, reader-lm:0.5b

每个模型包含: name, display_name, family, parameter_size, description, advantages[], best_for[], released, context_window, category

### 标准测试问题 (prompts.py)

9 个标准问题，分 4 类：
- **simple**: 基础事实回忆
- **reasoning**: 分析/对比/诊断
- **multilingual**: 中文理解和推理
- **rag**: 基于上下文的精确提取

### 新增 Noun

| Noun | 归属模块 | 说明 |
|------|---------|------|
| `Catalog` | llms | 精选模型目录 |
| `Pull` | llms | 模型拉取操作 |
| `Progress` | llms | 拉取进度状态 |
| `Library` | llms | Ollama 模型库 |
| `Benchmark` | llms | 模型性能测试 |

### 文件变更清单

**新建:**
| 文件 | 模板 | 说明 |
|------|------|------|
| `engine_v2/llms/catalog.py` | `py-module-impl.md` | 精选模型目录数据 |
| `engine_v2/llms/prompts.py` | `py-module-impl.md` | 标准测试问题 |
| `engine_v2/llms/benchmark.py` | `py-module-impl.md` | 测试执行逻辑 |
| `features/engine/llms/components/CatalogCard.tsx` | — | 精选模型卡片 |
| `features/engine/llms/components/BenchmarkConsole.tsx` | — | 测试控制台 |

**修改:**
| 文件 | 说明 |
|------|------|
| `engine_v2/llms/__init__.py` | 更新 docstring |
| `engine_v2/api/routes/llms.py` | +8 端点 (discover/search/categories/questions/pull/test/test-batch/delete) |
| `features/engine/llms/types.ts` | +CatalogModel, +BenchmarkQuestion, +BenchmarkResult, +PullProgress |
| `features/engine/llms/api.ts` | +searchLibrary(), +pullModel(), +testModel(), +testBatch(), +fetchBenchmarkQuestions() |
| `app/(frontend)/engine/llms/page.tsx` | +Library tab, +Benchmark tab, +CatalogCard, +BenchmarkConsole |
