# Textbook RAG — 数据库设计文档

## 文档信息

- 版本: 1.0
- 角色: Senior Data Engineer / Architect
- 日期: 2026-03-07
- 输入: `docs/architecture/system-architecture.md`, `docs/sprints/sprint-plan.md`
- 状态: Active

---

## 1. 概述

### 1.1 数据库类型

| 属性 | 值 |
|------|------|
| 引擎 | **SQLite 3** (嵌入式) |
| 文件路径 | `data/textbook_rag.sqlite3` |
| 日志模式 | WAL (Write-Ahead Logging) |
| 全文检索 | FTS5 虚拟表 |
| 向量存储 | ChromaDB (独立持久化目录 `data/chroma_persist/`) |
| 字符集 | UTF-8 |
| 外键 | 启用 (`PRAGMA foreign_keys = ON`) |

### 1.2 选型理由

| 决策 | 理由 | 教材依据 |
|------|------|----------|
| SQLite 而非 PostgreSQL | 零部署、嵌入式、已有数据；MVP 为本地单用户应用 | Kreibich, *Using SQLite* — 嵌入式数据库适用场景; Kleppmann, *DDIA* Ch3 — 存储引擎选型需匹配工作负载 |
| WAL 模式 | 允许并发读写（前端读 + 后台预处理写）、崩溃恢复 | Kreibich, *Using SQLite* — WAL mode 并发特性 |
| FTS5 而非外部搜索引擎 | 内置虚拟表、零运维、BM25 排序、足够 MVP 规模 | Kreibich, *Using SQLite* — FTS 模块; Manning et al., *Intro to IR* — 倒排索引与 TF-IDF |
| ChromaDB 向量库 | 嵌入式 Python 原生、余弦相似度、与 sentence-transformers 无缝集成 | —— |
| 只读运行时 | 数据仅在离线预处理阶段写入，运行时纯只读查询 | Kleppmann, *DDIA* Ch3 — OLTP vs OLAP 工作负载分离 |

### 1.3 命名规范

| 规则 | 说明 | 示例 |
|------|------|------|
| 表名 | 小写复数 | `books`, `chunks`, `pages` |
| 字段名 | snake_case | `book_id`, `created_at`, `reading_order` |
| 主键 | `id` (AUTOINCREMENT) | `books.id`, `chunks.id` |
| 外键 | `{referenced_concept}_id` | `book_id`, `chapter_id`, `page_id` |
| 时间戳 | `_at` 后缀 | `created_at` |
| 布尔值 | 未使用（当前无布尔字段） | — |
| 自然键 | 语义唯一标识 | `books.book_id`, `chunks.chunk_id` |

---

## 2. ER 图

