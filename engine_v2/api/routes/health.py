"""Health route — GET /engine/health."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "version": "2.0.0"}
