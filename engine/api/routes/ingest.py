"""POST /engine/ingest — trigger ingest pipeline from Payload hook."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from engine.adapters.payload_client import update_task, update_book_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingest"])

_executor = ThreadPoolExecutor(max_workers=2)


class IngestRequest(BaseModel):
    book_id: int
    file_url: str
    category: str = "textbook"
    task_id: int


def _run_pipeline(book_id: int, file_url: str, category: str, task_id: int) -> None:
    """Execute the full ingest pipeline in a background thread."""
    try:
        update_task(task_id, status="running", progress=0)
        update_book_status(book_id, "processing")

        # Import here to avoid circular dep at startup
        from engine.ingest.pipeline import IngestPipeline
        pipeline = IngestPipeline()
        pipeline.run(
            book_id=book_id,
            file_url=file_url,
            category=category,
            task_id=task_id,
        )
    except Exception as e:
        logger.error("Ingest pipeline failed for book %d: %s", book_id, e)
        update_task(task_id, status="error", error=str(e))
        update_book_status(book_id, "error")


@router.post("/ingest")
def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    """Start ingest pipeline asynchronously. Returns immediately."""
    background_tasks.add_task(
        _run_pipeline, req.book_id, req.file_url, req.category, req.task_id
    )
    return {"status": "started", "task_id": req.task_id}
