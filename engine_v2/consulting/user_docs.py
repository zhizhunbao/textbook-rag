"""consulting.user_docs — User private document endpoints.

Endpoints (C3 — User Private Documents):
    POST   /engine/consulting/user-doc/ingest   — ingest user PDF into private collection
    GET    /engine/consulting/user-doc/list      — list user's private documents
    DELETE /engine/consulting/user-doc/{doc_id}  — delete user doc + ChromaDB cleanup
"""

from __future__ import annotations

import threading
from pathlib import Path

import chromadb
from fastapi import APIRouter, Request
from loguru import logger
from pydantic import BaseModel

from engine_v2.personas.registry import (
    fetch_persona as _fetch_persona,
    get_collection_count as _get_collection_count,
)
from engine_v2.user_docs.manager import (
    update_user_doc as _update_user_doc,
    user_collection_name as _user_collection_name,
)
from engine_v2.settings import (
    CHROMA_PERSIST_DIR,
    DATA_DIR,
    MINERU_OUTPUT_DIR,
    PAYLOAD_API_KEY,
    PAYLOAD_URL,
)

router = APIRouter(tags=["consulting"])


# ============================================================
# Request models
# ============================================================


class UserDocIngestRequest(BaseModel):
    """Ingest a user-uploaded PDF into their private collection."""

    # GO-MU-06: user_id removed — now extracted from JWT auth
    persona_slug: str
    doc_id: int  # Payload UserDocuments record ID
    pdf_filename: str  # filename in data/raw_pdfs/user_private/
    force_parse: bool = False
    country: str = "ca"  # ISO 3166-1 alpha-2


# ============================================================
# Helpers
# ============================================================


