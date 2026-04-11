"""Abstract base class for all retrieval strategies."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod

from engine.rag.config import QueryConfig
from engine.rag.types import StrategyResult


class RetrievalStrategy(ABC):
    """Base class for all retrieval strategies.

    Each strategy is self-contained:
    - Has its own data source (FTS5 table / ChromaDB / toc_entries / page_structure)
    - Receives the same QueryConfig as every other strategy
    - Returns a StrategyResult with its ranked hits
    - Strategies do NOT import or call each other

    Filters (book_ids, categories, content_types) are in QueryConfig.filters
    and each strategy applies them internally.
    """

    name: str           # machine identifier, e.g. "fts5_bm25"
    display_name: str   # human label, e.g. "FTS5 BM25"
    default_enabled: bool = True

    @abstractmethod
    def search(self, query: str, config: QueryConfig, db: sqlite3.Connection) -> StrategyResult:
        """Execute the search and return a StrategyResult.

        Args:
            query:  The user question string.
            config: Per-query config (top_k, fetch_k, filters, etc.).
            db:     SQLite connection (strategies that don't need it can ignore it).

        Returns:
            StrategyResult with hits ranked best-first.
        """
        ...

    def is_available(self) -> bool:
        """Return True if the strategy can execute (dependencies met).

        Override to check e.g. ChromaDB connection or ripgrep binary.
        Default: always available.
        """
        return True
