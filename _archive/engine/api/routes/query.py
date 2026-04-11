"""POST /engine/query — RAG query endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from engine.api.deps import get_rag_core
from engine.rag.config import QueryConfig, QueryFilters

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    fetch_k: int | None = None
    enabled_strategies: list[str] | None = None
    rrf_k: int = 60
    model: str | None = None
    provider: str | None = None  # v2.0: "ollama" | "azure_openai"
    prompt_template: str = "default"
    custom_system_prompt: str | None = None
    filters: dict | None = None


@router.post("/query")
def query(req: QueryRequest):
    """Execute RAG pipeline and return answer + sources + trace."""
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
    response = core.query(req.question, cfg)
    return {
        "answer": response.answer,
        "sources": response.sources,
        "trace": response.trace,
        "warnings": [{"level": w.level, "code": w.code, "message": w.message} for w in response.warnings],
        "stats": response.stats,
    }