```
┌─────────────────────┐
│       books          │
│─────────────────────│
│ id (PK)             │
│ book_id (UNIQUE)    │──────┐
│ title               │      │
│ authors             │      │
│ page_count          │      │
│ chapter_count       │      │
│ chunk_count         │      │
└─────────────────────┘      │
         │                   │
         │ 1:N               │ 1:N
         ▼                   │
┌─────────────────────┐      │      ┌─────────────────────┐
│    book_assets       │      │      │      chapters        │
│─────────────────────│      │      │─────────────────────│
│ id (PK)             │      │      │ id (PK)             │
│ book_id (FK→books)  │      ├─────▶│ book_id (FK→books)  │
│ asset_kind          │      │      │ chapter_key         │
│ path                │      │      │ title               │
│ url                 │      │      │ content_type        │
│ created_at          │      │      └─────────────────────┘
└─────────────────────┘      │               │
                             │               │ 1:N (nullable)
         ┌───────────────────┘               │
         │ 1:N                               │
         ▼                                   │
┌─────────────────────┐                      │
│       pages          │                     │
│─────────────────────│                      │
│ id (PK)             │◀──────┐              │
│ book_id (FK→books)  │       │              │
│ page_number         │       │              │
│ width               │       │              │
│ height              │       │              │
│ created_at          │       │              │
└─────────────────────┘       │              │
                              │              │
                     FK (primary_page_id)    │
                     FK (page_id)            │
                              │              │
                              │              │
┌──────────────────────────────┴──────────────┴──────┐
│                      chunks                         │
│────────────────────────────────────────────────────│
│ id (PK)                                            │
│ chunk_id (UNIQUE)           ← 自然键               │
│ book_id (FK→books)                                 │
│ chapter_id (FK→chapters)    ← nullable             │
│ primary_page_id (FK→pages)  ← nullable             │
│ content_type                ← text|equation|table|image │
│ text                                               │
│ reading_order                                      │
│ chroma_document_id          ← ChromaDB 关联键       │
└────────────────────────────────────────────────────┘
         │                              │
         │ 1:N                          │ content sync
         ▼                              ▼
┌─────────────────────┐      ┌─────────────────────┐
│  source_locators     │      │     chunk_fts        │
│─────────────────────│      │  (FTS5 虚拟表)       │
│ id (PK)             │      │─────────────────────│
│ chunk_id (FK→chunks)│      │ rowid → chunks.id   │
│ page_id (FK→pages)  │      │ text                │
│ locator_kind        │      └─────────────────────┘
│ x0, y0, x1, y1     │
└─────────────────────┘
```

**关键关系**:
- `books` 1:N → `book_assets`, `chapters`, `pages`, `chunks`
- `chapters` 1:N → `chunks` (nullable — 前言/目录等无章节归属)
- `pages` 1:N → `chunks` (via `primary_page_id`)
- `chunks` 1:N → `source_locators` (每个 chunk 至少一个 bbox)
- `chunks` 1:1 → `chunk_fts` (FTS5 内容表同步)
- `chunks.chroma_document_id` → ChromaDB 向量文档 ID

---

## 3. 表结构

### 3.1 books 表

存储教材元数据。每本书一行。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 内部主键 |
| book_id | TEXT | NOT NULL, UNIQUE | 自然键 (e.g. `goodfellow_deep_learning`) |
| title | TEXT | NOT NULL | 书名 |
| authors | TEXT | NOT NULL DEFAULT '' | 作者 |
| page_count | INTEGER | NOT NULL DEFAULT 0 | 总页数 |
| chapter_count | INTEGER | NOT NULL DEFAULT 0 | 章节数 |
| chunk_count | INTEGER | NOT NULL DEFAULT 0 | 文本块数 |

```sql
CREATE TABLE books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    authors         TEXT    NOT NULL DEFAULT '',
    page_count      INTEGER NOT NULL DEFAULT 0,
    chapter_count   INTEGER NOT NULL DEFAULT 0,
    chunk_count     INTEGER NOT NULL DEFAULT 0
);
```

### 3.2 book_assets 表

存储书籍关联的文件资产（PDF、Markdown 等）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 内部主键 |
| book_id | INTEGER | FK→books(id), NOT NULL | 所属书籍 |
| asset_kind | TEXT | NOT NULL | 资产类型: `source_pdf`, `origin_pdf`, `markdown`, `content_list` |
| path | TEXT | NOT NULL | 相对路径 |
| url | TEXT | — | 可选下载链接 |
| created_at | TEXT | NOT NULL DEFAULT now | 创建时间 |

