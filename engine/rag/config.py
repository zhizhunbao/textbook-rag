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
# Prompt template
# Now handled via Payload CMS Seed; default behavior expects custom_system_prompt
# ---------------------------------------------------------------------------


@dataclass
class RAGConfig:
    """Global RAG Core configuration (set at startup)."""

    db_path: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen3.5:4b"
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = ""
    mineru_output_dir: str = ""


@dataclass
class QueryFilters:
    """Filters applied across all retrieval strategies (cross-cutting)."""

    book_ids: list[int] = field(default_factory=list)
    book_id_strings: list[str] = field(default_factory=list)
    chapter_ids: list[int] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    def resolve_book_ids(self, db) -> None:
        """Resolve book_id_strings (engine slug like 'krug_dont_make_me_think') to integer IDs.

        Called once before retrieval so strategies can use book_ids uniformly.
        """
        if not self.book_id_strings:
            return
        ph = ",".join("?" * len(self.book_id_strings))
        rows = db.execute(
            f"SELECT id FROM books WHERE book_id IN ({ph})",
            self.book_id_strings,
        ).fetchall()
        resolved = [r[0] if isinstance(r, (tuple, list)) else r["id"] for r in rows]
        # Merge with any existing book_ids
        existing = set(self.book_ids)
        for rid in resolved:
            if rid not in existing:
                self.book_ids.append(rid)
                existing.add(rid)

    def as_dict(self) -> dict:
        return {
            "book_ids": self.book_ids,
            "book_id_strings": self.book_id_strings,
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
    prompt_template: str = "default"
    custom_system_prompt: str | None = None  # main way to set system prompt
    active_book_title: str | None = None

    @property
    def effective_fetch_k(self) -> int:
        fk = self.fetch_k
        return fk if fk is not None else self.top_k * 3

    @property
    def effective_strategies(self) -> list[str]:
        es = self.enabled_strategies
        if es is not None:
            return es
        return DEFAULT_STRATEGIES
