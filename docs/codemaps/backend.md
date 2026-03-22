# Textbook RAG v2.0 — Engine Backend Codemap

> **版本**: 2.0 | **日期**: 2026-03-22
> **输入**: system-architecture.md, database.md, sprint-plan.md

---

## 1. 模块总览

```
engine/                          # 独立 Python 包 (uv)
├── pyproject.toml              # 包配置 + 依赖
├── engine/
│   ├── __init__.py
│   ├── config.py               # EngineSettings (统一配置)
│   │
│   ├── rag/                    # === v1.1 Core 平移 + Azure 扩展 ===
│   │   ├── __init__.py         # 导出 RAGCore
│   │   ├── core.py             # ← backend/app/core/rag_core.py
│   │   ├── retrieval.py        # ← backend/app/core/retrieval.py
│   │   ├── generation.py       # ← backend/app/core/generation.py (+ Provider 模式)
│   │   ├── citation.py         # ← backend/app/core/citation.py
│   │   ├── quality.py          # ← backend/app/core/quality.py
│   │   ├── fusion.py           # ← backend/app/core/fusion.py
│   │   ├── trace.py            # ← backend/app/core/trace.py
│   │   ├── config.py           # ← backend/app/core/config.py
│   │   ├── types.py            # ← backend/app/core/types.py
│   │   ├── strategies/
│   │   │   ├── __init__.py     # ← backend/app/core/strategies/__init__.py
│   │   │   ├── base.py         # ← backend/app/core/strategies/base.py
│   │   │   ├── registry.py     # ← backend/app/core/strategies/registry.py
│   │   │   ├── fts5_strategy.py
│   │   │   ├── vector_strategy.py
│   │   │   ├── toc_strategy.py
│   │   │   ├── pageindex_strategy.py
│   │   │   ├── sirchmunk_strategy.py
│   │   │   └── azure_search.py      # NEW
│   │   └── providers/               # NEW: LLM Provider 抽象
│   │       ├── __init__.py
│   │       ├── base.py              # LLMProvider ABC
│   │       ├── ollama.py            # 提取自 generation.py
│   │       └── azure_openai.py      # NEW
│   │
│   ├── ingest/                 # === scripts/ 拆分 ===
│   │   ├── __init__.py
│   │   ├── pipeline.py         # IngestPipeline 编排器
│   │   ├── pdf_parser.py       # ← scripts/batch_mineru.py
│   │   ├── chunk_builder.py    # ← scripts/rebuild_db.py (核心拆分)
│   │   ├── toc_extractor.py    # ← scripts/rebuild_toc.py
│   │   └── metadata_enricher.py # ← scripts/rebuild_db.py (元数据部分)
│   │
│   ├── index/                  # === scripts/ 拆分 ===
│   │   ├── __init__.py
│   │   ├── vector_builder.py   # ← scripts/build_vectors.py
│   │   ├── fts5_builder.py     # ← scripts/rebuild_db.py (FTS5 部分)
│   │   └── topic_indexer.py    # ← scripts/rebuild_topic_index.py
│   │
│   ├── api/                    # Thin FastAPI (内部)
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI app 创建
│   │   ├── deps.py             # 依赖注入 (RAGCore, DB, etc.)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── query.py        # POST /engine/query
│   │       ├── ingest.py       # POST /engine/ingest
│   │       └── health.py       # GET /engine/health + strategies + models
│   │
│   └── adapters/               # 外部适配器
│       ├── __init__.py
│       ├── payload_client.py   # 调 Payload REST API
│       ├── chroma_adapter.py   # ChromaDB 连接
│       └── azure_blob.py       # Azure Blob Storage (可选)
│
└── tests/
    ├── conftest.py
    ├── test_rag/               # v1.1 测试平移
    ├── test_ingest/
    ├── test_index/
    └── test_api/
```

## 2. Sprint Story → 模块映射

| Story | 目标模块 | 操作 | 关键文件 |
|-------|---------|------|---------|
| P4-01 | engine/ 根 | 新建骨架 | pyproject.toml, __init__.py |
| P4-08 | engine/config.py | 新建 | config.py |
| P4-02 | engine/rag/ | 平移 | 全部 core 文件 |
| P4-07 | engine/adapters/ | 重构 | chroma_adapter.py |
| P4-03 | engine/ingest/ | 拆分 | rebuild_db.py → 4 模块 |
| P4-04 | engine/index/ | 拆分 | 3 scripts → 3 模块 |
| P4-05 | engine/api/ | 新建 | app.py, routes/* |
| P4-06 | engine/adapters/ | 新建 | payload_client.py |
| P4-09 | engine/tests/ | 平移 | v1.1 测试 |
| A2-01 | engine/rag/generation.py | 重构 | Provider 模式 |
| A2-02 | engine/rag/providers/ | 提取 | ollama.py |
| A2-03 | engine/rag/providers/ | 新建 | azure_openai.py |
| A1-01 | engine/rag/strategies/ | 新建 | azure_search.py |

## 3. 开发顺序

```
Phase A: 骨架 (P4-01 + P4-08)
  └─→ Phase B: RAG Core 平移 (P4-02)
       ├─→ Phase C: 策略 + Provider (A1-01, A2-01..03)
       └─→ Phase D: ingest/index 拆分 (P4-03, P4-04)
            └─→ Phase E: API + Adapter (P4-05, P4-06, P4-07)
                 └─→ Phase F: 测试验证 (P4-09)
```

## 4. 关键数据流

### 4.1 查询流

```
Payload custom EP → POST /engine/query
  → api/routes/query.py
  → deps.get_rag_core()
  → RAGCore.query(question, config)
    → RetrievalOrchestrator.retrieve()
      → [FTS5, Vector, TOC, PageIndex, Sirchmunk, AzureSearch]
      → RRFusion.fuse()
    → GenerationEngine.generate()
      → providers[config.provider].generate()
    → CitationEngine.validate()
    → QualityChecker.check()
    → TraceCollector.build()
  → Return RAGResponse
```

### 4.2 入库流

```
Payload hook → POST /engine/ingest
  → api/routes/ingest.py
  → IngestPipeline.run(book_id, file_url, task_id)
    → pdf_parser.parse(file_url) → MinerU output
    → chunk_builder.build(mineru_output) → chunks[]
    → toc_extractor.extract(mineru_output) → toc_entries[]
    → metadata_enricher.enrich(chunks) → enriched chunks[]
    → payload_client.batch_create_chunks(chunks)
    → vector_builder.build(chunks) → ChromaDB
    → fts5_builder.build(chunks) → Engine SQLite
    → payload_client.update_book_status(book_id, "indexed")
    → payload_client.update_task(task_id, status="done")
```

## 5. v1.1 文件到 import 路径变更

| v1.1 import | v2.0 import |
|-------------|-------------|
| `backend.app.core.rag_core.RAGCore` | `engine.rag.core.RAGCore` |
| `backend.app.core.retrieval.RetrievalOrchestrator` | `engine.rag.retrieval.RetrievalOrchestrator` |
| `backend.app.core.generation.GenerationEngine` | `engine.rag.generation.GenerationEngine` |
| `backend.app.core.strategies.base.RetrievalStrategy` | `engine.rag.strategies.base.RetrievalStrategy` |
| `backend.app.core.types.ChunkHit` | `engine.rag.types.ChunkHit` |
| `backend.app.core.config.RAGConfig` | `engine.rag.config.RAGConfig` |
| `backend.app.config.Settings` | `engine.config.EngineSettings` |
