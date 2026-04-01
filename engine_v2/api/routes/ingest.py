"""Ingest route — POST /engine/ingest."""

from __future__ import annotations

import threading

from fastapi import APIRouter
from pydantic import BaseModel

from engine_v2.ingestion.pipeline import ingest_book

router = APIRouter()


class IngestRequest(BaseModel):
    book_id: int
    file_url: str
    category: str = "textbook"
    task_id: int | None = None


@router.post("/ingest")
async def ingest(req: IngestRequest):
    """Trigger book ingestion in a background thread."""
    from pathlib import Path

    book_dir_name = Path(req.file_url).stem.replace("-", "_")

    thread = threading.Thread(
        target=ingest_book,
        kwargs={
            "book_id": req.book_id,
            "book_dir_name": book_dir_name,
            "category": req.category,
            "task_id": req.task_id,
        },
        daemon=True,
    )
    thread.start()

    return {"status": "accepted", "book_dir_name": book_dir_name}
