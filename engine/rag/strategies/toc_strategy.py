"""TOCHeadingStrategy — Table-of-Contents heading-overlap retrieval.

STORY-004: ported from retrieval_lab toc_retriever algorithm.
Algorithm:
  1. Tokenise the user query into lower-case terms.
  2. Score each toc_entry by:
     a. Term overlap ratio  (|query_terms ∩ heading_terms| / |query_terms|)
     b. Substring bonus      (+0.3 if the full query is a substring of the heading)
  3. Keep entries whose score ≥ SCORE_THRESHOLD.
  4. For each matching toc_entry, fetch the chunks whose primary_page_id falls
     on the same page (joined via pages.page_number).
  5. Rank chunks by toc_score (descending), then reading_order (ascending).
"""

from __future__ import annotations

import re
import sqlite3

from engine.rag.config import QueryConfig
from engine.rag.strategies.base import RetrievalStrategy
from engine.rag.types import ChunkHit, StrategyResult

# Minimum combined score to include a TOC match
_SCORE_THRESHOLD = 0.2
# Substring bonus added when the full (lowercased) query appears in the heading
_SUBSTRING_BONUS = 0.3


def _tokenise(text: str) -> set[str]:
    """Lower-case word tokenisation, stripping punctuation."""
    return set(re.findall(r"\b\w+\b", text.lower()))


def _score_heading(query_terms: set[str], heading: str, raw_query: str) -> float:
    """Compute relevance score for a single toc_entry heading."""
    if not query_terms:
        return 0.0
    heading_terms = _tokenise(heading)
    overlap = len(query_terms & heading_terms) / len(query_terms)
    bonus = _SUBSTRING_BONUS if raw_query.lower() in heading.lower() else 0.0
    return overlap + bonus


class TOCHeadingStrategy(RetrievalStrategy):
    """Table-of-Contents heading similarity retrieval.

    Queries the ``toc_entries`` table (populated by rebuild_db from MinerU
    ``_middle.json`` outline data).  Each matched heading yields the chunks
    whose primary_page_id corresponds to that heading's page.

    Filters: book_ids, categories (applied via JOIN).
    content_types / chapter_ids are applied post-hoc on chunk rows.
    """

    name: str = "toc_heading"
    display_name: str = "TOC Heading"
    default_enabled: bool = True

    def search(
        self,
        query: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> StrategyResult:
        query_terms = _tokenise(query)
        if not query_terms:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        fetch_k = config.effective_fetch_k
        f = config.filters

        # ── 1. Load candidate TOC entries ────────────────────────────────
        toc_where: list[str] = []
        toc_params: list[object] = []

        if f.book_ids:
            ph = ",".join("?" * len(f.book_ids))
            toc_where.append(f"t.book_id IN ({ph})")
            toc_params.extend(f.book_ids)

        if f.categories:
            ph = ",".join("?" * len(f.categories))
            toc_where.append(f"b.category IN ({ph})")
            toc_params.extend(f.categories)

        books_join = "LEFT JOIN books b ON b.id = t.book_id" if f.categories else ""
        where_sql = ("WHERE " + " AND ".join(toc_where)) if toc_where else ""

        toc_sql = (
            "SELECT t.id, t.book_id, t.page_id, t.title, t.level "
            "FROM toc_entries t "
            f"{books_join} "
            f"{where_sql}"
        )
        try:
            toc_rows = db.execute(toc_sql, toc_params).fetchall()
        except Exception as exc:  # noqa: BLE001
            return StrategyResult(
                strategy=self.name, hits=[], query_used=query, error=str(exc)
            )

        if not toc_rows:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        # ── 2. Score each TOC entry ───────────────────────────────────────
        scored: list[tuple[float, int, int]] = []  # (score, page_id, book_id)
        for row in toc_rows:
            score = _score_heading(query_terms, row["title"], query)
            if score >= _SCORE_THRESHOLD:
                scored.append((score, row["page_id"], row["book_id"]))

        if not scored:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        # Sort by score descending; keep top fetch_k pages
        scored.sort(key=lambda x: x[0], reverse=True)
        top_scored = scored[:fetch_k]
        page_ids = list({s[1] for s in top_scored})
        score_map: dict[int, float] = {}
        for sc, pid, _ in top_scored:
            score_map[pid] = max(score_map.get(pid, 0.0), sc)

        # ── 3. Fetch chunks whose primary_page_id is in matched pages ────
        ph = ",".join("?" * len(page_ids))
        chunk_where: list[str] = [f"c.primary_page_id IN ({ph})"]
        chunk_params: list[object] = [*page_ids]

        if f.content_types:
            content_ph = ",".join("?" * len(f.content_types))
            chunk_where.append(f"c.content_type IN ({content_ph})")
            chunk_params.extend(f.content_types)

        chunk_sql = (
            "SELECT c.id, c.chunk_id, c.book_id, c.chapter_id, c.primary_page_id,"
            "       c.content_type, c.text, c.reading_order, c.chroma_document_id "
            "FROM chunks c "
            "WHERE " + " AND ".join(chunk_where) + " "
            "ORDER BY c.reading_order ASC "
            f"LIMIT {fetch_k}"
        )
        try:
            chunk_rows = db.execute(chunk_sql, chunk_params).fetchall()
        except Exception as exc:  # noqa: BLE001
            return StrategyResult(
                strategy=self.name, hits=[], query_used=query, error=str(exc)
            )

        hits: list[ChunkHit] = []
        for rank, row in enumerate(chunk_rows, start=1):
            r = dict(row)
            toc_score = score_map.get(r["primary_page_id"], 0.0)
            hits.append(
                ChunkHit(
                    id=r["id"],
                    chunk_id=r["chunk_id"],
                    book_id=r["book_id"],
                    text=r["text"],
                    content_type=r.get("content_type", "text"),
                    reading_order=r.get("reading_order", 0),
                    chroma_document_id=r.get("chroma_document_id"),
                    toc_rank=rank,
                    toc_score=toc_score,
                )
            )

        # Re-sort by toc_score descending (chunks from highest-scoring page first)
        hits.sort(key=lambda h: (-(h.toc_score or 0.0), h.reading_order))
        for i, h in enumerate(hits, start=1):
            h.toc_rank = i

        return StrategyResult(strategy=self.name, hits=hits, query_used=query)
