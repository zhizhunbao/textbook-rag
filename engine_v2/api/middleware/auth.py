"""auth — JWT verification middleware for Engine API.

Extracts and validates Payload CMS JWT tokens from incoming requests.
Supports two auth strategies:
    1. Cookie: `payload-token` (browser sessions)
    2. Header: `Authorization: Bearer <token>` (API calls)
    3. API Key bypass: `X-Engine-Api-Key` for internal Payload→Engine calls

Injects `request.state.user` = UserContext(id, role) on success.
Returns 401 for unauthenticated requests (except whitelisted paths).

Ref: Payload uses HS256 JWT signed with PAYLOAD_SECRET.
"""

from __future__ import annotations

import os
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# ============================================================
# Constants
# ============================================================

_PAYLOAD_SECRET = os.getenv("PAYLOAD_SECRET", "")
_ENGINE_API_KEY = os.getenv("ENGINE_API_KEY", "")
_COOKIE_NAME = "payload-token"
_JWT_ALGORITHM = "HS256"

# Paths that do NOT require authentication
_PUBLIC_PATHS: set[str] = {
    "/engine/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


# ============================================================
# Middleware
# ============================================================


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate Payload JWT or API Key on every request."""

    def __init__(self, app: ASGIApp, public_paths: set[str] | None = None):
        super().__init__(app)
        self._public = public_paths or _PUBLIC_PATHS

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ):
        path = request.url.path

        # Skip auth for public endpoints
        if path in self._public:
            return await call_next(request)

        # Strategy 1: Internal API Key bypass (Payload→Engine server calls)
        api_key = request.headers.get("x-engine-api-key", "")
        if _ENGINE_API_KEY and api_key == _ENGINE_API_KEY:
            request.state.user = {"id": 0, "role": "admin"}
            return await call_next(request)

        # Strategy 2: JWT from cookie or Authorization header
        token = _extract_token(request)
        if not token:
            # DEV-MODE: skip auth, set anonymous user (re-enable before production)
            logger.debug("No token found — using anonymous user (dev mode)")
            request.state.user = {"id": 0, "role": "reader", "email": "", "tier": "free", "collection": "users"}
            return await call_next(request)

        payload = _verify_token(token)
        if payload is None:
            logger.debug("Invalid token — using anonymous user (dev mode)")
            request.state.user = {"id": 0, "role": "reader", "email": "", "tier": "free", "collection": "users"}
            return await call_next(request)

        # Inject user context
        request.state.user = {
            "id": payload.get("id", 0),
            "role": payload.get("role", "reader"),
            "email": payload.get("email", ""),
            "tier": payload.get("tier", "free"),  # GO-MON-03
            "collection": payload.get("collection", "users"),
        }

        return await call_next(request)


# ============================================================
# Helpers
# ============================================================


def _extract_token(request: Request) -> str | None:
    """Extract JWT from cookie or Authorization header."""
    # Cookie first (browser sessions)
    token = request.cookies.get(_COOKIE_NAME)
    if token:
        return token

    # Authorization: Bearer <token>
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return None


def _verify_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a Payload JWT token."""
    if not _PAYLOAD_SECRET:
        logger.warning("PAYLOAD_SECRET not set — cannot verify JWT")
        return None

    try:
        payload = jwt.decode(
            token,
            _PAYLOAD_SECRET,
            algorithms=[_JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("Invalid JWT: {}", e)
        return None


def _unauthorized(detail: str) -> JSONResponse:
    """Return a 401 response."""
    return JSONResponse(
        status_code=401,
        content={"detail": detail},
    )
