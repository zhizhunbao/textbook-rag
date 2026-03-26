"""Query router — POST /api/v1/query + /prompt-templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.database import DB
from backend.app.repositories import book_repo
from backend.app.schemas.query import (
    ModelInfo,
    PromptTemplateInfo,
    QueryRequest,
    QueryResponse,
)
from backend.app.services import generation_service, query_service

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.get("/models", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    try:
        return generation_service.list_available_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/prompt-templates", response_model=list[PromptTemplateInfo])
def list_prompt_templates() -> list[PromptTemplateInfo]:
    """Return available built-in prompt templates (STORY-011)."""
    from backend.app.core.generation import GenerationEngine
    return [PromptTemplateInfo(**t) for t in GenerationEngine.list_templates()]


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, db: DB) -> QueryResponse:
    filters = None
    if req.filters:
        filters = req.filters.model_dump(exclude_none=True)
        # Remove empty lists so downstream code treats them as "no filter"
        filters = {k: v for k, v in filters.items() if v}

    # Resolve selected book title for the generation prompt
    book_title: str | None = None
    if filters and filters.get("book_ids") and len(filters["book_ids"]) == 1:
        book = book_repo.get_book(db, filters["book_ids"][0])
        if book:
            book_title = book["title"]

    try:
        return query_service.query(
            db,
            req.question,
            filters=filters,
            top_k=req.top_k,
            fetch_k=req.fetch_k,
            active_book_title=book_title,
            model=req.model,
            enabled_strategies=req.enabled_strategies,
            rrf_k=req.rrf_k,
            prompt_template=req.prompt_template,
            custom_system_prompt=req.custom_system_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
