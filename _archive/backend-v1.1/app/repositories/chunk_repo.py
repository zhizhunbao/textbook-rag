"""Chunk repository — FTS5 full-text search and source-locator lookups."""

from __future__ import annotations

import sqlite3


def search_fts(
    db: sqlite3.Connection,
    query: str,
    *,
    filters: dict | None = None,
    limit: int = 10,
) -> list[dict]:
    """Run an FTS5 MATCH query and return ranked chunk rows.

    Each returned dict contains chunk columns plus ``rank`` (BM25 score).
    Filters may contain ``book_ids``, ``chapter_ids``, ``content_types``.
    """
    if not query or not query.strip():
        return []

    # Sanitise the user query for FTS5: remove special FTS operators
    safe_q = _sanitise_fts(query)
    if not safe_q:
        return []

    where_clauses: list[str] = []
    params: list[object] = []

    if filters:
        if filters.get("book_ids"):
            placeholders = ",".join("?" for _ in filters["book_ids"])
            where_clauses.append(f"c.book_id IN ({placeholders})")
            params.extend(filters["book_ids"])
        if filters.get("chapter_ids"):
            placeholders = ",".join("?" for _ in filters["chapter_ids"])
            where_clauses.append(f"c.chapter_id IN ({placeholders})")
            params.extend(filters["chapter_ids"])
        if filters.get("content_types"):
            placeholders = ",".join("?" for _ in filters["content_types"])
            where_clauses.append(f"c.content_type IN ({placeholders})")
            params.extend(filters["content_types"])

    where_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = (
        "SELECT c.id, c.chunk_id, c.book_id, c.chapter_id, c.primary_page_id, "
        "       c.content_type, c.text, c.reading_order, c.chroma_document_id, "
        "       fts.rank "
        "FROM chunk_fts AS fts "
        "JOIN chunks AS c ON c.id = fts.rowid "
        f"WHERE fts.chunk_fts MATCH ?{where_sql} "
        "ORDER BY fts.rank "
        "LIMIT ?"
    )
    params_all: list[object] = [safe_q, *params, limit]
    rows = db.execute(sql, params_all).fetchall()
    return [dict(r) for r in rows]


def get_source_locators(
    db: sqlite3.Connection,
    chunk_ids: list[int],
) -> list[dict]:
    """Return source_locator rows for the given chunk ids."""
    if not chunk_ids:
        return []
    placeholders = ",".join("?" for _ in chunk_ids)
    rows = db.execute(
        "SELECT sl.id, sl.chunk_id, sl.page_id, sl.locator_kind, "
        "       sl.x0, sl.y0, sl.x1, sl.y1, p.page_number "
        "FROM source_locators sl "
        "JOIN pages p ON p.id = sl.page_id "
        f"WHERE sl.chunk_id IN ({placeholders})",
        chunk_ids,
    ).fetchall()
    return [dict(r) for r in rows]


def get_chunks_by_chroma_ids(
    db: sqlite3.Connection,
    chroma_ids: list[str],
) -> list[dict]:
    """Look up chunks by their ChromaDB document ids."""
    if not chroma_ids:
        return []
    placeholders = ",".join("?" for _ in chroma_ids)
    rows = db.execute(
        "SELECT id, chunk_id, book_id, chapter_id, primary_page_id, "
        "       content_type, text, reading_order, chroma_document_id "
        f"FROM chunks WHERE chroma_document_id IN ({placeholders})",
        chroma_ids,
    ).fetchall()
    return [dict(r) for r in rows]


def _sanitise_fts(query: str) -> str:
    """Strip FTS5 special syntax from user input to prevent query errors."""
    import re

    # Keep only word characters (letters, digits, underscore) and whitespace
    cleaned = re.sub(r"[^\w\s]", " ", query)
    tokens = cleaned.split()
    if not tokens:
        return ""
    # Join with spaces — FTS5 implicit AND
    return " ".join(tokens)
