"""FTS5BM25Strategy — full-text keyword search via SQLite FTS5.

STORY-002: extracted from retrieval_service.py and chunk_repo.search_fts().
Returns hits ranked by BM25 score (lower rank column = better match).
"""

from __future__ import annotations

import re
import sqlite3

from engine.rag.config import QueryConfig
from engine.rag.strategies.base import RetrievalStrategy
from engine.rag.types import ChunkHit, StrategyResult


def _sanitise_fts(query: str) -> str:
    """Strip FTS5 special syntax from user input to prevent query errors."""
    cleaned = re.sub(r"[^\w\s]", " ", query)
    tokens = cleaned.split()
    return " ".join(tokens) if tokens else ""


class FTS5BM25Strategy(RetrievalStrategy):
    """SQLite FTS5 BM25 keyword retrieval strategy.

    Uses the ``chunk_fts`` virtual table.  The FTS5 ``rank`` column is a
    negative BM25 score (more negative = higher relevance), so ORDER BY rank
    returns best matches first.

    Filters applied: book_ids, chapter_ids, content_types, categories.
    """

    name: str = "fts5_bm25"
    display_name: str = "FTS5 BM25"
    default_enabled: bool = True

    def search(
        self,
        query: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> StrategyResult:
        """Run FTS5 MATCH and return ranked ChunkHit list."""
        safe_q = _sanitise_fts(query)
        if not safe_q:
            return StrategyResult(strategy=self.name, hits=[], query_used="")

        fetch_k = config.effective_fetch_k
        f = config.filters

        where_clauses: list[str] = []
        params: list[object] = []

        if f.book_ids:
            ph = ",".join("?" * len(f.book_ids))
            where_clauses.append(f"c.book_id IN ({ph})")
            params.extend(f.book_ids)
        if f.chapter_ids:
            ph = ",".join("?" * len(f.chapter_ids))
            where_clauses.append(f"c.chapter_id IN ({ph})")
            params.extend(f.chapter_ids)
        if f.content_types:
            ph = ",".join("?" * len(f.content_types))
            where_clauses.append(f"c.content_type IN ({ph})")
            params.extend(f.content_types)
        if f.categories:
            ph = ",".join("?" * len(f.categories))
            where_clauses.append(f"b.category IN ({ph})")
            params.extend(f.categories)

        extra_where = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

        # category filter requires JOIN books
        books_join = (
            "LEFT JOIN books b ON b.id = c.book_id" if f.categories else ""
        )

        sql = (
            "SELECT c.id, c.chunk_id, c.book_id, c.chapter_id, c.primary_page_id,"
            "       c.content_type, c.text, c.reading_order, c.chroma_document_id,"
            "       fts.rank "
            "FROM chunk_fts AS fts "
            "JOIN chunks AS c ON c.id = fts.rowid "
            f"{books_join} "
            f"WHERE fts.chunk_fts MATCH ?{extra_where} "
            "ORDER BY fts.rank "
            "LIMIT ?"
        )
        all_params: list[object] = [safe_q, *params, fetch_k]

        try:
            rows = db.execute(sql, all_params).fetchall()
        except Exception as exc:  # noqa: BLE001
            return StrategyResult(
                strategy=self.name, hits=[], query_used=safe_q,
                error=str(exc),
            )

        hits = []
        for rank, row in enumerate(rows, start=1):
            r = dict(row)
            fts_score = -float(r["rank"]) if r.get("rank") is not None else None
            hits.append(
                ChunkHit(
                    id=r["id"],
                    chunk_id=r["chunk_id"],
                    book_id=r["book_id"],
                    text=r["text"],
                    content_type=r.get("content_type", "text"),
                    reading_order=r.get("reading_order", 0),
                    chroma_document_id=r.get("chroma_document_id"),
                    fts_rank=rank,
                    fts_score=fts_score,
                )
            )

        return StrategyResult(strategy=self.name, hits=hits, query_used=safe_q)
