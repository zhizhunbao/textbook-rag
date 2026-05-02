"""suggest — Fetch and rank high-quality questions for chat consumption.

Responsibilities:
    - Fetch existing questions from Payload CMS Questions collection
    - Filter by book_id and sort by quality score
    - Return normalised SuggestedQuestion dicts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from loguru import logger

from engine_v2.settings import PAYLOAD_URL, PAYLOAD_API_KEY


# ============================================================
# Data types
# ============================================================
@dataclass
class SuggestedQuestion:
    """A single suggested question for chat consumption."""

    id: int | str
    question: str
    book_id: str = ""
    book_title: str = ""
    difficulty: str | None = None
    category: str | None = None
    likes: int = 0


# ============================================================
# Payload CMS client
# ============================================================
def _payload_headers() -> dict[str, str]:
    """Build authorization headers for Payload REST API."""
    headers = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"users API-Key {PAYLOAD_API_KEY}"
    return headers


def fetch_suggested_questions(
    book_id: str | None = None,
    limit: int = 6,
    min_score: int = 2,
) -> list[SuggestedQuestion]:
    """Fetch high-quality questions from Payload CMS.

    Questions are sorted by overall score (descending), then by likes.
    Only questions with scoreOverall >= min_score are returned.

    Args:
        book_id: Optional filter by book ID.
        limit: Maximum number of questions to return.
        min_score: Minimum overall score threshold.

    Returns:
        List of SuggestedQuestion sorted by quality.
    """
    params: dict[str, Any] = {
        "limit": limit,
        "sort": "-scoreOverall,-likes",
    }

    if book_id:
        params["where[bookId][equals]"] = book_id

    if min_score > 0:
        params["where[scoreOverall][greater_than_equal]"] = min_score

    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/questions",
            params=params,
            headers=_payload_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except Exception as e:
        logger.warning("Failed to fetch questions from Payload: {}", e)
        return []

    questions = [
        SuggestedQuestion(
            id=d.get("id", 0),
            question=d.get("question", ""),
            book_id=d.get("bookId", ""),
            book_title=d.get("bookTitle", ""),
            difficulty=d.get("scoreDifficulty"),
            category=d.get("category"),
            likes=d.get("likes", 0),
        )
        for d in docs
    ]

    logger.info("Fetched {} suggested questions (book_id={})", len(questions), book_id)
    return questions
