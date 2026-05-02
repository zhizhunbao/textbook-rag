"""quota — In-memory per-user quota middleware (GO-MON-01 + GO-MON-04).

Enforces daily query limits and monthly ingest limits based on user tier.
Uses an in-memory sliding window for real-time enforcement (no HTTP round-trip).
UsageRecords in Payload CMS serve as audit log only — not consulted on hot path.

Tier limits:
    Free: 30 queries/day, 3 doc ingests/month
    Pro:  200 queries/day, 100 doc ingests/month
    Admin: unlimited

After each allowed request, writes a UsageRecord to Payload asynchronously
(fire-and-forget) so billing dashboards stay current.
"""

from __future__ import annotations

import os
import time
import threading
from collections import defaultdict

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


# ============================================================
# Tier limits
# ============================================================

_TIERS: dict[str, dict[str, int]] = {
    "free": {"query_daily": 30, "ingest_monthly": 3},
    "pro": {"query_daily": 200, "ingest_monthly": 100},
}

# Endpoint classification
_QUERY_ENDPOINTS: set[str] = {
    "/engine/consulting/query",
    "/engine/consulting/query/stream",
    "/engine/query",
    "/engine/query/stream",
}

_INGEST_ENDPOINTS: set[str] = {
    "/engine/consulting/user-doc/ingest",
    "/engine/ingest",
}

# Payload CMS for async usage recording
_PAYLOAD_URL = os.getenv("PAYLOAD_URL", "http://localhost:3001")
_PAYLOAD_API_KEY = os.getenv("PAYLOAD_API_KEY", "")


# ============================================================
# In-memory counters
# ============================================================

_DAY_SECONDS = 86_400
_MONTH_SECONDS = 30 * _DAY_SECONDS


class _QuotaStore:
    """Thread-safe in-memory counter for quota enforcement."""

    __slots__ = ("_lock", "_buckets")

    def __init__(self):
        self._lock = threading.Lock()
        # key → list[timestamp]
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check_and_record(
        self, key: str, window_sec: float, limit: int,
    ) -> tuple[bool, int]:
        """Check quota and record usage if allowed.

        Returns (allowed, remaining).
        """
        now = time.monotonic()
        cutoff = now - window_sec

        with self._lock:
            ts = self._buckets[key]
            ts[:] = [t for t in ts if t > cutoff]

            if len(ts) >= limit:
                return False, 0

            ts.append(now)
            return True, limit - len(ts)

    def peek(self, key: str, window_sec: float) -> int:
        """Read current usage count without recording. Thread-safe."""
        now = time.monotonic()
        cutoff = now - window_sec

        with self._lock:
            ts = self._buckets.get(key, [])
            return sum(1 for t in ts if t > cutoff)


_store = _QuotaStore()


# ============================================================
# Middleware
# ============================================================


class QuotaMiddleware(BaseHTTPMiddleware):
    """Enforce tier-based usage quotas on query/ingest endpoints."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ):
        path = request.url.path

        # Only enforce on billable endpoints
        action = _classify_action(path)
        if not action:
            return await call_next(request)

        # Extract user from auth middleware
        user_data = getattr(request.state, "user", None)
        if not user_data:
            return await call_next(request)

        role = user_data.get("role", "reader")
        if role == "admin":
            return await call_next(request)

        user_id = user_data.get("id", 0)
        tier = user_data.get("tier", "free")
        limits = _TIERS.get(tier, _TIERS["free"])

        # Determine window and limit
        if action == "query":
            key = f"query:{user_id}"
            window = float(_DAY_SECONDS)
            limit = limits["query_daily"]
        else:
            key = f"ingest:{user_id}"
            window = float(_MONTH_SECONDS)
            limit = limits["ingest_monthly"]

        allowed, remaining = _store.check_and_record(key, window, limit)

        if not allowed:
            logger.warning(
                "Quota exceeded: user={} tier={} action={}", user_id, tier, action,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Quota exceeded for {action}. Upgrade to Pro for higher limits.",
                    "action": action,
                    "tier": tier,
                    "limit": limit,
                    "upgrade_url": "/billing/upgrade",
                },
                headers={
                    "X-Quota-Limit": str(limit),
                    "X-Quota-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Headers for client awareness
        response.headers["X-Quota-Limit"] = str(limit)
        response.headers["X-Quota-Remaining"] = str(remaining)

        # Async audit log write (fire-and-forget)
        _write_usage_record_async(user_id, path, action)

        return response


# ============================================================
# Helpers
# ============================================================


def _classify_action(path: str) -> str | None:
    """Classify endpoint as 'query', 'ingest', or None (not billable)."""
    if path in _QUERY_ENDPOINTS:
        return "query"
    if path in _INGEST_ENDPOINTS:
        return "ingest"
    return None


def _write_usage_record_async(
    user_id: int, endpoint: str, action: str,
) -> None:
    """Fire-and-forget write to Payload UsageRecords collection."""

    def _write():
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if _PAYLOAD_API_KEY:
            headers["Authorization"] = f"users API-Key {_PAYLOAD_API_KEY}"
        try:
            resp = httpx.post(
                f"{_PAYLOAD_URL}/api/usage-records",
                json={
                    "user": user_id,
                    "endpoint": endpoint,
                    "action": action,
                },
                headers=headers,
                timeout=5.0,
            )
            if not resp.is_success:
                logger.debug(
                    "UsageRecord write failed: {} {}", resp.status_code, resp.text[:200],
                )
        except Exception as e:
            logger.debug("UsageRecord write error: {}", e)

    thread = threading.Thread(target=_write, daemon=True)
    thread.start()
