"""Query service — delegates to RAGCore for the full RAG pipeline.

STORY-001 T-001.5: query_service now acts as a thin adapter between the
FastAPI layer (dict-based I/O) and the RAGCore OOP layer.

All strategy selection, RRF fusion, citation processing, and quality
checking happen inside RAGCore.  This module converts the result back
to the legacy QueryResponse schema so existing tests and frontend remain
compatible.
"""

from __future__ import annotations

import sqlite3

from backend.app.config import (
    CHROMA_PERSIST_DIR,
    DATABASE_PATH,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from backend.app.core.config import QueryConfig, QueryFilters, RAGConfig
from backend.app.core.rag_core import RAGCore
from backend.app.schemas.query import (
    GenerationTrace,
    QueryFilters as SchemaQueryFilters,
    QueryResponse,
    QueryTrace,
    RetrievalStats,
    RetrievalTrace,
    SourceInfo,
    TraceChunkHit,
    QualityWarning as SchemaQualityWarning,
    CitationCleaningTrace,
)

# ── Singleton RAGCore (initialised lazily on first query) ──────────────────
_rag_core: RAGCore | None = None


def _get_rag_core() -> RAGCore:
    global _rag_core
    if _rag_core is None:
        rag_cfg = RAGConfig(
            db_path=str(DATABASE_PATH),
            ollama_base_url=OLLAMA_BASE_URL,
            default_model=OLLAMA_MODEL,
            chroma_persist_dir=str(CHROMA_PERSIST_DIR),
        )
        _rag_core = RAGCore(db_path=str(DATABASE_PATH), config=rag_cfg)
    return _rag_core


# ── Public query function ──────────────────────────────────────────────────

def query(
    db: sqlite3.Connection,
    question: str,
    filters: dict | None = None,
    top_k: int = 5,
    fetch_k: int | None = None,
    active_book_title: str | None = None,
    model: str | None = None,
    enabled_strategies: list[str] | None = None,
    rrf_k: int = 60,
    prompt_template: str = "default",
    custom_system_prompt: str | None = None,
) -> QueryResponse:
    """Full RAG pipeline via RAGCore, returns legacy QueryResponse schema."""

    # Build QueryFilters from raw dict
    qf = QueryFilters()
    if filters:
        qf.book_ids = filters.get("book_ids", [])
        qf.chapter_ids = filters.get("chapter_ids", [])
        qf.content_types = filters.get("content_types", [])
        qf.categories = filters.get("categories", [])

    cfg = QueryConfig(
        top_k=top_k,
        fetch_k=fetch_k,
        filters=qf,
        model=model,
        enabled_strategies=enabled_strategies,
        rrf_k=rrf_k,
        prompt_template=prompt_template,
        custom_system_prompt=custom_system_prompt,
        active_book_title=active_book_title,
    )

    core = _get_rag_core()
    rag_response = core.query(question, cfg)

    # ── Convert RAGResponse → QueryResponse (legacy schema) ───────────────
    sources = _build_sources(rag_response.sources)
    retrieval_stats = _build_stats(rag_response.stats)
    trace = _build_trace(question, top_k, filters, active_book_title, rag_response.trace)
    warnings = [
        SchemaQualityWarning(level=w.level, code=w.code, message=w.message)
        for w in rag_response.warnings
    ]

    return QueryResponse(
        answer=rag_response.answer,
        sources=sources,
        retrieval_stats=retrieval_stats,
        trace=trace,
        warnings=warnings,
    )


# ── Schema conversion helpers ──────────────────────────────────────────────

def _build_sources(raw_sources: list[dict]) -> list[SourceInfo]:
    result = []
    for s in raw_sources:
        bbox = s.get("bbox")
        result.append(SourceInfo(
            source_id=s.get("chunk_id", ""),
            book_id=0,  # not in CitationResult sources directly
            book_title=s.get("book_title", ""),
            chapter_title=s.get("chapter_title"),
            page_number=s.get("page_number") or 0,
            snippet=s.get("snippet", ""),
            bbox=bbox,
            confidence=1.0,
        ))
    return result


def _build_stats(stats: dict) -> RetrievalStats:
    return RetrievalStats(
        fts_hits=stats.get("fts5_bm25_hits", stats.get("fts_hits", 0)),
        vector_hits=stats.get("vector_hits", 0),
        pageindex_hits=stats.get("pageindex_hits", 0),

        fused_count=stats.get("total_hits", stats.get("fused_count", 0)),
    )


def _build_trace(
    question: str,
    top_k: int,
    filters: dict | None,
    active_book_title: str | None,
    raw_trace: dict,
) -> QueryTrace:
    ret = raw_trace.get("retrieval", {})
    gen = raw_trace.get("generation", {})
    cit = raw_trace.get("citations", {})

    # Per-strategy hits → TraceChunkHit lists
    per_strategy = ret.get("per_strategy", {})

    def _to_hits(name: str) -> list[TraceChunkHit]:
        return [
            TraceChunkHit(
                strategy=name,
                rank=h.get("rank", 0),
                chunk_id=h.get("chunk_id", ""),
                book_title=h.get("book_title", ""),
                chapter_title=h.get("chapter_title"),
                page_number=h.get("page_number"),
                score=h.get("score"),
                snippet=h.get("snippet", ""),
            )
            for h in per_strategy.get(name, {}).get("hits", [])
        ]

    schema_filters = None
    if filters:
        schema_filters = SchemaQueryFilters(**{
            k: filters.get(k, [])
            for k in ("book_ids", "chapter_ids", "content_types", "categories")
        })

    citation_cleaning = CitationCleaningTrace(
        raw_answer="",
        cleaned_answer="",
        valid_citations=cit.get("valid", []),
        invalid_citations=cit.get("invalid", []),
        total_found=len(cit.get("valid", [])) + len(cit.get("invalid", [])),
    )

    return QueryTrace(
        question=question,
        top_k=top_k,
        filters=schema_filters,
        active_book_title=active_book_title,
        retrieval=RetrievalTrace(
            fetch_k=ret.get("fetch_k", top_k * 3),
            fts_query=per_strategy.get("fts5_bm25", {}).get("query_used", question),
            fts_results=_to_hits("fts5_bm25"),
            vector_results=_to_hits("vector"),
            pageindex_results=_to_hits("pageindex"),

            fused_results=[],  # fused list not tracked per-hit in trace
        ),
        generation=GenerationTrace(
            model=gen.get("model") or "",
            system_prompt=gen.get("prompt_template", ""),
            user_prompt=question,
            citation_cleaning=citation_cleaning,
        ),
    )
