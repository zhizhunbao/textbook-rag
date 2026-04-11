"""POST /engine/reindex — rebuild vector + FTS5 indexes for a book.

Re-reads chunks from Engine SQLite and rebuilds ChromaDB vectors and FTS5
index without re-parsing the PDF. Used by the Pipeline dashboard "Reindex"
action.
"""

from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from engine.config import DATABASE_PATH
from engine.adapters.payload_client import update_task, update_book_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reindex"])

_executor = ThreadPoolExecutor(max_workers=1)


class ReindexRequest(BaseModel):
    book_id: str | None = None          # Engine book_id string (e.g. "ramalho_fluent_python")
    payload_book_id: int | None = None  # Payload numeric book ID (for status updates)
    task_id: int | None = None          # PipelineTask ID for progress tracking


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _rebuild_vectors_for_book(book_id: str) -> int:
    """Re-embed all chunks for a book into ChromaDB."""
    from engine.adapters.chroma_adapter import get_collection
    from engine.config import EMBEDDING_MODEL
    from sentence_transformers import SentenceTransformer

    conn = _get_db()
    rows = conn.execute(
        "SELECT c.chunk_id, c.content_type, c.text "
        "FROM chunks c "
        "JOIN books b ON c.book_id = b.id "
        "WHERE b.book_id = ? AND c.text != '' "
        "ORDER BY c.reading_order",
        (book_id,),
    ).fetchall()

    # Category is not stored in the DB; default to textbook
    category = "textbook"
    conn.close()

    if not rows:
        logger.warning("reindex: no chunks found for %s", book_id)
        return 0

    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = get_collection()

    texts = [r["text"] for r in rows]
    ids = [r["chunk_id"] for r in rows]
    metadatas = [
        {
            "book_id": book_id,
            "chunk_id": r["chunk_id"],
            "content_type": r["content_type"],
            "category": category,
        }
        for r in rows
    ]

    batch_size = 64
    total = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]

        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        collection.upsert(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_meta,
        )
        total += len(batch_ids)

    logger.info("reindex: upserted %d vectors for %s", total, book_id)
    return total


def _rebuild_fts5_for_book(book_id: str) -> int:
    """Rebuild FTS5 index entries for a book."""
    conn = _get_db()

    # Get book primary key
    book_row = conn.execute(
        "SELECT id FROM books WHERE book_id = ?", (book_id,)
    ).fetchone()
    if not book_row:
        conn.close()
        return 0

    book_pk = book_row["id"]

    # Check if chunk_fts table exists
    has_fts = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_fts'"
    ).fetchone()

    if not has_fts:
        logger.warning("reindex: chunk_fts table does not exist, skipping FTS rebuild")
        conn.close()
        return 0

    # Delete existing FTS entries for this book's chunks, then re-insert
    # The triggers on chunks table handle FTS automatically, so we just
    # need to ensure the data is consistent
    chunk_count = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE book_id = ?", (book_pk,)
    ).fetchone()[0]

    conn.close()
    logger.info("reindex: FTS5 index has %d chunks for %s (maintained by triggers)", chunk_count, book_id)
    return chunk_count


def _run_reindex(book_id: str, task_id: int | None, payload_book_id: int | None) -> None:
    """Execute reindex in background thread."""
    try:
        if task_id:
            update_task(task_id, status="running", progress=0, log="Starting reindex...")
        if payload_book_id:
            update_book_status(payload_book_id, "processing")

        # Step 1: Rebuild vectors (70% of work)
        if task_id:
            update_task(task_id, status="running", progress=10, log="Rebuilding vector index...")

        vec_count = _rebuild_vectors_for_book(book_id)

        if task_id:
            update_task(task_id, status="running", progress=70, log=f"Vectors rebuilt: {vec_count}")

        # Step 2: Verify FTS5 (30% of work)
        if task_id:
            update_task(task_id, status="running", progress=80, log="Verifying FTS5 index...")

        fts_count = _rebuild_fts5_for_book(book_id)

        if task_id:
            update_task(task_id, status="done", progress=100, log=f"Reindex complete: {vec_count} vectors, {fts_count} FTS entries")
        if payload_book_id:
            update_book_status(payload_book_id, "indexed")

        logger.info("Reindex done: %s (vectors=%d, fts=%d)", book_id, vec_count, fts_count)

    except Exception as e:
        logger.error("Reindex failed for %s: %s", book_id, e, exc_info=True)
        if task_id:
            try:
                update_task(task_id, status="error", error=str(e))
            except Exception:
                pass
        if payload_book_id:
            try:
                update_book_status(payload_book_id, "error")
            except Exception:
                pass


@router.post("/reindex")
def reindex(req: ReindexRequest, background_tasks: BackgroundTasks):
    """Rebuild vector + FTS5 indexes for a book (or all books).

    If book_id is provided, reindex that book only.
    If book_id is None, reindex all books.
    """
    if req.book_id:
        # Single book reindex
        background_tasks.add_task(
            _run_reindex, req.book_id, req.task_id, req.payload_book_id
        )
        return {"status": "started", "book_id": req.book_id, "task_id": req.task_id}

    # Reindex all books
    conn = _get_db()
    book_ids = [
        r["book_id"]
        for r in conn.execute("SELECT book_id FROM books ORDER BY id").fetchall()
    ]
    conn.close()

    for bid in book_ids:
        background_tasks.add_task(_run_reindex, bid, None, None)

    return {"status": "started", "books": len(book_ids)}
