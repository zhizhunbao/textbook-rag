# Textbook RAG — 后端代码地图 (Backend Codemap)

## 文档信息

- 版本: 1.0
- 角色: Senior Backend Engineer
- 日期: 2026-03-07
- 输入: `docs/architecture/system-architecture.md`, `docs/sprints/sprint-plan.md`, `docs/codemaps/database.md`

---

## 1. 模块结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              ← FastAPI app 入口, CORS, lifespan
│   ├── config.py            ← Settings (env vars, paths)
│   ├── database.py          ← SQLite 连接管理 (get_db)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── books.py         ← GET /books, /books/{id}, /books/{id}/pdf
│   │   └── query.py         ← POST /query
│   ├── services/
│   │   ├── __init__.py
│   │   ├── query_service.py      ← 问答编排: retrieve → generate → assemble
│   │   ├── retrieval_service.py  ← 混合检索: FTS5 + ChromaDB → RRF
│   │   └── generation_service.py ← Ollama LLM 调用
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── book_repo.py     ← books / chapters / pages / book_assets CRUD
│   │   ├── chunk_repo.py    ← chunks + FTS5 + source_locators
│   │   └── vector_repo.py   ← ChromaDB 封装
│   └── schemas/
│       ├── __init__.py
│       ├── books.py          ← BookSummary, BookDetail, ChapterInfo
│       └── query.py          ← QueryRequest, QueryResponse, Source
└── tests/
    ├── __init__.py
    ├── conftest.py           ← fixtures: test db, test client
    ├── test_book_repo.py
    ├── test_chunk_repo.py
    ├── test_books_router.py
    └── test_query_router.py
```

---

## 2. Story → 模块映射

| Story | 模块 | 主要文件 |
|-------|------|----------|
| INFRA-001 | 骨架 | `main.py`, `config.py`, `database.py`, 所有 `__init__.py` |
| BE-001 | Book Repository | `repositories/book_repo.py` |
| BE-002 | Chunk Repository | `repositories/chunk_repo.py` |
| BE-003 | Vector Repository | `repositories/vector_repo.py` |
| BE-004 | Books Router | `routers/books.py`, `schemas/books.py` |
| BE-005 | Retrieval Service | `services/retrieval_service.py` |
| BE-006 | Generation Service | `services/generation_service.py` |
| BE-007 | Query Service | `services/query_service.py` |
| BE-008 | Query Router | `routers/query.py`, `schemas/query.py` |

---

## 3. 依赖流向

```
routers/books.py  ──→  repositories/book_repo.py  ──→  SQLite
routers/query.py  ──→  services/query_service.py
                         ├─→ services/retrieval_service.py
                         │     ├─→ repositories/chunk_repo.py  ──→  SQLite (FTS5)
                         │     └─→ repositories/vector_repo.py ──→  ChromaDB
                         └─→ services/generation_service.py    ──→  Ollama
```

所有层通过 FastAPI Depends() 注入，外层依赖内层。

---

## 4. 数据流

### 4.1 POST /api/v1/query

```
Request {question, filters?, top_k?}
  → QueryRouter.query()
    → QueryService.query(question, filters, top_k)
      → RetrievalService.retrieve(question, filters, top_k)
        → ChunkRepo.search_fts(question, filters, top_k*2)   → fts_results
        → VectorRepo.search(question, top_k*2, filters)       → vec_results
        → RRF fusion(fts_results, vec_results) → top_k ranked chunks
        → ChunkRepo.get_source_locators(chunk_ids) → source_locators
      → GenerationService.generate(question, context_chunks)
        → Ollama chat completion → answer_text
      → assemble QueryResponse {answer, sources[], retrieval_stats}
  → JSON Response
```

### 4.2 GET /api/v1/books

```
Request
  → BooksRouter.list_books()
    → BookRepo.list_books() → SELECT * FROM books ORDER BY title
  → JSON { books: BookSummary[] }
