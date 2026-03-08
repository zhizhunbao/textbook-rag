"""Query router — POST /api/v1/query."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.database import DB
from backend.app.repositories import book_repo
from backend.app.schemas.query import QueryRequest, QueryResponse
from backend.app.services import query_service

router = APIRouter(prefix="/api/v1", tags=["query"])


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
            db, req.question, filters=filters, top_k=req.top_k,
            active_book_title=book_title,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