def _payload_headers() -> dict[str, str]:
    """Get auth headers for Payload CMS."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"users API-Key {PAYLOAD_API_KEY}"
    return headers


# ============================================================
# POST /engine/consulting/user-doc/ingest
# ============================================================


@router.post("/user-doc/ingest")
async def user_doc_ingest(req: UserDocIngestRequest, request: Request):
    """Ingest a user-uploaded PDF into their private ChromaDB collection.

    Flow:
        1. MinerU parse (if not cached)
        2. MinerUReader → IngestionPipeline → user_{userId}_{personaSlug}
        3. Update UserDocuments record: status=indexed, chunkCount=N

    PDF is expected at: data/raw_pdfs/user_private/{pdf_filename}
    (Payload PdfUploads/UserDocuments stores files there via staticDir)
    """
    from engine_v2.api.routes.ingest import _run_mineru_parse
    from engine_v2.ingestion.pipeline import ingest_book

    # GO-MU-06: user_id from JWT auth
    user_data = getattr(request.state, "user", {})
    user_id = user_data.get("id", 0)
    collection_name = _user_collection_name(user_id, req.persona_slug, req.country)

    # Derive book_dir_name from filename
    stem = Path(req.pdf_filename).stem
    book_dir_name = stem.lower().replace(" ", "_").replace("-", "_")
    category = "user_private"

    # Locate PDF — Payload stores uploads in data/raw_pdfs/user_private/
    pdf_base = DATA_DIR / "raw_pdfs" / "user_private"
    pdf_path = pdf_base / req.pdf_filename
    if not pdf_path.exists():
        # Payload may store with subdirectory structure
        for candidate in pdf_base.rglob(req.pdf_filename):
            pdf_path = candidate
            break
    if not pdf_path.exists():
        _update_user_doc(req.doc_id, status="error",
                         error=f"PDF not found: {req.pdf_filename}")
        return {
            "status": "error",
            "message": f"PDF not found at {pdf_base / req.pdf_filename}",
        }

    # MinerU output path
    auto_dir = (
        MINERU_OUTPUT_DIR / category / book_dir_name / book_dir_name / "auto"
    )
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"

    def _run():
        try:
            # Mark as processing
            _update_user_doc(req.doc_id, status="processing",
                             chroma_collection=collection_name)

            # Step 1: MinerU parse
            if req.force_parse or not content_list_path.exists():
                logger.info(
                    "Parsing user PDF: user={}, persona={}, file={}",
                    user_id, req.persona_slug, pdf_path,
                )
                _run_mineru_parse(pdf_path, book_dir_name, category)
            else:
                logger.info(
                    "MinerU output exists for user doc {}, skipping parse",
                    book_dir_name,
                )

            # Step 2: Ingest into user-private collection
            result = ingest_book(
                book_id=0,  # no Payload book record
                book_dir_name=book_dir_name,
                category=category,
                collection_name=collection_name,
            )

            chunk_count = result.get("chunk_count", 0)
            _update_user_doc(
                req.doc_id,
                status="indexed",
                chunk_count=chunk_count,
                chroma_collection=collection_name,
            )
            logger.info(
                "User doc ingest complete: user={}, persona={}, chunks={}",
                user_id, req.persona_slug, chunk_count,
            )

        except Exception as e:
            logger.exception(
                "User doc ingest failed: user={}, doc={}, error={}",
                user_id, req.doc_id, e,
            )
            _update_user_doc(req.doc_id, status="error", error=str(e))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "status": "accepted",
        "doc_id": req.doc_id,
        "collection_name": collection_name,
        "book_dir_name": book_dir_name,
    }


# ============================================================
# GET /engine/consulting/user-doc/list
# ============================================================


@router.get("/user-doc/list")
async def user_doc_list(request: Request, persona_slug: str | None = None):
    """List a user's private documents with collection stats.

    Args:
        persona_slug: Optional filter by persona.
    """
    import httpx

    # GO-MU-06: user_id from JWT auth
    user_data = getattr(request.state, "user", {})
    user_id = user_data.get("id", 0)

    headers = _payload_headers()
    params: dict[str, str] = {
        "where[user][equals]": str(user_id),
        "sort": "-createdAt",
        "limit": "50",
    }
    if persona_slug:
        # Filter by persona relationship — need to resolve persona ID first
        persona = _fetch_persona(persona_slug)
        if persona:
            params["where[persona][equals]"] = str(persona.get("id", ""))

    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/user-documents",
            params=params,
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except Exception as e:
        logger.warning("Failed to fetch user docs: {}", e)
        return {"docs": [], "error": str(e)}

    # Enrich with live ChromaDB stats
    result = []
    for doc in docs:
        collection = doc.get("chromaCollection", "")
        live_count = _get_collection_count(collection) if collection else 0
        result.append({
            "id": doc.get("id"),
            "filename": doc.get("filename"),
            "status": doc.get("status"),
            "chunkCount": doc.get("chunkCount", 0),
            "liveChunkCount": live_count,
            "chromaCollection": collection,
            "persona": doc.get("persona"),
            "createdAt": doc.get("createdAt"),
            "description": doc.get("description"),
        })

    return {"docs": result}


# ============================================================
# DELETE /engine/consulting/user-doc/{doc_id}
# ============================================================


@router.delete("/user-doc/{doc_id}")
async def user_doc_delete(doc_id: int, delete_vectors: bool = True):
    """Delete a user document and optionally clean up its ChromaDB data.

    Args:
        doc_id: Payload UserDocuments record ID.
        delete_vectors: If True, also delete the ChromaDB collection.
    """
    import httpx

    headers = _payload_headers()

    # Fetch the doc to get collection name before deleting
    collection_name = ""
    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/user-documents/{doc_id}",
            headers=headers,
            timeout=10.0,
        )
        if resp.is_success:
            doc_data = resp.json()
            collection_name = doc_data.get("chromaCollection", "")
    except Exception:
        pass

    # Delete from Payload
    deleted = False
    try:
        resp = httpx.delete(
            f"{PAYLOAD_URL}/api/user-documents/{doc_id}",
            headers=headers,
            timeout=10.0,
        )
        deleted = resp.is_success
    except Exception as e:
        logger.warning("Failed to delete user doc {}: {}", doc_id, e)

    # Clean up ChromaDB collection
    vectors_deleted = False
    if delete_vectors and collection_name:
        try:
            client = chromadb.PersistentClient(
                path=str(CHROMA_PERSIST_DIR),
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            client.delete_collection(collection_name)
            vectors_deleted = True
            logger.info(
                "Deleted ChromaDB collection: {}", collection_name,
            )
        except Exception as e:
            logger.warning(
                "Failed to delete ChromaDB collection {}: {}",
                collection_name, e,
            )

    return {
        "doc_id": doc_id,
        "deleted": deleted,
        "vectors_deleted": vectors_deleted,
        "collection_name": collection_name,
    }
