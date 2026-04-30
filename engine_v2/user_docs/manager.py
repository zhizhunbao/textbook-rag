"""manager — User private document ChromaDB lifecycle.

Responsibilities:
    - Build user-private ChromaDB collection names
    - Idempotent creation of user-private collections
    - Collection stats retrieval
    - Payload CMS UserDocuments record updates
"""

from __future__ import annotations

from typing import Any

import chromadb
from loguru import logger

from engine_v2.settings import (
    CHROMA_PERSIST_DIR,
    PAYLOAD_API_KEY,
    PAYLOAD_URL,
)


# ============================================================
# Collection naming
# ============================================================


def user_collection_name(
    user_id: int, persona_slug: str, country: str = "ca",
) -> str:
    """Build a user-private ChromaDB collection name.

    Format: user_{userId}_{country}_{personaSlug}
    Guarantees data isolation per user per persona per country.
    """
    return f"user_{user_id}_{country}_{persona_slug}"


# ============================================================
# Collection lifecycle
# ============================================================


def _get_chroma_client() -> chromadb.ClientAPI:
    """Create a persistent ChromaDB client."""
    return chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


def ensure_user_collection(
    user_id: int, persona_slug: str, country: str = "ca",
) -> str:
    """Idempotent creation of a user-private ChromaDB collection.

    Returns the collection name.
    """
    name = user_collection_name(user_id, persona_slug, country)
    client = _get_chroma_client()
    client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(
        "Ensured user collection: user={}, persona={}, collection={}",
        user_id, persona_slug, name,
    )
    return name


def get_user_doc_stats(
    user_id: int, persona_slug: str, country: str = "ca",
) -> dict[str, Any]:
    """Return collection stats for a user/persona pair."""
    name = user_collection_name(user_id, persona_slug, country)
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection(name)
        count = col.count()
    except Exception:
        count = 0

    return {
        "user_id": user_id,
        "persona_slug": persona_slug,
        "collection_name": name,
        "chunk_count": count,
        "has_data": count > 0,
    }


# ============================================================
# Payload CMS integration
# ============================================================


def _payload_headers() -> dict[str, str]:
    """Get auth headers for Payload CMS."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
    return headers


def update_user_doc(
    doc_id: int,
    status: str | None = None,
    chunk_count: int | None = None,
    chroma_collection: str | None = None,
    error: str | None = None,
) -> None:
    """Update a UserDocuments record in Payload CMS."""
    import httpx

    body: dict[str, Any] = {}
    if status:
        body["status"] = status
    if chunk_count is not None:
        body["chunkCount"] = chunk_count
    if chroma_collection:
        body["chromaCollection"] = chroma_collection
    if error:
        body["error"] = error

    if not body:
        return

    try:
        httpx.patch(
            f"{PAYLOAD_URL}/api/user-documents/{doc_id}",
            json=body,
            headers=_payload_headers(),
            timeout=10.0,
        ).raise_for_status()
    except Exception as e:
        logger.warning("Failed to update user doc {}: {}", doc_id, e)
