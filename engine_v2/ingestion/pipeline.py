"""IngestionPipeline — Reader → Transforms → ChromaVectorStore.

Fully LlamaIndex-native:
    - Uses ChromaVectorStore integration (not raw chromadb)
    - Uses Settings.embed_model for embeddings (not manual SentenceTransformer)
    - Uses IngestionPipeline.run() with vector_store sink
    - Payload CMS notification is the only project-specific part
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import BaseNode
from llama_index.core.settings import Settings
from llama_index.vector_stores.chroma import ChromaVectorStore

from engine_v2.ingestion.transformations import BBoxNormalizer
from engine_v2.readers.mineru_reader import MinerUReader
from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    MINERU_OUTPUT_DIR,
    PAYLOAD_API_KEY,
    PAYLOAD_URL,
)

logger = logging.getLogger(__name__)


def get_vector_store(
    collection_name: str = CHROMA_COLLECTION,
) -> ChromaVectorStore:
    """Create a ChromaVectorStore backed by persistent ChromaDB."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    return ChromaVectorStore(chroma_collection=collection)


def ingest_book(
    book_id: int,
    book_dir_name: str,
    category: str = "textbook",
    task_id: int | None = None,
    mineru_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Run the full ingest pipeline for one book.

    Flow (fully LlamaIndex-native):
        1. MinerUReader.load_data() → Document[]
        2. IngestionPipeline.run(transformations, vector_store) → Node[]
           - BBoxNormalizer (metadata cleanup)
           - Settings.embed_model (auto-embeddings)
           - ChromaVectorStore (auto-upsert)
        3. Push chunk records to Payload CMS
        4. Update book status in Payload CMS

    Returns:
        dict with keys: book_id, chunk_count, status
    """
    mineru_path = Path(mineru_dir) if mineru_dir else MINERU_OUTPUT_DIR

    _notify(task_id, status="running", progress=5, log="Reading MinerU output...")

    # Step 1: Read documents via MinerUReader
    reader = MinerUReader(mineru_path)
    documents = reader.load_data(book_dir_name=book_dir_name, category=category)
    if not documents:
        raise FileNotFoundError(
            f"No content found for {book_dir_name} in {mineru_path}"
        )
    logger.info("Read %d documents from %s", len(documents), book_dir_name)
    _notify(task_id, status="running", progress=20,
            log=f"Read {len(documents)} chunks")

    # Step 2: Run LlamaIndex IngestionPipeline
    vector_store = get_vector_store()
    pipeline = IngestionPipeline(
        transformations=[
            BBoxNormalizer(),        # project-specific metadata cleanup
            Settings.embed_model,    # auto-embed via HuggingFace
        ],
        vector_store=vector_store,   # auto-upsert into ChromaDB
    )
    nodes = pipeline.run(documents=documents, show_progress=True)
    logger.info("Ingested %d nodes into ChromaDB", len(nodes))
    _notify(task_id, status="running", progress=70, log="Vectors built in ChromaDB")

    # Step 3: Push chunk metadata to Payload CMS
    _push_chunks_to_payload(nodes, book_id)
    _notify(task_id, status="running", progress=90, log="Chunks pushed to Payload")

    # Step 4: Update book status
    _update_book_status(book_id, chunk_count=len(nodes))
    _notify(task_id, status="done", progress=100, log="Ingest complete")

    return {
        "book_id": book_id,
        "book_dir_name": book_dir_name,
        "chunk_count": len(nodes),
        "status": "indexed",
    }


# ---------------------------------------------------------------------------
# Payload CMS helpers (project-specific, not LlamaIndex)
# ---------------------------------------------------------------------------

def _payload_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
    return headers


def _push_chunks_to_payload(nodes: list[BaseNode], book_id: int) -> None:
    """Batch-create chunk records in Payload CMS."""
    import httpx

    headers = _payload_headers()
    for node in nodes:
        bbox = node.metadata.get("bbox", [0, 0, 0, 0])
        page_idx = node.metadata.get("page_idx", 0)
        payload = {
            "chunkId": node.id_,
            "book": book_id,
            "text": node.get_content(),
            "contentType": node.metadata.get("content_type", "text"),
            "readingOrder": node.metadata.get("reading_order", 0),
            "pageNumber": page_idx,
            "sourceLocators": [
                {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3],
                 "page": page_idx}
            ] if bbox and any(v != 0 for v in bbox) else [],
            "vectorized": True,
        }
        try:
            resp = httpx.post(
                f"{PAYLOAD_URL}/api/chunks",
                json=payload, headers=headers, timeout=30.0,
            )
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to push chunk %s: %s", node.id_, e)


def _update_book_status(book_id: int, chunk_count: int) -> None:
    """Mark book as indexed in Payload CMS."""
    import httpx

    try:
        httpx.patch(
            f"{PAYLOAD_URL}/api/books/{book_id}",
            json={"status": "indexed", "chunkCount": chunk_count},
            headers=_payload_headers(),
            timeout=30.0,
        ).raise_for_status()
    except Exception as e:
        logger.error("Failed to update book %d status: %s", book_id, e)


def _notify(
    task_id: int | None, status: str,
    progress: int | None = None, log: str | None = None,
    error: str | None = None,
) -> None:
    """Update PipelineTask progress in Payload CMS."""
    if task_id is None:
        return
    import httpx

    body: dict[str, Any] = {"status": status}
    if progress is not None:
        body["progress"] = progress
    if log is not None:
        body["log"] = log
    if error is not None:
        body["error"] = error
    try:
        httpx.patch(
            f"{PAYLOAD_URL}/api/ingest-tasks/{task_id}",
            json=body, headers=_payload_headers(), timeout=30.0,
        ).raise_for_status()
    except Exception as e:
        logger.warning("Failed to notify task %d: %s", task_id, e)
