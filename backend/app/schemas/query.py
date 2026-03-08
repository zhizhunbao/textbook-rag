"""Pydantic schemas for the /query endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryFilters(BaseModel):
    book_ids: list[int] = Field(default_factory=list)
    chapter_ids: list[int] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    filters: QueryFilters | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SourceInfo(BaseModel):
    source_id: str
    book_id: int
    book_title: str
    chapter_title: str | None = None
    page_number: int
    snippet: str
    bbox: dict | None = None
    confidence: float


class RetrievalStats(BaseModel):
    fts_hits: int
    vector_hits: int
    fused_count: int


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    retrieval_stats: RetrievalStats
