# Backend Codemap v1.1

> sprint-plan.md → 后端实现的模块边界、文件、接口和数据流

## 模块映射

| Story | 文件 | 接口 |
|-------|------|------|
| STORY-001 | `core/config.py` | `RAGConfig`, `QueryConfig` |
| STORY-001 | `core/types.py` | `ChunkHit`, `RetrievalResult`, `RAGResponse` |
| STORY-001 | `core/strategies/base.py` | `RetrievalStrategy` ABC |
| STORY-001 | `core/strategies/registry.py` | `StrategyRegistry` |
| STORY-001 | `core/rag_core.py` | `RAGCore.query()` |
| STORY-002 | `core/strategies/fts5_strategy.py` | `FTS5BM25Strategy` |
| STORY-003 | `core/strategies/vector_strategy.py` | `VectorStrategy` |
| STORY-004 | `core/strategies/toc_strategy.py` | `TOCHeadingStrategy` |
| STORY-005 | `core/strategies/pageindex_strategy.py` | `PageIndexStrategy` |
| STORY-007 | `core/retrieval.py` | `RetrievalOrchestrator` |
| STORY-007 | `core/fusion.py` | `RRFusion.fuse()` |
| STORY-008 | `core/citation.py` | `CitationEngine` |
| STORY-009 | `core/trace.py` | `TraceCollector` |
| STORY-009 | `core/quality.py` | `QualityChecker` |
| STORY-011 | `core/generation.py` | `GenerationEngine` |

## 数据流

```
QueryRequest (API)
    │
    ▼
RAGCore.query(question, config)
    │
    ├─→ RetrievalOrchestrator.retrieve()
    │       ├─→ [enabled strategies].search(query, config) → list[ChunkHit]
    │       └─→ RRFusion.fuse(results) → list[ChunkHit]
    │
    ├─→ GenerationEngine.generate(question, chunks, config) → raw_answer
    │
    ├─→ CitationEngine.process(raw_answer, chunks)
    │       ├─→ validate() → valid/invalid lists
    │       ├─→ sanitize() → cleaned_answer
    │       └─→ map_to_sources() → list[SourceInfo]
    │
    ├─→ QualityChecker.check(retrieval_result, citation_result) → list[QualityWarning]
    │
    └─→ TraceCollector.get_trace() → QueryTrace
```

## v1.0 → v1.1 委托关系

```
routers/query.py  →  services/query_service.py  →  core/rag_core.py
                                                        ↓
                                                  (all core logic)
```

`services/` 保留但变为 thin wrappers，不做任何业务逻辑。
