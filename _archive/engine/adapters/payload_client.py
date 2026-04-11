"""Payload CMS REST API client — used by Engine to read/write Collections.

v2.0: Engine calls Payload API to:
  - batch create Chunks after ingest
  - update Book status (pending → processing → indexed / error)
  - update PipelineTask progress and status
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from engine.config import PAYLOAD_API_KEY, PAYLOAD_URL

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        h["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
    return h


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------

def update_book_status(book_id: int, status: str, chunk_count: int | None = None) -> None:
    """Update Book.status (and optionally chunkCount) via Payload API."""
    payload: dict[str, Any] = {"status": status}
    if chunk_count is not None:
        payload["chunkCount"] = chunk_count
    url = f"{PAYLOAD_URL}/api/books/{book_id}"
    try:
        resp = httpx.patch(url, json=payload, headers=_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
        logger.info("Book %d status → %s", book_id, status)
    except Exception as e:
        logger.error("Failed to update book %d status: %s", book_id, e)
        raise


# ---------------------------------------------------------------------------
# Chunks
# ---------------------------------------------------------------------------

def batch_create_chunks(chunks: list[dict[str, Any]]) -> list[int]:
    """Batch-create Chunks in Payload. Returns list of created IDs."""
    created_ids = []
    for chunk in chunks:
        url = f"{PAYLOAD_URL}/api/chunks"
        try:
            resp = httpx.post(url, json=chunk, headers=_headers(), timeout=_TIMEOUT)
            resp.raise_for_status()
            created_ids.append(resp.json()["doc"]["id"])
        except Exception as e:
            logger.error("Failed to create chunk %s: %s", chunk.get("chunkId"), e)
            raise
    logger.info("Created %d chunks in Payload", len(created_ids))
    return created_ids


# ---------------------------------------------------------------------------
# PipelineTasks
# ---------------------------------------------------------------------------

def update_task(
    task_id: int,
    status: str,
    progress: int | None = None,
    log: str | None = None,
    error: str | None = None,
) -> None:
    """Update PipelineTask status/progress/log/error."""
    payload: dict[str, Any] = {"status": status}
    if progress is not None:
        payload["progress"] = progress
    if log is not None:
        payload["log"] = log
    if error is not None:
        payload["error"] = error
    url = f"{PAYLOAD_URL}/api/pipeline-tasks/{task_id}"
    try:
        resp = httpx.patch(url, json=payload, headers=_headers(), timeout=_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to update task %d: %s", task_id, e)
        raise