```sql
CREATE TABLE book_assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    asset_kind      TEXT    NOT NULL,
    path            TEXT    NOT NULL,
    url             TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**asset_kind 枚举值**:

| 值 | 说明 | 数量 |
|---|------|------|
| `source_pdf` | 原始 PDF (textbooks/ 目录) | 8 |
| `origin_pdf` | MinerU 输出的 origin PDF | 58 |
| `markdown` | MinerU 转换的 Markdown | 58 |
| `content_list` | MinerU 结构化 JSON | 58 |

### 3.3 chapters 表

存储章节/附录结构。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 内部主键 |
| book_id | INTEGER | FK→books(id), NOT NULL | 所属书籍 |
| chapter_key | TEXT | NOT NULL | 章节键 (e.g. `ch01`, `ch12`, `appA`) |
| title | TEXT | NOT NULL | 章节标题 |
| content_type | TEXT | NOT NULL DEFAULT 'text' | 内容类型 |

```sql
CREATE TABLE chapters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    chapter_key     TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    content_type    TEXT    NOT NULL DEFAULT 'text'
);
```

### 3.4 pages 表

存储每页元数据（尺寸），用于 PDF 坐标映射。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 内部主键 |
| book_id | INTEGER | FK→books(id), NOT NULL | 所属书籍 |
| page_number | INTEGER | NOT NULL | 页码（0-indexed） |
| width | REAL | NOT NULL DEFAULT 0 | 页面宽度 (pt) |
| height | REAL | NOT NULL DEFAULT 0 | 页面高度 (pt) |
| created_at | TEXT | NOT NULL DEFAULT now | 创建时间 |

```sql
CREATE TABLE pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    page_number     INTEGER NOT NULL,
    width           REAL    NOT NULL DEFAULT 0,
    height          REAL    NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### 3.5 chunks 表

核心表：存储文本块（段落、标题、公式、表格、图片标题）。每个 chunk 对应 MinerU content_list.json 中一个非 discarded 条目。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 内部主键 |
| chunk_id | TEXT | NOT NULL, UNIQUE | 自然键 (e.g. `goodfellow_deep_learning_000042`) |
| book_id | INTEGER | FK→books(id), NOT NULL | 所属书籍 |
| chapter_id | INTEGER | FK→chapters(id), nullable | 所属章节（前言等无章节归属） |
| primary_page_id | INTEGER | FK→pages(id), nullable | 所在页面 |
| content_type | TEXT | NOT NULL DEFAULT 'text' | 内容类型 |
| text | TEXT | NOT NULL DEFAULT '' | 文本内容 |
| reading_order | INTEGER | NOT NULL DEFAULT 0 | 阅读顺序（书内全局递增） |
| chroma_document_id | TEXT | — | ChromaDB 向量文档 ID |

```sql
CREATE TABLE chunks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id            TEXT    NOT NULL UNIQUE,
    book_id             INTEGER NOT NULL REFERENCES books(id),
    chapter_id          INTEGER REFERENCES chapters(id),
    primary_page_id     INTEGER REFERENCES pages(id),
    content_type        TEXT    NOT NULL DEFAULT 'text',
    text                TEXT    NOT NULL DEFAULT '',
    reading_order       INTEGER NOT NULL DEFAULT 0,
    chroma_document_id  TEXT
);
```

**content_type 分布**:

| 值 | 说明 | 数量 | 占比 |
|---|------|------|------|
| `text` | 段落/标题文本 | 207,762 | 86.6% |
| `equation` | LaTeX 公式 | 23,645 | 9.9% |
| `image` | 图片标题/caption | 5,842 | 2.4% |
| `table` | HTML 表格 | 2,629 | 1.1% |

### 3.6 source_locators 表

存储每个 chunk 在 PDF 页面上的精确位置（bbox）。用于前端高亮。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 内部主键 |
| chunk_id | INTEGER | FK→chunks(id), NOT NULL | 对应 chunk |
| page_id | INTEGER | FK→pages(id), NOT NULL | 对应页面 |
| locator_kind | TEXT | NOT NULL DEFAULT 'bbox' | 定位类型 |
| x0 | REAL | NOT NULL DEFAULT 0 | 左上角 X (pt) |
| y0 | REAL | NOT NULL DEFAULT 0 | 左上角 Y (pt) |
| x1 | REAL | NOT NULL DEFAULT 0 | 右下角 X (pt) |
| y1 | REAL | NOT NULL DEFAULT 0 | 右下角 Y (pt) |

