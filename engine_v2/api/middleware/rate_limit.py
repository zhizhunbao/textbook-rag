"""rate_limit — In-memory per-user rate limiting middleware.

Implements a simple sliding window counter for Engine API endpoints.
MVP design: in-memory only — resets on server restart.
Sufficient for GO-MU; upgrade to Redis when scaling horizontally.

Configuration (env vars):
    RATE_LIMIT_RPM   — requests per minute per user (default 30)
    RATE_LIMIT_BURST — burst allowance above RPM (default 10)
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# ============================================================
# Config
# ============================================================

_RPM = int(os.getenv("RATE_LIMIT_RPM", "30"))
_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))
_WINDOW_SEC = 60.0
_MAX_PER_WINDOW = _RPM + _BURST

# Paths exempt from rate limiting
_EXEMPT_PATHS: set[str] = {
    "/engine/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


# ============================================================
# In-memory store
# ============================================================


class _SlidingWindow:
    """Thread-safe sliding window counter per user."""

    __slots__ = ("_lock", "_buckets")

    def __init__(self):
        self._lock = Lock()
        # user_key → list of timestamps
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, remaining)."""
        now = time.monotonic()
        cutoff = now - _WINDOW_SEC

        with self._lock:
            # Prune expired entries
            timestamps = self._buckets[key]
            timestamps[:] = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= _MAX_PER_WINDOW:
                return False, 0

            timestamps.append(now)
            remaining = _MAX_PER_WINDOW - len(timestamps)
            return True, remaining


_store = _SlidingWindow()


# ============================================================
# Middleware
# ============================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user rate limiting (in-memory sliding window)."""

    def __init__(self, app: ASGIApp, exempt_paths: set[str] | None = None):
        super().__init__(app)
        self._exempt = exempt_paths or _EXEMPT_PATHS

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ):
        path = request.url.path

        # Skip exempt paths
        if path in self._exempt:
            return await call_next(request)

        # Extract user key from auth middleware
        user_data = getattr(request.state, "user", None)
        if not user_data:
            # Not authenticated — let auth middleware handle 401
            return await call_next(request)

        user_key = f"user:{user_data.get('id', 'anon')}"
        allowed, remaining = _store.check(user_key)

        if not allowed:
            logger.warning("Rate limit exceeded for {}", user_key)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please wait before making more requests.",
                    "limit": _MAX_PER_WINDOW,
                    "window_seconds": int(_WINDOW_SEC),
                },
                headers={
                    "Retry-After": str(int(_WINDOW_SEC)),
                    "X-RateLimit-Limit": str(_MAX_PER_WINDOW),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(_MAX_PER_WINDOW)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
