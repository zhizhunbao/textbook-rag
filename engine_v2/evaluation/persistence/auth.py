"""auth — Payload CMS JWT authentication.

Provides a cached JWT token for admin API access.
All evaluation modules that need Payload access import from here.
"""

from __future__ import annotations

import httpx
from loguru import logger

from engine_v2.settings import PAYLOAD_URL

# ============================================================
# Constants
# ============================================================
PAYLOAD_TIMEOUT = 30.0

# Cached JWT token for Payload admin access
_payload_token: str | None = None


async def get_payload_token() -> str:
    """Authenticate with Payload CMS and cache the JWT token.

    Uses PAYLOAD_ADMIN_EMAIL / PAYLOAD_ADMIN_PASSWORD from settings.
    Token is cached module-level to avoid re-login on every request.
    """
    global _payload_token
    if _payload_token:
        return _payload_token

    from engine_v2.settings import PAYLOAD_ADMIN_EMAIL, PAYLOAD_ADMIN_PASSWORD

    if not PAYLOAD_ADMIN_EMAIL or not PAYLOAD_ADMIN_PASSWORD:
        raise RuntimeError(
            "PAYLOAD_ADMIN_EMAIL and PAYLOAD_ADMIN_PASSWORD must be set in .env "
            "for the engine to authenticate with Payload CMS."
        )

    url = f"{PAYLOAD_URL}/api/users/login"
    async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
        resp = await client.post(url, json={
            "email": PAYLOAD_ADMIN_EMAIL,
            "password": PAYLOAD_ADMIN_PASSWORD,
        })
        resp.raise_for_status()
        data = resp.json()

    _payload_token = data.get("token")
    if not _payload_token:
        raise RuntimeError("Payload login succeeded but no token returned")

    logger.info("Authenticated with Payload CMS as {}", PAYLOAD_ADMIN_EMAIL)
    return _payload_token


def invalidate_token() -> None:
    """Clear the cached JWT token so the next request triggers re-login."""
    global _payload_token
    _payload_token = None