```sql
CREATE TABLE source_locators (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id        INTEGER NOT NULL REFERENCES chunks(id),
    page_id         INTEGER NOT NULL REFERENCES pages(id),
    locator_kind    TEXT    NOT NULL DEFAULT 'bbox',
    x0              REAL    NOT NULL DEFAULT 0,
    y0              REAL    NOT NULL DEFAULT 0,
    x1              REAL    NOT NULL DEFAULT 0,
    y1              REAL    NOT NULL DEFAULT 0
);
```

### 3.7 chunk_fts 虚拟表 (FTS5)

FTS5 全文索引，用于 BM25 关键词检索。通过触发器与 `chunks` 表自动同步。

```sql
CREATE VIRTUAL TABLE chunk_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);
```

**同步触发器**:

```sql
-- 插入同步
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text);
END;

-- 删除同步
CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES('delete', old.id, old.text);
END;

-- 更新同步
CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES('delete', old.id, old.text);
    INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text);
END;
```

**教材依据**: Kreibich, *Using SQLite* — FTS 模块、MATCH 运算符、BM25 排序; Manning et al., *Introduction to Information Retrieval* Ch1-6 — 倒排索引、TF-IDF、向量空间模型

---

## 4. 索引设计

### 4.1 索引列表

| 索引名 | 表 | 列 | 用途 |
|--------|----|----|------|
| `idx_chunks_book_id` | chunks | book_id | 按书筛选 chunks |
| `idx_chunks_chapter_id` | chunks | chapter_id | 按章节筛选 chunks |
| `idx_chunks_primary_page` | chunks | primary_page_id | 按页查找 chunks |
| `idx_pages_book_page` | pages | (book_id, page_number) | 按书+页码定位页面 |
| `idx_chapters_book` | chapters | book_id | 按书查章节列表 |
| `idx_source_locators_chunk` | source_locators | chunk_id | 获取 chunk 的所有 bbox |
| `idx_source_locators_page` | source_locators | page_id | 获取页面上所有 bbox |
| `idx_book_assets_book` | book_assets | book_id | 获取书的资产列表 |
| (UNIQUE) | books | book_id | 按自然键查找 |
| (UNIQUE) | chunks | chunk_id | 按自然键查找 |

### 4.2 索引策略

索引设计覆盖以下核心查询模式：

1. **按书浏览**: `books` → `chapters` → `chunks`（走 `idx_chapters_book`, `idx_chunks_chapter_id`）
2. **按书+页码定位**: `pages` WHERE book_id AND page_number（走复合 `idx_pages_book_page`）
3. **FTS 关键词搜索**: `chunk_fts` MATCH → JOIN `chunks` → JOIN `books`（FTS5 内部 B-Tree）
4. **来源高亮**: `source_locators` WHERE chunk_id（走 `idx_source_locators_chunk`）
5. **页面全部 bbox**: `source_locators` WHERE page_id（走 `idx_source_locators_page`）

**教材依据**: Kleppmann, *DDIA* Ch3 — B-Tree 索引结构、覆盖索引; Kreibich, *Using SQLite* — SQLite 索引策略

---

## 5. 数据字典

### 5.1 当前语料统计

| 指标 | 值 |
|------|------|
| 教材数 | 58 |
| 章节数 | 991 |
| 页面数 | 29,383 |
| 文本块数 | 239,878 |
| 来源定位数 | 239,878 |
| 资产数 | 182 |
| FTS 索引行数 | 239,878 |
| 无章节归属的 chunks | 4,162 (1.7%) |
| SQLite 文件大小 | ~141 MB |

### 5.2 content_type 枚举

| 值 | 来源 | 说明 |
|---|------|------|
| `text` | MinerU type=text | 段落、标题、列表项 |
| `equation` | MinerU type=equation | LaTeX 公式（含 `text_format: latex`） |
| `table` | MinerU type=table | HTML 表格（`table_body` 字段） |
| `image` | MinerU type=image | 图片标题（`image_caption` 字段） |

