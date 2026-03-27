"""POST /engine/sync-to-payload — Sync books from Engine SQLite to Payload CMS.

Reads all books from engine SQLite and creates/updates corresponding
Book records in Payload. This is a one-time recovery operation when
the Payload DB is rebuilt.
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter

from engine.config import DATABASE_PATH, PAYLOAD_URL, PAYLOAD_API_KEY

import httpx

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sync"])

_TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        h["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
    return h


def _category_from_book_id(book_id: str) -> str:
    """Infer category from engine book_id prefix."""
    if book_id.startswith("ed_update") or book_id.startswith("oreb_"):
        return "ecdev"
    # Add more rules as needed
    return "textbook"


@router.post("/sync-to-payload")
def sync_to_payload():
    """Sync all books from engine SQLite → Payload CMS."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT id, book_id, title, authors, page_count, chapter_count, chunk_count "
        "FROM books ORDER BY id"
    ).fetchall()
    conn.close()

    results = {"created": 0, "updated": 0, "errors": [], "total": len(rows)}

    for row in rows:
        book_data = {
            "engineBookId": row["book_id"],
            "title": row["title"],
            "authors": row["authors"] or "",
            "category": _category_from_book_id(row["book_id"]),
            "status": "indexed",
            "chunkCount": row["chunk_count"] or 0,
            "pipeline": {
                "chunked": "done",
                "stored": "done",
                "vector": "done",
                "fts": "done",
                "toc": "done",
            },
            "metadata": {
                "pageCount": row["page_count"] or 0,
                "chapterCount": row["chapter_count"] or 0,
            },
        }

        try:
            # Check if already exists in Payload
            check_url = (
                f"{PAYLOAD_URL}/api/books"
                f"?where[engineBookId][equals]={row['book_id']}&limit=1"
            )
            resp = httpx.get(check_url, headers=_headers(), timeout=_TIMEOUT)
            resp.raise_for_status()
            existing = resp.json()

            if existing.get("docs") and len(existing["docs"]) > 0:
                # Update existing
                doc_id = existing["docs"][0]["id"]
                resp = httpx.patch(
                    f"{PAYLOAD_URL}/api/books/{doc_id}",
                    json=book_data,
                    headers=_headers(),
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                results["updated"] += 1
            else:
                # Create new
                resp = httpx.post(
                    f"{PAYLOAD_URL}/api/books",
                    json=book_data,
                    headers=_headers(),
                    timeout=_TIMEOUT,
                )
                resp.raise_for_status()
                results["created"] += 1

        except Exception as e:
            msg = f"{row['book_id']}: {e}"
            logger.error("Sync failed: %s", msg)
            results["errors"].append(msg)

    return results
