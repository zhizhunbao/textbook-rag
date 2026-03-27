# ✅ 书本初始化 — 完成报告

## 执行结果

| Stage | 状态 | 结果 |
|-------|------|------|
| **1. Ingest** (rebuild_db.py) | ✅ 完成 | 59 books → SQLite |
| **2. TOC** (rebuild_toc.py) | ✅ 完成 | 52 books, 10,143 TOC entries |
| **3. Vectors** (build_vectors.py) | ✅ 完成 | 184,061 chunks → ChromaDB (GPU RTX 4060, ~23 min) |
| **4. Sync** (sync_to_payload.py) | ✅ 完成 | 46 created + 13 skipped, 743 chapters synced |

### 类别分布

| 类别 | 书本数 | 备注 |
|------|--------|------|
| textbooks | 46 | CLRS, Fluent Python, DDIA 等经典教材 |
| ecdev | 12 | 经济发展季度更新 |
| real_estate | 1 | OREB 市场报告 |

---

## Bug 修复

### Category 命名不一致 (重要)

文件系统目录是 `textbooks`（复数），但代码中有多处使用 `textbook`（单数）。

修复范围：

| 文件 | 修改 |
|------|------|
| [`scripts/rebuild_db.py`](../scripts/rebuild_db.py) | `SOURCE_DIRS` key, `categories` list, fallback → `"textbooks"` |
| [`scripts/sync_to_payload.py`](../scripts/sync_to_payload.py) | `detect_category()` 返回值保持 `"textbook"` (Payload select 枚举值) |

> [!IMPORTANT]
> 两个层面的 "category" 含义不同：
> - **文件系统层**: `textbooks` (复数) — rebuild_db.py 用这个扫描目录
> - **Payload CMS 层**: `textbook` (单数) — Books 集合 select 枚举值

---

## 新增功能

### 1. 统一 CLI 入口: `init_books.py`

```bash
# 完整 pipeline
.venv/Scripts/python scripts/init_books.py

# 跳过向量
.venv/Scripts/python scripts/init_books.py --skip-vectors

# 单本书
.venv/Scripts/python scripts/init_books.py --book cormen_CLRS

# 特定 stage
.venv/Scripts/python scripts/init_books.py --stages ingest,toc
```

→ [`scripts/init_books.py`](../scripts/init_books.py)

### 2. Pipeline Feature 模块 (前端)

新增 `features/pipeline/` 模块，遵循单一职责：

```
features/pipeline/
├── types.ts              ← PipelineTask, TaskType 类型
├── api.ts                ← triggerPipeline, triggerEngineSync, fetchTask
├── PipelineActions.tsx   ← Pipeline 下拉按钮组件
└── index.ts              ← barrel export
```

已集成到 LibraryPage toolbar，提供：
- **Sync Engine → CMS** — 全量同步
- **Re-ingest** — 重新处理选中的书
- **Reindex** — 重建 FTS + 向量索引
- **Full Pipeline** — 执行完整流程

→ [`payload/src/features/pipeline/PipelineActions.tsx`](../payload/src/features/pipeline/PipelineActions.tsx)

### 3. Features 模块拆分方案

详见 → [`docs/features-refactoring-plan.md`](./features-refactoring-plan.md)

核心变更：
- `chat/` 上帝模块 → 拆出 `pdf/`, `trace/`, `book-picker/`
- `shared/` 垃圾桶 → 拆出 `api/`, `ui/`
- `models/api.ts` 626 行 → 拆为 `api/crud.ts` + `health.ts` + `discovery.ts`

---

## 当前运行的服务

| 服务 | 端口 | 状态 |
|------|------|------|
| Engine (FastAPI) | 8000 | ✅ 运行中 |
| Payload CMS | 3000 | ✅ 运行中 |
