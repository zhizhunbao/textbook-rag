# AI Textbook Q&A System — Database Design

> **Author**: Bob (Architect)
> **Phase**: 6/11 — Database Design
> **Date**: 2026-03-04
> **Input**: `docs/architecture/system-architecture.md` §4

---

## 1. Overview

This system uses **three data stores**, each optimized for a different retrieval pattern:

| Store              | Technology            | Purpose                                | Data                                      |
| ------------------ | --------------------- | -------------------------------------- | ----------------------------------------- |
| `textbook_qa.db`   | SQLite + FTS5         | BM25 keyword search + metadata queries | All chunks with full metadata             |
| `chroma_db/`       | ChromaDB (persistent) | Semantic similarity search             | All chunks embedded with all-MiniLM-L6-v2 |
| `pageindex_trees/` | JSON files            | LLM-guided TOC navigation              | Hierarchical TOC tree per book            |

---

## 2. SQLite Database (`textbook_qa.db`)

### 2.1 Entity: `chunks`

The primary table storing all text chunks extracted from textbooks.

```sql
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id      TEXT PRIMARY KEY,       -- "{book_key}_p{page}_{idx}"
    book_key      TEXT NOT NULL,          -- e.g. "goodfellow_deep_learning"
    book_title    TEXT NOT NULL,          -- e.g. "Deep Learning"
    author        TEXT,                   -- e.g. "Goodfellow et al."
    chapter       TEXT,                   -- e.g. "8 Optimization for Training Deep Models"
    section       TEXT,                   -- e.g. "8.5"
    page_number   INTEGER NOT NULL,       -- Original PDF page number (0-indexed from MinerU)
    content_type  TEXT NOT NULL           -- "text" | "table" | "formula" | "figure"
                  CHECK(content_type IN ('text', 'table', 'formula', 'figure')),
    text          TEXT NOT NULL,          -- Chunk content (plain text / HTML / LaTeX)
    bbox_json     TEXT NOT NULL,          -- JSON: [x0, y0, x1, y1]
    text_level    INTEGER,               -- Heading level (1=chapter, 2=section, NULL=body)
    token_count   INTEGER,               -- Approximate token count
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_chunks_book ON chunks(book_key);
CREATE INDEX idx_chunks_page ON chunks(book_key, page_number);
CREATE INDEX idx_chunks_type ON chunks(content_type);
CREATE INDEX idx_chunks_chapter ON chunks(book_key, chapter);
```

### 2.2 FTS5 Virtual Table: `chunks_fts`

Full-text search index on chunk content with BM25 ranking.

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,      -- Included for join, not indexed for search
    book_title,              -- Searchable: book title
    chapter,                 -- Searchable: chapter name
    text,                    -- Searchable: chunk content
    content='chunks',        -- Content sync with main table
    content_rowid='rowid',
    tokenize='porter unicode61'  -- Porter stemming + Unicode support
);

-- Triggers for content sync
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, chunk_id, book_title, chapter, text)
    VALUES (new.rowid, new.chunk_id, new.book_title, new.chapter, new.text);
END;

CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, book_title, chapter, text)
    VALUES ('delete', old.rowid, old.chunk_id, old.book_title, old.chapter, old.text);
END;

CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, book_title, chapter, text)
    VALUES ('delete', old.rowid, old.chunk_id, old.book_title, old.chapter, old.text);
    INSERT INTO chunks_fts(rowid, chunk_id, book_title, chapter, text)
    VALUES (new.rowid, new.chunk_id, new.book_title, new.chapter, new.text);
END;
```

### 2.3 Entity: `books`

Metadata table for indexed books.

```sql
CREATE TABLE IF NOT EXISTS books (
    book_key      TEXT PRIMARY KEY,       -- e.g. "goodfellow_deep_learning"
    book_title    TEXT NOT NULL,          -- e.g. "Deep Learning"
    author        TEXT,                   -- e.g. "Goodfellow, Bengio, Courville"
    total_pages   INTEGER,               -- Total PDF pages
    total_chunks  INTEGER,               -- Total chunks indexed
    indexed_at    TEXT DEFAULT (datetime('now'))
);
```

### 2.4 Query Patterns

**BM25 Search:**

```sql
SELECT c.*, bm25(chunks_fts) AS rank
FROM chunks_fts f
JOIN chunks c ON c.rowid = f.rowid
WHERE chunks_fts MATCH ?
ORDER BY rank
LIMIT ?;
```

**Metadata Filter Search:**

```sql
SELECT * FROM chunks
WHERE book_key IN (?, ?, ?)
  AND content_type = ?
  AND page_number BETWEEN ? AND ?
