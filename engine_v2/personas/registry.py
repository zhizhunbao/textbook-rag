"""registry — Persona ChromaDB collection lifecycle.

Responsibilities:
    - Idempotent creation of persona-specific ChromaDB collections
    - Collection statistics retrieval (chunk_count, status)
    - Persona data fetching from Payload CMS (cached)
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
# Persona cache (in-memory, process-scoped)
# ============================================================

_persona_cache: dict[str, dict[str, Any]] = {}


def fetch_persona(slug: str) -> dict[str, Any] | None:
    """Fetch persona config from Payload CMS (cached in-memory).

    Returns dict with: name, slug, systemPrompt, chromaCollection, etc.
    """
    if slug in _persona_cache:
        return _persona_cache[slug]

    import httpx

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"

    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/consulting-personas",
            params={
                "where[slug][equals]": slug,
                "where[isEnabled][equals]": "true",
                "limit": "1",
            },
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if docs:
            _persona_cache[slug] = docs[0]
            return docs[0]
    except Exception as e:
        logger.warning("Failed to fetch persona {}: {}", slug, e)

    return None


def clear_persona_cache() -> None:
    """Clear the in-memory persona cache (useful after CMS updates)."""
    _persona_cache.clear()


# ============================================================
# Collection lifecycle
# ============================================================


def get_collection_name(slug: str) -> str:
    """Derive ChromaDB collection name for a persona.

    Naming: {country}_{slug}  (e.g. ca_lawyer)
    Fallback: persona_{slug}  (for legacy data without country)
    """
    persona = fetch_persona(slug)
    if persona:
        # Explicit config takes priority (backward compat)
        if persona.get("chromaCollection"):
            return persona["chromaCollection"]
        # New logic: country + slug
        country = persona.get("country", "")
        if country:
            return f"{country}_{slug}"
    return f"persona_{slug}"


def _get_chroma_client() -> chromadb.ClientAPI:
    """Create a persistent ChromaDB client."""
    return chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


def ensure_persona_collection(slug: str) -> str:
    """Idempotent creation of a persona's ChromaDB collection.

    Returns the collection name.
    """
    collection_name = get_collection_name(slug)
    client = _get_chroma_client()
    client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(
        "Ensured persona collection: slug={}, collection={}",
        slug, collection_name,
    )
    return collection_name


def get_persona_stats(slug: str) -> dict[str, Any]:
    """Return collection stats for a persona.

    Returns:
        dict with keys: slug, collection_name, chunk_count, has_data, status
    """
    collection_name = get_collection_name(slug)
    chunk_count = get_collection_count(collection_name)

    status = "ready" if chunk_count > 0 else "empty"

    return {
        "slug": slug,
        "collection_name": collection_name,
        "chunk_count": chunk_count,
        "has_data": chunk_count > 0,
        "status": status,
    }


def get_collection_count(collection_name: str) -> int:
    """Get the document count from a ChromaDB collection."""
    try:
        client = _get_chroma_client()
        col = client.get_or_create_collection(collection_name)
        return col.count()
    except Exception:
        return 0
