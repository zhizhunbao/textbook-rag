# Textbook RAG v1.1 — 数据库设计文档

> **版本**: 1.1
> **作者**: Bob (Architect)
> **日期**: 2026-03-11
> **输入**: system-architecture.md, v1.0 rebuild_db.py

---

## 1. 数据库概述

| 组件 | 技术 | 用途 |
|------|------|------|
| **SQLite** | textbook_rag.sqlite3 | 结构化数据 + FTS5 全文搜索 |
| **ChromaDB** | chroma_persist/ | 向量嵌入 + 语义搜索 |

v1.1 在 v1.0 schema 基础上做**最小增量变更**，不影响现有数据。

---

## 2. v1.0 现有 Schema（保留）

```
books (id, book_id, title, authors, page_count, chapter_count, chunk_count)
  │
  ├── book_assets (id, book_id, asset_kind, path, url, created_at)
  ├── chapters (id, book_id, chapter_key, title, content_type)
  ├── pages (id, book_id, page_number, width, height, created_at)
  └── chunks (id, chunk_id, book_id, chapter_id, primary_page_id, content_type, text, reading_order, chroma_document_id)
       │
       ├── source_locators (id, chunk_id, page_id, locator_kind, x0, y0, x1, y1)
       └── chunk_fts (text) ← FTS5 虚拟表, content='chunks'

toc_entries (id, book_id, level, number, title, pdf_page, sort_order)
```

---

## 3. v1.1 Schema 变更

### 3.1 books 表新增 `category` 列

```sql
ALTER TABLE books ADD COLUMN category TEXT NOT NULL DEFAULT 'textbook';
-- 值域: 'textbook', 'ecdev', 'real_estate'
```

**变更影响**:
- `rebuild_db.py` 新增 `--category` 参数
- `BOOK_REGISTRY` 扩展 EcDev 和房地产条目
- 检索策略根据 category 过滤

### 3.2 prompt_templates 表（新增）

```sql
CREATE TABLE IF NOT EXISTS prompt_templates (
    id          TEXT    PRIMARY KEY,     -- 'default', 'concise', 'detailed', 'academic'
    name        TEXT    NOT NULL,        -- 显示名
    description TEXT    NOT NULL DEFAULT '',
    system_prompt TEXT  NOT NULL,        -- system prompt 完整内容
    is_builtin  INTEGER NOT NULL DEFAULT 1,  -- 1=内置, 0=用户自定义
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**设计理由**: 用户要求 prompt 可配置可增强（通过表存储而非硬编码常量，支持运行时编辑）

### 3.3 evaluation_runs 表（新增）

```sql
CREATE TABLE IF NOT EXISTS evaluation_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    config_json TEXT    NOT NULL DEFAULT '{}'  -- 运行时配置快照
);