### 5.3 locator_kind 枚举

| 值 | 说明 |
|---|------|
| `bbox` | PDF 页面坐标矩形 (x0, y0, x1, y1)，单位: PDF points |

### 5.4 asset_kind 枚举

| 值 | 路径模式 | 说明 |
|---|------|------|
| `source_pdf` | `textbooks/{book}.pdf` | 原始 PDF（仅部分书有） |
| `origin_pdf` | `data/mineru_output/{book}/{book}/auto/{book}_origin.pdf` | MinerU 处理前 PDF |
| `markdown` | `data/mineru_output/{book}/{book}/auto/{book}.md` | MinerU Markdown 输出 |
| `content_list` | `data/mineru_output/{book}/{book}/auto/{book}_content_list.json` | MinerU 结构化内容 |

---

## 6. 数据流与 Pipeline

### 6.1 离线预处理 Pipeline

```
textbooks/*.pdf
  ↓ MinerU (scripts/batch_mineru.py)
data/mineru_output/{book}/{book}/auto/
  ├── {book}_content_list.json   ← 结构化内容 + bbox
  ├── {book}_middle.json         ← 页面尺寸
  ├── {book}.md                  ← Markdown
  └── {book}_origin.pdf          ← 原始 PDF 副本
  ↓ scripts/rebuild_db.py
data/textbook_rag.sqlite3
  ├── books, chapters, pages     ← 元数据
  ├── chunks + source_locators   ← 文本块 + bbox
  ├── chunk_fts                  ← FTS5 全文索引
  └── book_assets                ← 资产路径
  ↓ scripts/rebuild_db.py (可选)
data/chroma_persist/
  └── textbook_chunks collection ← 向量嵌入 (cosine)
```

### 6.2 运行时查询流

```
用户问题
  ↓
RetrievalService
  ├── FTS5 关键词检索 (BM25)
  │   SELECT ... FROM chunk_fts WHERE chunk_fts MATCH ?
  │   JOIN chunks, books, source_locators
  │
  └── ChromaDB 向量检索 (cosine similarity)
      collection.query(query_texts=[question], n_results=K)
  ↓
RRF 融合排序 → top_k chunks
  ↓
GenerationService (Ollama)
  ↓
API Response (answer + sources with bbox)
```

### 6.3 重建命令

```bash
# 全量重建（SQLite + ChromaDB）
uv run python scripts/rebuild_db.py

# 快速重建（仅 SQLite，跳过向量）
uv run python scripts/rebuild_db.py --skip-vectors

# 重建单本书
uv run python scripts/rebuild_db.py --book goodfellow_deep_learning

# 重建主题索引
uv run python scripts/rebuild_topic_index.py
```

---

## 7. ChromaDB 向量存储

### 7.1 配置

| 属性 | 值 |
|------|------|
| 持久化路径 | `data/chroma_persist/` |
| Collection 名 | `textbook_chunks` |
| 距离度量 | cosine |
| 嵌入模型 | all-MiniLM-L6-v2 (ChromaDB 默认) |
| 文档数 | 与 chunks 表行数一致 |

### 7.2 元数据字段

每个 ChromaDB 文档携带以下 metadata：

| 字段 | 类型 | 说明 |
|------|------|------|
| book_id | string | 书的自然键 |
| chunk_id | string | chunk 自然键 |
| page_idx | int | 页码 (0-indexed) |
| content_type | string | text/equation/table/image |

### 7.3 关联方式

`chunks.chroma_document_id` 存储 ChromaDB document ID (UUID)。查询时：
1. ChromaDB 返回 document IDs
2. 通过 `chroma_document_id` 反查 `chunks` 表获取完整元数据和 bbox

---

## 8. 查询模式与示例 SQL

