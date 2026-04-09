"""query routes — Query endpoints (sync + SSE streaming).

Endpoints:
    POST   /engine/query          — synchronous RAG query with citation
    POST   /engine/query/stream   — SSE streaming RAG query with citation

Ref: llama_index — RetrieverQueryEngine, StreamingResponse
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from engine_v2.api.deps import get_engine
from engine_v2.query_engine.citation import get_query_engine, query as run_query
from engine_v2.schema import build_source
from engine_v2.settings import TOP_K
from loguru import logger

# ============================================================
# Router
# ============================================================
router = APIRouter(tags=["query"])


# ============================================================
# Request / Response models
# ============================================================
class QueryFilters(BaseModel):
    """Optional filters to narrow retrieval scope."""

    book_ids: list[int] = Field(default_factory=list)
    book_id_strings: list[str] = Field(default_factory=list)
    chapter_ids: list[int] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    """Unified query request — consumed by both sync and stream endpoints."""

    question: str
    top_k: int = TOP_K
    filters: QueryFilters = Field(default_factory=QueryFilters)
    model: str | None = None
    provider: str | None = None


# ============================================================
# Helpers — build trace dict from retriever + synthesizer data
# ============================================================
# _build_source removed — use shared build_source() from engine_v2.schema


def _build_trace(
    question: str,
    top_k: int,
    sources: list[dict[str, Any]],
    model: str | None = None,
) -> dict[str, Any]:
    """Build a trace object matching the frontend QueryTrace interface."""
    return {
        "retrieval": {
            "question": question,
            "top_k": top_k,
            "per_strategy": {},
        },
        "generation": {
            "model": model or "",
        },
    }


def _build_stats(sources: list[dict[str, Any]]) -> dict[str, int]:
    """Build retrieval stats from source list."""
    return {
        "source_count": len(sources),
        "fts_hits": 0,
        "vector_hits": 0,
        "toc_heading_hits": 0,
    }


# ============================================================
# POST /engine/query — synchronous
# ============================================================
@router.post("/query")
async def query(req: QueryRequest, engine=Depends(get_engine)):
    """Execute a RAG query with citation support.

    Flow:
        query_engine/ (RetrieverQueryEngine)
        ├── retrievers/ (BM25 + Vector → RRF, with MetadataFilters)
        ├── response_synthesizers/ (citation prompts)
        └── llms/ (Ollama or Azure OpenAI)
    """
    # Extract book scope from filters
    book_ids = req.filters.book_id_strings or []
    logger.info("Sync query: {} (top_k={}, books={})", req.question[:80], req.top_k, book_ids or "all")

    result = run_query(
        req.question,
        engine=engine if not book_ids else None,
        book_id_strings=book_ids or None,
    )

    return {
        "answer": result.answer,
        "sources": result.sources,
        "warnings": result.warnings,
        "stats": result.stats,
        "trace": _build_trace(
            question=req.question,
            top_k=req.top_k,
            sources=result.sources,
            model=req.model,
        ),
    }


# ============================================================
# POST /engine/query/stream — SSE streaming
# ============================================================
async def _stream_generator(req: QueryRequest):
    """Async generator that yields SSE events for streaming query.

    SSE event sequence:
        1. event: retrieval_done  — retrieval complete, sources available
        2. event: token           — each generated token
        3. event: done            — final response with full answer + sources + trace
    """
    try:
        # Extract book scope from filters
        book_ids = req.filters.book_id_strings or []

        # Build streaming engine with book scope filter
        streaming_engine = get_query_engine(
            similarity_top_k=req.top_k,
            streaming=True,
            book_id_strings=book_ids or None,
        )

        logger.info("Stream query: {} (top_k={}, books={})", req.question[:80], req.top_k, book_ids or "all")

        # Execute query with streaming enabled
        response = streaming_engine.query(req.question)

        # Extract sources from retrieved nodes
        sources = []
        for i, nws in enumerate(response.source_nodes, start=1):
            sources.append(build_source(nws, i))

        stats = _build_stats(sources)

        # Event 1: retrieval done — sources are already pre-deduped
        # by TextbookCitationQueryEngine._create_citation_nodes()
        yield _sse_event("retrieval_done", {"stats": stats, "sources": sources})

        # Event 2: stream tokens from the response generator
        full_answer = ""
        response_gen = response.response_gen
        if response_gen is not None:
            for token in response_gen:
                full_answer += token
                yield _sse_event("token", {"t": token})
        else:
            # Fallback: if response_gen is None, use the full response text
            full_answer = str(response)

        # Event 3: done — no post-hoc dedup needed
        # Source N labels are 1:1 with source_nodes (guaranteed by engine)
        trace = _build_trace(
            question=req.question,
            top_k=req.top_k,
            sources=sources,
            model=req.model,
        )

        yield _sse_event("done", {
            "answer": full_answer,
            "sources": sources,
            "stats": stats,
            "trace": trace,
        })

    except Exception as e:
        logger.exception("Stream query error: {}", e)
        yield _sse_event("error", {"message": str(e)})


def _sse_event(event: str, data: dict[str, Any]) -> str:
    """Format a single SSE event string."""
    json_str = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {json_str}\n\n"


@router.post("/query/stream")
async def query_stream(req: QueryRequest):
    """Execute a RAG query with SSE streaming response.

    Streams tokens as they are generated by the LLM, enabling
    real-time display in the frontend ChatPanel.

    SSE events:
        - retrieval_done: {stats, sources} — retrieval phase complete
        - token: {t} — single generated token
        - done: {answer, sources, stats, trace} — final result
        - error: {message} — on failure
    """
    return StreamingResponse(
        _stream_generator(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
