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


# Common English stopwords — stripped from long FTS queries to reduce
# overly restrictive implicit-AND matching
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "its",
    "they", "them", "their", "this", "that", "these", "those",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "about", "against", "and", "but", "or", "nor", "not", "no",
    "so", "if", "than", "too", "very", "just", "also", "more", "most",
    "some", "any", "each", "every", "all", "both", "few", "other",
    "such", "only", "own", "same", "then", "once", "here", "there",
    "again", "further", "regarding", "overall", "don", "t", "s",
    # Common question/navigation words — unlikely to match content
    "explain", "describe", "discuss", "emphasize", "emphasizes",
    "page", "chapter", "section", "paragraph", "figure", "table",
    "according", "based", "using", "used", "use",
})

# If after stopword removal fewer than this many tokens remain, fall back
# to the full (no-stopword-removal) query to avoid empty searches
_MIN_CONTENT_TOKENS = 2

# Maximum content tokens to keep — more than this makes implicit-AND too strict
_MAX_CONTENT_TOKENS = 5


def _sanitise_fts(query: str) -> str:
    """Strip FTS5 special syntax and remove stopwords from long queries.

    FTS5 treats space-separated tokens as implicit AND.  For short keyword
    queries (≤4 tokens) this works well, but natural-language questions with
    many tokens almost never match because every word must appear in a single
    chunk.  Removing stopwords keeps only content words, dramatically
    improving recall while preserving precision via BM25 ranking.
    """
    cleaned = re.sub(r"[^\w\s]", " ", query)
    tokens = cleaned.split()
    if not tokens:
        return ""

    # Short queries: keep as-is (implicit AND is fine)
    if len(tokens) <= 4:
        return " ".join(tokens)

    # Long queries: strip stopwords and bare numbers to keep content words only
    content = [
        t for t in tokens
        if t.lower() not in _STOPWORDS and not t.isdigit()
    ]
    if len(content) < _MIN_CONTENT_TOKENS:
        # Fallback: stopword removal was too aggressive
        return " ".join(tokens[:_MAX_CONTENT_TOKENS])

    # Cap to prevent over-constraining
    return " ".join(content[:_MAX_CONTENT_TOKENS])


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
        """Run FTS5 MATCH and return ranked ChunkHit list.

        Uses implicit AND first; if that returns 0 results, falls back to
        OR mode so that BM25 can still rank partial matches.
        """
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

        # --- Try implicit AND first ---
        rows = self._execute_fts(db, safe_q, books_join, extra_where, params, fetch_k)

        # --- Fallback: OR mode if AND returned nothing ---
        actual_query = safe_q
        tokens = safe_q.split()
        if not rows and len(tokens) > 1:
            or_query = " OR ".join(tokens)
            rows = self._execute_fts(db, or_query, books_join, extra_where, params, fetch_k)
            if rows:
                actual_query = or_query

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

        return StrategyResult(strategy=self.name, hits=hits, query_used=actual_query)

    @staticmethod
    def _execute_fts(
        db: sqlite3.Connection,
        match_expr: str,
        books_join: str,
        extra_where: str,
        params: list[object],
        limit: int,
    ) -> list:
        """Execute a single FTS5 query and return raw rows."""
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
        all_params: list[object] = [match_expr, *params, limit]
        try:
            return db.execute(sql, all_params).fetchall()
        except Exception:  # noqa: BLE001
            return []