### 8.1 FTS5 全文检索 + 来源定位

```sql
SELECT
    c.chunk_id,
    b.title      AS book_title,
    ch.title     AS chapter_title,
    p.page_number,
    c.text,
    sl.x0, sl.y0, sl.x1, sl.y1,
    p.width, p.height
FROM chunk_fts f
JOIN chunks c          ON c.id = f.rowid
JOIN books b           ON c.book_id = b.id
LEFT JOIN chapters ch  ON c.chapter_id = ch.id
LEFT JOIN pages p      ON c.primary_page_id = p.id
LEFT JOIN source_locators sl ON sl.chunk_id = c.id
WHERE chunk_fts MATCH ?    -- 参数化查询，防 SQL 注入
ORDER BY rank              -- FTS5 BM25 排名
LIMIT ?;
```

### 8.2 按书获取章节列表

```sql
SELECT ch.chapter_key, ch.title, COUNT(c.id) AS chunk_count
FROM chapters ch
LEFT JOIN chunks c ON c.chapter_id = ch.id
WHERE ch.book_id = ?
GROUP BY ch.id
ORDER BY ch.chapter_key;
```

### 8.3 按页获取所有 bbox

```sql
SELECT c.chunk_id, c.content_type, c.text,
       sl.x0, sl.y0, sl.x1, sl.y1
FROM source_locators sl
JOIN chunks c ON sl.chunk_id = c.id
JOIN pages p  ON sl.page_id = p.id
WHERE p.book_id = ? AND p.page_number = ?
ORDER BY c.reading_order;
```

### 8.4 书籍列表 + PDF 路径

```sql
SELECT b.id, b.book_id, b.title, b.authors,
       b.page_count, b.chapter_count, b.chunk_count,
       ba.path AS pdf_path
FROM books b
LEFT JOIN book_assets ba ON ba.book_id = b.id AND ba.asset_kind = 'source_pdf'
ORDER BY b.title;
```

---

## 9. 安全考量

| 关注点 | 措施 | 教材依据 |
|--------|------|----------|
| SQL 注入 | 所有查询使用 `?` 参数化占位符，不拼接字符串 | Zalewski, *The Tangled Web*; OWASP Top 10 |
| 路径穿越 | PDF 服务通过 `book_assets.path` 表映射，不接受用户路径 | Gourley, *HTTP: The Definitive Guide* |
| 数据完整性 | `FOREIGN KEY` 约束 + `NOT NULL` 约束 | Kreibich, *Using SQLite* — 约束与数据完整性 |

---

## 10. 扩展路径

| 场景 | 变更 |
|------|------|
| 新增教材 | 运行 `scripts/batch_mineru.py` + `scripts/rebuild_db.py --book <name>` |
| 语义分块 | 在 `rebuild_db.py` 中添加 token 窗口切分，同时保留 bbox 多对一映射 |
| 用户系统 | 新增 `users` 表 + `query_history` 表 |
| 缓存层 | 新增 `query_cache` 表（question hash → answer） |
| 全量向量 | `uv run python scripts/rebuild_db.py`（不加 `--skip-vectors`） |

---

## 11. 教材引用汇总

| 教材 | 引用章节/概念 | 影响的设计决策 |
|------|---------------|----------------|
| Kreibich, *Using SQLite* | WAL mode, FTS5, 虚拟表, 约束 | 数据库引擎选型、全文检索、数据完整性 |
| Kleppmann, *DDIA* | Ch2 数据模型, Ch3 存储引擎/索引 | 关系模型选型、B-Tree 索引策略、只读工作负载分离 |
| Manning et al., *Intro to IR* | Ch1-6 倒排索引, TF-IDF, BM25 | FTS5 检索策略 |
| Fontaine, *Art of PostgreSQL* | 查询模式, 索引策略 | 索引设计（概念迁移到 SQLite） |
| Zalewski, *The Tangled Web* | 注入防护 | 参数化查询 |
