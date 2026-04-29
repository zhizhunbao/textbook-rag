"""deps — Dependency injection for Engine API routes.

Provides:
    get_engine()       → Singleton TextbookCitationQueryEngine
    get_current_user() → UserContext from JWT auth (GO-MU-07)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from engine_v2.query_engine.citation import (
    TextbookCitationQueryEngine,
    get_query_engine,
)


# ============================================================
# Query Engine singleton
# ============================================================


@lru_cache(maxsize=1)
def get_engine() -> TextbookCitationQueryEngine:
    """Return singleton TextbookCitationQueryEngine instance.

    Composes:
        retrievers/    → QueryFusionRetriever (BM25 + Vector → RRF)
        _create_citation_nodes → merge same-page + Source N labels
        response_synthesizers/ → CitationSynthesizer
    """
    return get_query_engine()


# ============================================================
# User Context (GO-MU-07)
# ============================================================


class UserContext(BaseModel):
    """Authenticated user context extracted from JWT."""

    id: int
    role: str = "reader"
    email: str = ""
    tier: str = "free"  # GO-MON-03: free | pro


def get_current_user(request: Request) -> UserContext:
    """Extract current user from request.state (set by AuthMiddleware).

    Admin users can impersonate via `?as_user_id=X` query param (debug only).
    """
    user_data = getattr(request.state, "user", None)
    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = UserContext(
        id=user_data.get("id", 0),
        role=user_data.get("role", "reader"),
        email=user_data.get("email", ""),
        tier=user_data.get("tier", "free"),
    )

    # Admin impersonation for debugging
    if user.role == "admin":
        as_user = request.query_params.get("as_user_id")
        if as_user:
            try:
                user = UserContext(id=int(as_user), role="reader")
            except ValueError:
                pass

    return user


# Annotated type alias for cleaner route signatures
CurrentUser = Annotated[UserContext, Depends(get_current_user)]
