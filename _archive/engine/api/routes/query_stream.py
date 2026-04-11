"""POST /engine/query/stream — SSE streaming RAG query endpoint.

Returns Server-Sent Events following the Coze HTTP-chunk pattern:
  event: retrieval_done → {"stats": ..., "chunk_count": N}
  event: token          → {"t": "..."}
  event: done           → {"answer": ..., "sources": [...], "trace": ..., ...}
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from engine.api.deps import get_rag_core
from engine.rag.config import QueryConfig, QueryFilters

router = APIRouter(tags=["query"])


class StreamQueryRequest(BaseModel):
    question: str
    top_k: int = 5
    fetch_k: int | None = None
    enabled_strategies: list[str] | None = None
    rrf_k: int = 60
    model: str | None = None
    provider: str | None = None
    prompt_template: str = "default"
    custom_system_prompt: str | None = None
    filters: dict | None = None


@router.post("/query/stream")
def query_stream(req: StreamQueryRequest):
    """Execute RAG pipeline and stream answer tokens via SSE."""
    filters = QueryFilters(**(req.filters or {}))
    cfg = QueryConfig(
        top_k=req.top_k,
        fetch_k=req.fetch_k,
        enabled_strategies=req.enabled_strategies,
        rrf_k=req.rrf_k,
        filters=filters,
        model=req.model,
        provider=req.provider,
        prompt_template=req.prompt_template,
        custom_system_prompt=req.custom_system_prompt,
    )
    core = get_rag_core()

    def event_generator():
        for event in core.query_stream(req.question, cfg):
            evt = event["event"]
            data = json.dumps(event["data"], ensure_ascii=False)
            yield f"event: {evt}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
