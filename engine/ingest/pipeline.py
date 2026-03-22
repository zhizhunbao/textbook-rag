"""IngestPipeline — orchestrates the full ingest flow for one book.

Flow:
  1. pdf_parser   — download/locate PDF → MinerU output
  2. chunk_builder — MinerU output → chunks[]
  3. payload_client — batch create Chunks in Payload PG
  4. index/vector_builder — chunks → ChromaDB
  5. index/fts5_builder  — chunks → Engine SQLite FTS5
  6. payload_client — update Book status=indexed, chunkCount
  7. payload_client — update PipelineTask status=done, progress=100
"""

from __future__ import annotations

import logging
from pathlib import Path

from engine.config import DATABASE_PATH, MINERU_OUTPUT_DIR
from engine.adapters.payload_client import (
    batch_create_chunks,
    update_book_status,
    update_task,
)
from engine.ingest.chunk_builder import build_chunks

logger = logging.getLogger(__name__)


class IngestPipeline:
    """Orchestrates full book ingest pipeline."""

    def run(
        self,
        book_id: int,
        file_url: str,
        category: str,
        task_id: int,
    ) -> None:
        """Run the full pipeline. Updates task progress via Payload API."""
        book_dir_name = self._url_to_dir_name(file_url)
        logger.info("IngestPipeline: book_id=%d dir=%s category=%s", book_id, book_dir_name, category)

        try:
            # Step 1: Build chunks from MinerU output
            update_task(task_id, status="running", progress=10, log="Building chunks from MinerU output...")
            result = build_chunks(
                book_dir_name=book_dir_name,
                category=category,
                mineru_dir=MINERU_OUTPUT_DIR,
            )
            if result is None:
                raise FileNotFoundError(f"No content_list.json found for {book_dir_name}")

            logger.info("  chunks built: %d", len(result.chunks))
            update_task(task_id, status="running", progress=30, log=f"Built {len(result.chunks)} chunks")

            # Step 2: Write chunks to Payload (PostgreSQL)
            chunk_payloads = [self._chunk_to_payload(c, book_id) for c in result.chunks]
            batch_create_chunks(chunk_payloads)
            update_task(task_id, status="running", progress=50, log="Chunks written to Payload")

            # Step 3: Vector index (ChromaDB)
            from engine.index.vector_builder import build_vectors
            build_vectors(result)
            update_task(task_id, status="running", progress=70, log="Vectors built in ChromaDB")

            # Step 4: FTS5 index (Engine SQLite)
            from engine.index.fts5_builder import build_fts5
            build_fts5(result, db_path=DATABASE_PATH)
            update_task(task_id, status="running", progress=90, log="FTS5 index built")

            # Step 5: Mark Book as indexed
            update_book_status(book_id, status="indexed", chunk_count=len(result.chunks))
            update_task(task_id, status="done", progress=100, log="Ingest complete")
            logger.info("IngestPipeline done: book_id=%d chunks=%d", book_id, len(result.chunks))

        except Exception as e:
            logger.error("IngestPipeline error: %s", e, exc_info=True)
            try:
                update_book_status(book_id, status="error")
                update_task(task_id, status="error", error=str(e))
            except Exception:
                logger.error("Failed to update error status for book %d / task %d", book_id, task_id)
            raise

    def _url_to_dir_name(self, file_url: str) -> str:
        """Extract book dir name from Payload media URL or path."""
        return Path(file_url).stem.replace("-", "_")

    def _chunk_to_payload(self, chunk, book_id: int) -> dict:
        """Convert ChunkData to Payload REST API format."""
        return {
            "chunkId": chunk.chunk_id,
            "book": book_id,
            "text": chunk.text,
            "contentType": chunk.content_type,
            "readingOrder": chunk.reading_order,
            "pageNumber": chunk.page_idx,
            "sourceLocators": [{
                "x0": chunk.bbox[0], "y0": chunk.bbox[1],
                "x1": chunk.bbox[2], "y1": chunk.bbox[3],
                "page": chunk.page_idx,
            }] if chunk.bbox else [],
            "vectorized": False,
        }
