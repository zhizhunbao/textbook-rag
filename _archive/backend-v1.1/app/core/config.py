"""RAG Core configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Strategy names (used as identifiers in enabled_strategies list)
# ---------------------------------------------------------------------------
STRATEGY_FTS5 = "fts5_bm25"
STRATEGY_VECTOR = "vector"
STRATEGY_TOC = "toc_heading"
STRATEGY_PAGEINDEX = "pageindex"
STRATEGY_SIRCHMUNK = "sirchmunk"


ALL_STRATEGIES = [
    STRATEGY_FTS5,
    STRATEGY_VECTOR,
    STRATEGY_TOC,
    STRATEGY_PAGEINDEX,
    STRATEGY_SIRCHMUNK,
]
DEFAULT_STRATEGIES = [STRATEGY_FTS5, STRATEGY_VECTOR, STRATEGY_TOC]

# ---------------------------------------------------------------------------
# Prompt template IDs
# ---------------------------------------------------------------------------
PROMPT_DEFAULT = "default"
PROMPT_CONCISE = "concise"
PROMPT_DETAILED = "detailed"
PROMPT_ACADEMIC = "academic"


@dataclass
class RAGConfig:
    """Global RAG Core configuration (set at startup)."""

    db_path: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    default_model: str = "llama3.2:3b"
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = ""
    mineru_output_dir: str = ""


@dataclass
class QueryFilters:
    """Filters applied across all retrieval strategies (cross-cutting)."""

    book_ids: list[int] = field(default_factory=list)
    chapter_ids: list[int] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "book_ids": self.book_ids,
            "chapter_ids": self.chapter_ids,
            "content_types": self.content_types,
            "categories": self.categories,
        }


@dataclass
class QueryConfig:
    """Per-query configuration — all fields have v1.0-compatible defaults."""

    top_k: int = 5
    fetch_k: int | None = None  # None → auto (top_k * 3)
    enabled_strategies: list[str] | None = None  # None → DEFAULT_STRATEGIES
    rrf_k: int = 60
    filters: QueryFilters = field(default_factory=QueryFilters)
    model: str | None = None  # None → RAGConfig.default_model
    prompt_template: str = PROMPT_DEFAULT
    custom_system_prompt: str | None = None  # overrides template if set
    active_book_title: str | None = None

    @property
    def effective_fetch_k(self) -> int:
        return self.fetch_k if self.fetch_k is not None else self.top_k * 3

    @property
    def effective_strategies(self) -> list[str]:
        return self.enabled_strategies if self.enabled_strategies is not None else DEFAULT_STRATEGIES
