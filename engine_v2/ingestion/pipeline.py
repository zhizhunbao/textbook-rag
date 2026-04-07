"""IngestionPipeline — Reader → Transforms → ChromaVectorStore.

Fully LlamaIndex-native:
    - Uses ChromaVectorStore integration (not raw chromadb)
    - Uses Settings.embed_model for embeddings (not manual SentenceTransformer)
    - Uses IngestionPipeline.run() with vector_store sink
    - Payload CMS notification is the only project-specific part

Ref: HF-06 — batch chunk push optimization + loguru migration
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import BaseNode
from llama_index.core.settings import Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger

from engine_v2.ingestion.transformations import BBoxNormalizer
from engine_v2.readers.mineru_reader import MinerUReader
from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    MINERU_OUTPUT_DIR,
    PAYLOAD_ADMIN_EMAIL,
    PAYLOAD_ADMIN_PASSWORD,
    PAYLOAD_API_KEY,
    PAYLOAD_URL,
)


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
    logger.info("Read {} documents from {}", len(documents), book_dir_name)
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
    logger.info("Ingested {} nodes into ChromaDB", len(nodes))
    _notify(task_id, status="running", progress=70, log="Vectors built in ChromaDB")

    # Step 3: Push chunk metadata to Payload CMS
    _push_chunks_to_payload(nodes, book_id)
    _notify(task_id, status="running", progress=90, log="Chunks pushed to Payload")

    # Step 4: Update book status + seed ingestOutput
    ingest_output = {
        "nodeCount": len(nodes),
        "chromaCollection": CHROMA_COLLECTION,
        "chromaPersistDir": str(CHROMA_PERSIST_DIR),
    }
    _update_book_status(book_id, chunk_count=len(nodes), ingest_output=ingest_output)
    logger.info("Ingest complete for book {} — {} nodes indexed", book_id, len(nodes))
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
    """Get auth headers for Payload CMS REST API.

    Strategy:
        1. If PAYLOAD_API_KEY is set, use Bearer token directly.
        2. Otherwise, login with PAYLOAD_ADMIN_EMAIL/PASSWORD to get JWT.
        3. Cache the JWT token module-level for reuse.
    """
    global _cached_token

    headers = {"Content-Type": "application/json"}

    # Option 1: API key (if configured)
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
        return headers

    # Option 2: Login with email/password
    if PAYLOAD_ADMIN_EMAIL and PAYLOAD_ADMIN_PASSWORD:
        if not _cached_token:
            _cached_token = _login_payload()
        if _cached_token:
            headers["Authorization"] = f"JWT {_cached_token}"

    return headers


# Module-level cache for Payload JWT token
_cached_token: str | None = None


def _login_payload() -> str | None:
    """Login to Payload CMS and return JWT token."""
    import httpx

    try:
        resp = httpx.post(
            f"{PAYLOAD_URL}/api/users/login",
            json={
                "email": PAYLOAD_ADMIN_EMAIL,
                "password": PAYLOAD_ADMIN_PASSWORD,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        token = resp.json().get("token")
        if token:
            logger.info("Logged into Payload CMS as {}", PAYLOAD_ADMIN_EMAIL)
            return token
        logger.warning("Payload login response missing token")
    except Exception as e:
        logger.error("Failed to login to Payload CMS: {}", e)
    return None


def _map_content_type(raw: str) -> str:
    """Map MinerU content_type to Payload Chunks select values.

    Payload allows: text, table, image, equation, code.
    MinerU produces: text, title, interline_equation,
    table, image, discarded, etc.
    """
    mapping: dict[str, str] = {
        "text": "text",
        "title": "text",
        "table": "table",
        "image": "image",
        "equation": "equation",
        "interline_equation": "equation",
        "inline_equation": "equation",
        "code": "code",
        "discarded": "text",
    }
    return mapping.get(raw, "text")


def _push_chunks_to_payload(nodes: list[BaseNode], book_id: int) -> None:
    """Batch-create chunk records in Payload CMS.

    Deletes existing chunks for the book first (idempotent re-runs),
    then pushes new chunks in batches of BATCH_SIZE.
    """
    import httpx

    BATCH_SIZE = 50
    headers = _payload_headers()
    total = len(nodes)
    created = 0
    errors = 0

    # Delete existing chunks for this book (idempotent re-run support)
    try:
        del_resp = httpx.get(
            f"{PAYLOAD_URL}/api/chunks",
            params={
                "where[book][equals]": str(book_id),
                "limit": "0",  # Just get totalDocs count
            },
            headers=headers, timeout=15.0,
        )
        if del_resp.is_success:
            existing = del_resp.json().get("totalDocs", 0)
            if existing > 0:
                logger.info("Deleting {} existing chunks for book {}", existing, book_id)
                httpx.delete(
                    f"{PAYLOAD_URL}/api/chunks",
                    params={"where[book][equals]": str(book_id)},
                    headers=headers, timeout=60.0,
                ).raise_for_status()
                logger.info("Deleted existing chunks for book {}", book_id)
    except Exception as e:
        logger.warning("Failed to delete existing chunks for book {}: {}", book_id, e)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = nodes[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

        for node in batch:
            x0 = node.metadata.get("bbox_x0", 0.0)
            y0 = node.metadata.get("bbox_y0", 0.0)
            x1 = node.metadata.get("bbox_x1", 0.0)
            y1 = node.metadata.get("bbox_y1", 0.0)
            page_idx = node.metadata.get("page_idx", 0)
            raw_type = node.metadata.get("content_type", "text")
            payload = {
                "chunkId": node.id_,
                "book": book_id,
                "text": node.get_content() or "(empty)",
                "contentType": _map_content_type(raw_type),
                "readingOrder": node.metadata.get("reading_order", 0),
                "pageNumber": page_idx,
                "sourceLocators": [
                    {"x0": x0, "y0": y0, "x1": x1, "y1": y1,
                     "page": page_idx}
                ] if any(v != 0 for v in (x0, y0, x1, y1)) else [],
                "vectorized": True,
            }
            try:
                resp = httpx.post(
                    f"{PAYLOAD_URL}/api/chunks",
                    json=payload, headers=headers, timeout=30.0,
                )
                if not resp.is_success:
                    # Log response body for debugging 400 errors
                    if errors < 3:
                        logger.warning(
                            "Chunk push {} failed ({}): {}",
                            node.id_, resp.status_code, resp.text[:500],
                        )
                    resp.raise_for_status()
                created += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    logger.warning("Failed to push chunk {}: {}", node.id_, e)

        logger.info(
            "Pushed batch {}/{} ({} chunks, {} errors so far)",
            batch_num, total_batches, len(batch), errors,
        )

    logger.info(
        "Chunk push complete: {}/{} created, {} errors",
        created, total, errors,
    )


def _update_book_status(
    book_id: int,
    chunk_count: int,
    ingest_output: dict | None = None,
) -> None:
    """Mark book as indexed in Payload CMS with 2-stage pipeline."""
    import httpx

    body: dict = {
        "status": "indexed",
        "chunkCount": chunk_count,
        "pipeline": {
            "parse": "done",
            "ingest": "done",
        },
    }
    if ingest_output:
        body["pipeline"]["ingestOutput"] = ingest_output

    try:
        httpx.patch(
            f"{PAYLOAD_URL}/api/books/{book_id}",
            json=body,
            headers=_payload_headers(),
            timeout=30.0,
        ).raise_for_status()
    except Exception as e:
        logger.error("Failed to update book {} status: {}", book_id, e)


def _notify(
    task_id: int | None, status: str,
    progress: int | None = None, log: str | None = None,
    error: str | None = None,
) -> None:
    """Update PipelineTask progress in Payload CMS.

    Log lines are APPENDED with timestamps for real-time visibility.
    """
    if task_id is None:
        return
    import httpx
    from datetime import datetime

    body: dict[str, Any] = {"status": status}
    if progress is not None:
        body["progress"] = progress
    if error is not None:
        body["error"] = error

    try:
        # Append log line with timestamp (fetch existing → append → patch)
        if log is not None:
            ts = datetime.now().strftime("%H:%M:%S")
            new_line = f"[{ts}] {log}"

            # Fetch existing log
            existing_log = ""
            try:
                resp = httpx.get(
                    f"{PAYLOAD_URL}/api/ingest-tasks/{task_id}",
                    headers=_payload_headers(), timeout=10.0,
                )
                if resp.is_success:
                    existing_log = resp.json().get("log", "") or ""
            except Exception:
                pass

            body["log"] = f"{existing_log}\n{new_line}".strip()

        httpx.patch(
            f"{PAYLOAD_URL}/api/ingest-tasks/{task_id}",
            json=body, headers=_payload_headers(), timeout=30.0,
        ).raise_for_status()
    except Exception as e:
        logger.warning("Failed to notify task {}: {}", task_id, e)

