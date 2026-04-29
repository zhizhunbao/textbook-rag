"""billing routes — Usage quota status endpoint (GO-MON-04).

Endpoints:
    GET /engine/billing/me — Current user's quota usage and remaining limits.
"""

from __future__ import annotations

from fastapi import APIRouter

from engine_v2.api.deps import CurrentUser
from engine_v2.api.middleware.quota import (
    _store,
    _TIERS,
    _DAY_SECONDS,
    _MONTH_SECONDS,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/me")
async def billing_me(user: CurrentUser):
    """Return current user's quota usage and remaining limits.

    Called by the frontend UsagePanel to display progress bars.
    Uses the in-memory quota store (read-only peek, no mutation).
    """
    tier = user.tier
    limits = _TIERS.get(tier, _TIERS["free"])

    query_used = _store.peek(f"query:{user.id}", float(_DAY_SECONDS))
    ingest_used = _store.peek(f"ingest:{user.id}", float(_MONTH_SECONDS))

    query_limit = limits["query_daily"]
    ingest_limit = limits["ingest_monthly"]

    return {
        "tier": tier,
        "query": {
            "used": query_used,
            "limit": query_limit,
            "remaining": max(0, query_limit - query_used),
            "period": "day",
        },
        "ingest": {
            "used": ingest_used,
            "limit": ingest_limit,
            "remaining": max(0, ingest_limit - ingest_used),
            "period": "month",
        },
    }
