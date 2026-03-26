"""SirchmunkStrategy — Agentic search via Sirchmunk Python SDK.

Uses Sirchmunk's AgenticSearch to perform indexless retrieval on raw
MinerU markdown files. Results are mapped back to SQLite chunk_ids
for RRF fusion with other strategies.

Requires: pip install sirchmunk
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

from backend.app.core.config import QueryConfig, RAGConfig
from backend.app.core.strategies.base import RetrievalStrategy
from backend.app.core.types import ChunkHit, StrategyResult

logger = logging.getLogger(__name__)


class SirchmunkStrategy(RetrievalStrategy):
    """Sirchmunk AgenticSearch as a retrieval strategy.

    Searches raw MinerU markdown output files using Sirchmunk's
    ripgrep + Monte Carlo evidence sampling pipeline. Results are
    then mapped back to existing SQLite chunks by text overlap.
    """

    name: str = "sirchmunk"
    default_enabled: bool = False  # opt-in; requires sirchmunk + LLM

    def __init__(self, config: RAGConfig | None = None) -> None:
        self._config = config
        self._searcher = None
        self._mineru_dir: str | None = None

        if config and config.mineru_output_dir:
            self._mineru_dir = config.mineru_output_dir

    def is_available(self) -> bool:
        """Check if sirchmunk is installed and mineru output exists."""
        try:
            import sirchmunk  # noqa: F401
        except ImportError:
            logger.debug("sirchmunk not installed (pip install sirchmunk)")
            return False

        if not self._mineru_dir or not Path(self._mineru_dir).exists():
            logger.debug("mineru_output_dir not configured or does not exist")
            return False

        return True

    def _get_searcher(self):
        """Lazy-init the AgenticSearch instance."""
        if self._searcher is not None:
            return self._searcher

        from sirchmunk import AgenticSearch
        from sirchmunk.llm import OpenAIChat

        config = self._config or RAGConfig()
        llm = OpenAIChat(
            api_key="ollama",
            base_url=f"{config.ollama_base_url}/v1",
            model=config.default_model,
        )
        self._searcher = AgenticSearch(llm=llm)
        return self._searcher

    def search(
        self,
        question: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> StrategyResult:
        """Run Sirchmunk agentic search and map results to chunks."""
        if not question or not question.strip():
            return StrategyResult(strategy=self.name, hits=[], error=None)

        if not self.is_available():
            return StrategyResult(
                strategy=self.name,
                hits=[],
                error="sirchmunk not available",
            )

        try:
            searcher = self._get_searcher()

            # Collect markdown file paths to search
            search_paths = self._collect_search_paths(config)
            if not search_paths:
                return StrategyResult(strategy=self.name, hits=[], error=None)

            # Run async search in sync context
            result_text = asyncio.run(
                searcher.search(
                    query=question,
                    paths=search_paths,
                    mode="FAST",
                )
            )

            # Map sirchmunk text results back to chunk_ids
            hits = self._map_to_chunks(result_text, question, config, db)

            return StrategyResult(strategy=self.name, hits=hits, error=None)

        except Exception as e:  # noqa: BLE001
            logger.warning("Sirchmunk search failed: %s", e)
            return StrategyResult(
                strategy=self.name,
                hits=[],
                error=str(e),
            )

    def _collect_search_paths(self, config: QueryConfig) -> list[str]:
        """Build list of directories to search based on filters."""
        base = Path(self._mineru_dir)
        if not base.exists():
            return []

        # If category filter is set, search only those category dirs
        if config.filters and config.filters.categories:
            paths = []
            for cat in config.filters.categories:
                cat_dir = base / cat
                if cat_dir.exists():
                    paths.append(str(cat_dir))
            return paths if paths else [str(base)]

        return [str(base)]

    def _map_to_chunks(
        self,
        result_text: str,
        question: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> list[ChunkHit]:
        """Map Sirchmunk result text back to existing chunks.

        Strategy: find chunks whose text has the highest word overlap
        with the Sirchmunk result.
        """
        if not result_text or not result_text.strip():
            return []

        # Extract key phrases from the result
        result_words = set(result_text.lower().split())

        # Query chunks from DB
        fetch_k = config.effective_fetch_k
        filters = config.filters

        where_clauses = []
        params: list = []

        if filters and filters.book_ids:
            placeholders = ",".join("?" * len(filters.book_ids))
            where_clauses.append(f"c.book_id IN ({placeholders})")
            params.extend(filters.book_ids)

        if filters and filters.content_types:
            placeholders = ",".join("?" * len(filters.content_types))
            where_clauses.append(f"c.content_type IN ({placeholders})")
            params.extend(filters.content_types)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        rows = db.execute(
            f"""
            SELECT c.id, c.chunk_id, c.book_id, c.content_type, c.text
            FROM chunks c
            {where_sql}
            LIMIT ?
            """,
            [*params, fetch_k * 5],
        ).fetchall()

        # Score each chunk by word overlap with sirchmunk result
        scored = []
        for row in rows:
            chunk_text = row["text"] or ""
            chunk_words = set(chunk_text.lower().split())
            overlap = len(result_words & chunk_words)
            if overlap > 0:
                score = overlap / max(len(chunk_words), 1)
                scored.append((row, score))

        # Sort by overlap score, take top fetch_k
        scored.sort(key=lambda x: x[1], reverse=True)

        hits = []
        for rank, (row, score) in enumerate(scored[:fetch_k], start=1):
            hits.append(
                ChunkHit(
                    id=row["id"],
                    chunk_id=row["chunk_id"],
                    book_id=row["book_id"],
                    content_type=row["content_type"],
                    text=row["text"],
                    score=score,
                    rank=rank,
                    strategy=self.name,
                )
            )

        return hits
