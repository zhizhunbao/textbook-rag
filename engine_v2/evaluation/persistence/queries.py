"""queries — Fetch query records from Payload CMS.

Extracted from history.py to separate data access from evaluation logic.
"""

from __future__ import annotations

import httpx
from loguru import logger

from engine_v2.settings import PAYLOAD_URL
from engine_v2.evaluation.models import QueryRecord
from engine_v2.evaluation.persistence.auth import (
    PAYLOAD_TIMEOUT,
    get_payload_token,
    invalidate_token,
)


async def fetch_query_by_id(query_id: int) -> QueryRecord:
    """Fetch a single Queries record from Payload CMS by ID."""
    url = f"{PAYLOAD_URL}/api/queries/{query_id}"
    token = await get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    try:
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            # Token expired → invalidate, re-login, retry once
            if resp.status_code == 403:
                logger.warning("JWT expired for query_id={}, re-authenticating…", query_id)
                invalidate_token()
                token = await get_payload_token()
                headers = {"Authorization": f"JWT {token}"}
                resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            raw = resp.json()
    except httpx.ConnectError:
        logger.error("Cannot connect to Payload CMS at {} — is it running?", PAYLOAD_URL)
        raise RuntimeError(
            f"Cannot connect to Payload CMS at {PAYLOAD_URL}. "
            "Ensure the Payload server is running and PAYLOAD_URL is correct."
        )
    except httpx.HTTPStatusError as exc:
        logger.error("Payload returned {} for query_id={}", exc.response.status_code, query_id)
        raise RuntimeError(
            f"Payload returned HTTP {exc.response.status_code} for query_id={query_id}"
        )

    return _map_query_record(raw)


async def fetch_recent_queries(limit: int = 20) -> list[QueryRecord]:
    """Fetch the most recent N Queries records from Payload CMS."""
    params = {
        "limit": str(limit),
        "sort": "-createdAt",
    }
    url = f"{PAYLOAD_URL}/api/queries"
    token = await get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 403:
            invalidate_token()
            token = await get_payload_token()
            headers = {"Authorization": f"JWT {token}"}
            resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("docs", [])
    return [_map_query_record(d) for d in docs]


def extract_contexts(sources: list[dict]) -> list[str]:
    """Extract context strings from sources array.

    Each source may have 'full_content' (preferred) or 'snippet' as fallback.
    """
    contexts: list[str] = []
    for src in sources:
        text = src.get("full_content") or src.get("snippet") or ""
        if text:
            contexts.append(text)
    return contexts


def _map_query_record(raw: dict) -> QueryRecord:
    """Map raw Payload JSON to a QueryRecord dataclass."""
    return QueryRecord(
        id=raw.get("id", 0),
        question=raw.get("question", ""),
        answer=raw.get("answer", ""),
        sources=raw.get("sources") or [],
        model=raw.get("model"),
        created_at=raw.get("createdAt", ""),
    )
