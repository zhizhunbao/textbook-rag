"""Pydantic schemas for the /query endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryFilters(BaseModel):
    book_ids: list[int] = Field(default_factory=list)
    chapter_ids: list[int] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    filters: QueryFilters | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    fetch_k: int | None = Field(default=None, ge=1, le=100, description="Over-fetch count; defaults to top_k * 3")
    model: str | None = Field(default=None, min_length=1, max_length=200)
    # STORY-007: strategy control
    enabled_strategies: list[str] | None = Field(default=None, description="Strategy names to enable; None → default set")
    rrf_k: int = Field(default=60, ge=1, le=200, description="RRF constant k")
    # STORY-011: generation config
    prompt_template: str = Field(default="default", description="Prompt template id: default/concise/detailed/academic")
    custom_system_prompt: str | None = Field(default=None, max_length=4000, description="Overrides prompt_template if set")


class SourceInfo(BaseModel):
    source_id: str
    book_id: int
    book_title: str
    chapter_title: str | None = None
    page_number: int
    snippet: str
    bbox: dict | None = None
    page_dim: dict | None = None
    confidence: float


class RetrievalStats(BaseModel):
    fts_hits: int
    vector_hits: int
    pageindex_hits: int = 0

    fused_count: int


class TraceChunkHit(BaseModel):
    strategy: str
    rank: int
    chunk_id: str
    book_title: str
    chapter_title: str | None = None
    page_number: int | None = None
    score: float | None = None
    snippet: str


class RetrievalTrace(BaseModel):
    fetch_k: int
    fts_query: str
    fts_results: list[TraceChunkHit]
    vector_results: list[TraceChunkHit]
    pageindex_results: list[TraceChunkHit] = Field(default_factory=list)

    fused_results: list[TraceChunkHit]


class CitationCleaningTrace(BaseModel):
    raw_answer: str
    cleaned_answer: str
    valid_citations: list[int]
    invalid_citations: list[int]
    total_found: int


class QualityWarning(BaseModel):
    level: str  # "warn" | "error"
    code: str
    message: str


class GenerationTrace(BaseModel):
    model: str
    system_prompt: str
    user_prompt: str
    citation_cleaning: CitationCleaningTrace | None = None


class QueryTrace(BaseModel):
    question: str
    top_k: int
    filters: QueryFilters | None = None
    active_book_title: str | None = None
    retrieval: RetrievalTrace
    generation: GenerationTrace


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    retrieval_stats: RetrievalStats
    trace: QueryTrace
    warnings: list[QualityWarning] = Field(default_factory=list)


class ModelInfo(BaseModel):
    name: str
    is_default: bool = False


class PromptTemplateInfo(BaseModel):
    id: str
    name: str
    description: str