```

### 4.3 GET /api/v1/books/{book_id}

```
Request {book_id: int}
  → BooksRouter.get_book(book_id)
    → BookRepo.get_book(book_id) → book row + chapters
  → JSON BookDetail { ...book, chapters: ChapterInfo[] }
```

### 4.4 GET /api/v1/books/{book_id}/pdf

```
Request {book_id: int}
  → BooksRouter.get_pdf(book_id)
    → BookRepo.get_pdf_path(book_id) → file path from book_assets
  → FileResponse (application/pdf)
```

---

## 5. 关键接口定义

### 5.1 Schemas

```python
# schemas/query.py
class QueryFilters(BaseModel):
    book_ids: list[int] = []
    chapter_ids: list[int] = []
    content_types: list[str] = []

class QueryRequest(BaseModel):
    question: str  # min_length=1
    filters: QueryFilters | None = None
    top_k: int = 5  # ge=1, le=20

class SourceInfo(BaseModel):
    source_id: str
    book_id: int
    book_title: str
    chapter_title: str | None
    page_number: int
    snippet: str
    bbox: dict | None  # {x0, y0, x1, y1}
    confidence: float

class RetrievalStats(BaseModel):
    fts_hits: int
    vector_hits: int
    fused_count: int

class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    retrieval_stats: RetrievalStats

# schemas/books.py
class BookSummary(BaseModel):
    id: int
    book_id: str
    title: str
    authors: str
    page_count: int
    chapter_count: int
    chunk_count: int

class ChapterInfo(BaseModel):
    id: int
    chapter_key: str
    title: str

class BookDetail(BookSummary):
    chapters: list[ChapterInfo]
```

### 5.2 Repository 接口

```python
# BookRepo
list_books() -> list[dict]
get_book(book_id: int) -> dict | None
get_pdf_path(book_id: int) -> Path | None

# ChunkRepo
search_fts(query: str, filters: dict | None, limit: int) -> list[dict]
get_source_locators(chunk_ids: list[int]) -> list[dict]
get_chunks_by_chroma_ids(chroma_ids: list[str]) -> list[dict]

# VectorRepo
search(query_text: str, top_k: int, filters: dict | None) -> list[dict]
```

### 5.3 Service 接口

```python
# RetrievalService
retrieve(question: str, filters: dict | None, top_k: int) -> tuple[list[dict], RetrievalStats]

# GenerationService
generate(question: str, context_chunks: list[dict]) -> str

# QueryService
query(question: str, filters: dict | None, top_k: int) -> QueryResponse
```

---

## 6. 配置项 (config.py)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_PATH` | `data/textbook_rag.sqlite3` | SQLite 文件路径 |
| `CHROMA_PERSIST_DIR` | `data/chroma_persist` | ChromaDB 持久化目录 |
| `TEXTBOOKS_DIR` | `textbooks/` | PDF 文件目录 |
| `DATA_DIR` | `data/` | 数据根目录 |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `qwen2.5:7b` | 使用的 LLM 模型 |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers 模型 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 允许的前端来源 |
| `TOP_K_DEFAULT` | `5` | 默认检索数量 |

---

## 7. 教材依据

| 决策 | 教材 |
|------|------|
| Repository Pattern | Percival & Gregory, *Architecture Patterns with Python* Ch2 |
| Service Layer 编排 | Percival & Gregory, *Architecture Patterns with Python* Ch4 |
| Dependency Rule (外层→内层) | Martin, *Clean Architecture* Ch22 |
| 参数化 SQL 防注入 | Kreibich, *Using SQLite*; 安全最佳实践 |
| FTS5 BM25 检索 | Manning et al., *Introduction to IR*; Kreibich, *Using SQLite* |
| RRF 融合排序 | Manning et al., *Introduction to IR* — rank fusion |
| FastAPI 路由 + 依赖注入 | Lubanovic, *FastAPI: Modern Python Web Development* |
| Pydantic 请求/响应校验 | Lubanovic, *FastAPI* — data validation |