ORDER BY page_number;
```

**Book Listing:**

```sql
SELECT book_key, book_title, author, total_chunks
FROM books
ORDER BY book_title;
```

---

## 3. ChromaDB Collection (`chroma_db/`)

### 3.1 Collection Configuration

```python
collection_name = "textbook_chunks"
embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"   # 384-dimensional embeddings
)
distance_metric = "cosine"           # L2 is default; cosine preferred for text
```

### 3.2 Document Schema

```python
# Per chunk added to collection:
collection.add(
    ids=[chunk.chunk_id],
    documents=[chunk.text],
    metadatas=[{
        "book_key": chunk.book_key,
        "book_title": chunk.book_title,
        "chapter": chunk.chapter or "",
        "section": chunk.section or "",
        "page_number": chunk.page_number,
        "content_type": chunk.content_type,
        "bbox_json": json.dumps(chunk.bbox),
    }],
)
```

### 3.3 Query Pattern

```python
results = collection.query(
    query_texts=[question],
    n_results=top_k,
    where={                              # Optional metadata filters
        "$and": [
            {"book_key": {"$in": book_filter}},
            {"content_type": {"$in": type_filter}},
        ]
    } if filters else None,
)
```

---

## 4. PageIndex Trees (`pageindex_trees/`)

### 4.1 File Format

One JSON file per book: `pageindex_trees/{book_key}.json`

```json
{
  "book_key": "goodfellow_deep_learning",
  "book_title": "Deep Learning",
  "author": "Goodfellow, Bengio, Courville",
  "total_pages": 800,
  "tree": [
    {
      "title": "1 Introduction",
      "level": 1,
      "page_start": 1,
      "page_end": 28,
      "children": [
        {
          "title": "1.1 Who Should Read This Book?",
          "level": 2,
          "page_start": 8,
          "page_end": 10,
          "children": []
        },
        {
          "title": "1.2 Historical Trends in Deep Learning",
          "level": 2,
          "page_start": 11,
          "page_end": 28,
          "children": []
        }
      ]
    }
  ]
}
```

### 4.2 Tree Building Algorithm

```
Input: content_list.json (sorted by page_idx)
Output: Hierarchical tree

1. Filter items with text_level in (1, 2)
2. For each heading:
   a. If text_level == 1 → new top-level node
   b. If text_level == 2 → child of most recent level-1 node
3. Compute page_end for each node:
   a. page_end = page_start of next sibling - 1
   b. Last node: page_end = total_pages
```

---

## 5. Data Statistics (Expected)

| Metric                  | Expected Value                |
| ----------------------- | ----------------------------- |
| Total books             | 30–50                         |
| Total chunks            | ~50,000–100,000               |
| SQLite DB size          | ~50–100 MB                    |
| ChromaDB size           | ~200–500 MB (with embeddings) |
| PageIndex trees         | ~50 JSON files, ~5 MB total   |
| Average chunks per book | ~1,000–2,000                  |
| Average chunk length    | ~200–400 tokens               |

---

## 6. Data Integrity

### 6.1 Consistency Rules

- Every chunk in SQLite **must** also exist in ChromaDB (same `chunk_id`)
- Every book in `books` table must have a corresponding PageIndex tree JSON
- `page_number` in chunks must be within `[0, total_pages)` from the books table
- `bbox_json` must be a valid JSON array of 4 numbers `[x0, y0, x1, y1]`

### 6.2 Indexing Pipeline Validation

After indexing completes, verify:

```sql
-- Count mismatch check
SELECT b.book_key, b.total_chunks, COUNT(c.chunk_id) as actual_chunks
FROM books b
LEFT JOIN chunks c ON c.book_key = b.book_key
GROUP BY b.book_key
HAVING b.total_chunks != actual_chunks;
-- Should return 0 rows
```

```python
# ChromaDB count check
assert collection.count() == cursor.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
```
