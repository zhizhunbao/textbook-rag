"""consulting.personas — Persona listing and status endpoints.

Endpoints:
    GET /engine/consulting/personas       — list available personas
    GET /engine/consulting/status/{slug}  — collection stats for a persona
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger

from engine_v2.personas.registry import (
    fetch_persona as _fetch_persona,
    get_collection_count as _get_collection_count,
    get_collection_name as _get_persona_collection,
)
from engine_v2.settings import PAYLOAD_API_KEY, PAYLOAD_URL

router = APIRouter(tags=["consulting"])


# ============================================================
# GET /engine/consulting/personas — list personas
# ============================================================


@router.get("/personas")
async def list_personas(country: str | None = None):
    """List all enabled consulting personas with collection stats.

    Args:
        country: Optional ISO 3166-1 alpha-2 filter (e.g. 'ca').
    """
    import httpx

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"users API-Key {PAYLOAD_API_KEY}"

    try:
        params: dict[str, str] = {
            "where[isEnabled][equals]": "true",
            "sort": "sortOrder",
            "limit": "50",
        }
        if country:
            params["where[country][equals]"] = country
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/consulting-personas",
            params=params,
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        personas = resp.json().get("docs", [])
    except Exception as e:
        logger.warning("Failed to fetch personas: {}", e)
        return {"personas": [], "error": str(e)}

    # Enrich with collection stats
    result = []
    for p in personas:
        collection_name = p.get("chromaCollection", f"persona_{p['slug']}")
        chunk_count = _get_collection_count(collection_name)
        result.append({
            "name": p.get("name"),
            "slug": p.get("slug"),
            "icon": p.get("icon"),
            "description": p.get("description"),
            "chromaCollection": collection_name,
            "chunkCount": chunk_count,
            "country": p.get("country", "ca"),
            "category": p.get("category"),
        })

    return {"personas": result}


# ============================================================
# GET /engine/consulting/status/{slug} — collection stats
# ============================================================


@router.get("/status/{slug}")
async def persona_status(slug: str):
    """Return ChromaDB collection stats for a persona."""
    collection_name = _get_persona_collection(slug)
    count = _get_collection_count(collection_name)

    return {
        "slug": slug,
        "collection_name": collection_name,
        "chunk_count": count,
        "has_data": count > 0,
    }
