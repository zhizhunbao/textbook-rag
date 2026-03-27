"""GET /engine/chunks — sample chunks for pipeline preview.

Returns a sample of chunks from the Engine SQLite database for a given book.
Used by the Payload pipeline-preview API to show stage input/output data.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Query

from engine.config import DATABASE_PATH

router = APIRouter(tags=["chunks"])


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/query/chunks")
def sample_chunks(
    book_id: str = Query(..., description="Engine book_id string"),
    limit: int = Query(3, ge=1, le=50, description="Max chunks to return"),
):
    """Return a small sample of chunks for preview purposes.

    Used by pipeline-preview to show what data each stage produces.
    """
    conn = _get_db()

    rows = conn.execute(
        "SELECT c.chunk_id, c.content_type, c.text, c.reading_order "
        "FROM chunks c "
        "JOIN books b ON c.book_id = b.id "
        "WHERE b.book_id = ? "
        "ORDER BY c.reading_order "
        "LIMIT ?",
        (book_id, limit),
    ).fetchall()
    conn.close()

    return [
        {
            "chunk_id": r["chunk_id"],
            "content_type": r["content_type"],
            "text": r["text"],
            "reading_order": r["reading_order"],
        }
        for r in rows
    ]