CREATE TABLE IF NOT EXISTS evaluation_questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES evaluation_runs(id),
    question    TEXT    NOT NULL,
    ground_truth TEXT,
    system_answer TEXT,
    score       REAL,           -- 1.0 / 0.5 / 0.0
    top3_doc_ids TEXT,          -- JSON array of chunk_ids
    relevance_scores TEXT,      -- JSON array of 1/0.5/0 per doc
    trace_json  TEXT,           -- 完整 trace 快照
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_eval_q_run ON evaluation_questions(run_id);
```

**设计理由**: NLP 作业要求 20 题评估 + top-3 文档相关性标注，需要持久化评估结果

### 3.4 page_structure 表（新增 — PageIndex 策略数据源）

```sql
CREATE TABLE IF NOT EXISTS page_structure (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    node_id         TEXT    NOT NULL,       -- MinerU 结构树节点 ID
    title           TEXT    NOT NULL,       -- 节点标题
    level           INTEGER NOT NULL,       -- 层级深度 (1=章, 2=节, ...)
    parent_node_id  TEXT,                   -- 父节点 ID
    page_number     INTEGER,                -- 对应 PDF 页码
    line_num        INTEGER,                -- 对应 MinerU Markdown 行号
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_page_structure_book ON page_structure(book_id);
CREATE INDEX IF NOT EXISTS idx_page_structure_parent ON page_structure(book_id, parent_node_id);
```

**设计理由**: PageIndex 策略需要文档结构树数据。数据从 MinerU `_middle.json` 的 `para_blocks` 中提取，预处理后入库。与 `toc_entries` 的区别：
- `toc_entries` 来自 PDF 书签（rebuild_toc.py）
- `page_structure` 来自 MinerU 解析的实际文档结构（rebuild_db.py 新增）
- PageIndex 返回 line_num（行级定位），TOC 返回 pdf_page（页级定位）

**数据准备**: `rebuild_db.py` 新增 `_extract_page_structure()` 函数，从 `_middle.json` 提取结构树节点。

---

## 4. 完整 v1.1 ER 图

```
┌──────────────────────┐
│       books          │
│──────────────────────│
│ id (PK)              │
│ book_id (UNIQUE)     │
│ title                │
│ authors              │
│ category (NEW)       │──── 'textbook'│'ecdev'│'real_estate'
│ page_count           │
│ chapter_count        │
│ chunk_count          │
└───────┬──────────────┘
        │ 1:N
  ┌─────┼──────────┬──────────────┐
  │     │          │              │
  ▼     ▼          ▼              ▼
┌────┐ ┌────────┐ ┌──────┐ ┌──────────┐
│book│ │chapters│ │pages │ │toc_      │
│_   │ │        │ │      │ │entries   │
│ass │ │id (PK) │ │id(PK)│ │id (PK)   │
│ets │ │book_id │ │book  │ │book_id   │
│    │ │ch_key  │ │page# │ │level     │
│id  │ │title   │ │width │ │number    │
│book│ │content │ │height│ │title     │
│kind│ │_type   │ │      │ │pdf_page  │
│path│ └───┬────┘ └──┬───┘ │sort_order│
│url │     │         │     └──────────┘
└────┘     │         │
           │    1:N  │ 1:N
           ▼         ▼
      ┌─────────────────────────┐
      │        chunks           │
      │─────────────────────────│
      │ id (PK)                 │
      │ chunk_id (UNIQUE)       │
      │ book_id (FK → books)    │
      │ chapter_id (FK → ch)    │
      │ primary_page_id (FK)    │
      │ content_type            │──── 'text'│'table'│'image'│'equation'
      │ text                    │
      │ reading_order           │
      │ chroma_document_id      │
      └────────┬────────────────┘
               │ 1:N
               ▼
      ┌─────────────────────┐
      │  source_locators    │
      │─────────────────────│
      │ id (PK)             │
      │ chunk_id (FK)       │
      │ page_id (FK → pages)│
      │ locator_kind        │──── 'bbox'
      │ x0, y0, x1, y1     │──── PDF point 坐标
      └─────────────────────┘

      ┌──────────────────────┐
      │  chunk_fts (FTS5)    │
      │──────────────────────│
      │ text                 │
      │ content='chunks'     │
      └──────────────────────┘

      ┌───────────────────────────┐
      │  prompt_templates (NEW)   │
      │───────────────────────────│
      │ id (PK, TEXT)             │
      │ name                      │
      │ description               │
      │ system_prompt             │
      │ is_builtin                │
      │ created_at, updated_at    │
      └───────────────────────────┘

      ┌────────────────────────────┐
      │  evaluation_runs (NEW)     │
      │────────────────────────────│
      │ id (PK)                    │
      │ run_name                   │
      │ created_at                 │
      │ config_json                │
      └──────────┬─────────────────┘
                 │ 1:N
                 ▼
      ┌────────────────────────────────┐
      │  evaluation_questions (NEW)    │
      │────────────────────────────────│
      │ id (PK)                        │
      │ run_id (FK → evaluation_runs)  │
      │ question                       │
      │ ground_truth                   │
      │ system_answer                  │
      │ score (1.0/0.5/0.0)           │
      │ top3_doc_ids (JSON)           │
      │ relevance_scores (JSON)       │
      │ trace_json                     │
      │ created_at                     │
      └────────────────────────────────┘

      ┌───────────────────────────────┐
      │  page_structure (NEW)         │
      │───────────────────────────────│
      │ id (PK)                       │
      │ book_id (FK → books)          │
      │ node_id                       │
      │ title                         │
      │ level                         │
      │ parent_node_id                │
      │ page_number                   │
      │ line_num                      │
      │ sort_order                    │
      └───────────────────────────────┘
```

---

## 5. ChromaDB Schema

保持 v1.0 不变：

| 字段 | 说明 |
|------|------|
| `id` | UUID，对应 chunks.chroma_document_id |
| `document` | chunk text（max 8000 chars） |
| `metadata.book_id` | 书目 key |
| `metadata.chunk_id` | chunk_id |
| `metadata.page_idx` | page index |
| `metadata.content_type` | text/table/image/equation |

v1.1 新增 metadata 字段：

| 字段 | 说明 |
|------|------|
| `metadata.category` | textbook/ecdev/real_estate |

---

## 6. 索引策略

### 现有索引（保留）

```sql
idx_chunks_book_id        ON chunks(book_id)
idx_chunks_chapter_id     ON chunks(chapter_id)
idx_chunks_primary_page   ON chunks(primary_page_id)
idx_pages_book_page       ON pages(book_id, page_number)
idx_chapters_book         ON chapters(book_id)
idx_source_locators_chunk ON source_locators(chunk_id)
idx_source_locators_page  ON source_locators(page_id)
idx_book_assets_book      ON book_assets(book_id)
idx_toc_entries_book      ON toc_entries(book_id)
idx_toc_entries_page      ON toc_entries(book_id, pdf_page)
```

### 新增索引

```sql
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks(content_type);
CREATE INDEX IF NOT EXISTS idx_page_structure_book ON page_structure(book_id);
CREATE INDEX IF NOT EXISTS idx_page_structure_parent ON page_structure(book_id, parent_node_id);
```

**理由**: category 和 content_type 是横切过滤器的高频查询路径；page_structure 索引支持 PageIndex 策略的 book 级查询。

---

## 7. 数据迁移策略

v1.0 → v1.1 迁移为**追加式**，无破坏性：

```sql
-- Step 1: 新增列（如果 DB 已存在）
ALTER TABLE books ADD COLUMN category TEXT NOT NULL DEFAULT 'textbook';

-- Step 2: 新增表
-- prompt_templates, evaluation_runs, evaluation_questions
-- (用 CREATE TABLE IF NOT EXISTS，幂等)

-- Step 3: 新增索引
CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
CREATE INDEX IF NOT EXISTS idx_chunks_content_type ON chunks(content_type);

-- Step 4: 插入内置 prompt 模板
INSERT OR IGNORE INTO prompt_templates (id, name, description, system_prompt)
VALUES
  ('default', 'Default', 'Balanced IELTS-style response', '...'),
  ('concise', 'Concise', 'Short direct answer', '...'),
  ('detailed', 'Detailed', 'Thorough with examples', '...'),
  ('academic', 'Academic', 'Formal academic style', '...');
```

**rebuild_db.py** 增量修改：
1. `SCHEMA_SQL` 加入新表和新索引
2. `ingest_book()` 接受 `category` 参数
3. `main()` 新增 `--category` CLI 选项

---

## 8. 查询模式

### 8.1 检索相关查询

| 查询 | SQL | 使用者 |
|------|-----|--------|
| FTS5 搜索 | `SELECT ... FROM chunk_fts WHERE chunk_fts MATCH ? ...` | FTS5BM25Strategy |
| Vector 搜索 | `collection.query(query_texts=[...])` | VectorStrategy (ChromaDB) |
| TOC 标题搜索 | `SELECT * FROM toc_entries WHERE book_id=? AND title LIKE ?` | TOCHeadingStrategy |
| PageIndex 节点搜索 | `SELECT * FROM page_structure WHERE book_id=?` | PageIndexStrategy |
| 横切过滤 — 类别 | `... JOIN books b ON c.book_id=b.id WHERE b.category=?` | 所有策略的前置 filter |
| 横切过滤 — 内容类型 | `... WHERE content_type IN (?)` | 所有策略的前置 filter |
| Source locators | `SELECT * FROM source_locators WHERE chunk_id IN (...)` | CitationEngine |
| Page dimensions | `SELECT width, height FROM pages WHERE id=?` | PDF bbox 坐标转换 |

### 8.2 评估查询

| 查询 | SQL | 使用者 |
|------|-----|--------|
| 创建评估运行 | `INSERT INTO evaluation_runs ...` | evaluate.py |
| 记录评估结果 | `INSERT INTO evaluation_questions ...` | evaluate.py |
| 获取评估统计 | `SELECT AVG(score)... FROM evaluation_questions WHERE run_id=?` | 评估报告 |

### 8.3 Prompt 模板查询

| 查询 | SQL | 使用者 |
|------|-----|--------|
| 获取所有模板 | `SELECT * FROM prompt_templates` | GET /api/prompt-templates |
| 获取指定模板 | `SELECT system_prompt FROM prompt_templates WHERE id=?` | GenerationEngine |
| 更新/创建自定义模板 | `INSERT OR REPLACE INTO prompt_templates ...` | 前端 Prompt 编辑器 |
