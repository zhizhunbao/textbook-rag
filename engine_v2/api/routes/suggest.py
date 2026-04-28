"""suggest routes — Suggest high-quality questions for chat consumption.

Endpoints:
    GET    /engine/questions/suggest  — fetch suggested questions by book
"""

from __future__ import annotations


from typing import Any

from fastapi import APIRouter, Query

from loguru import logger

from engine_v2.question_gen.suggest import fetch_suggested_questions

# ============================================================
# Router
# ============================================================
router = APIRouter(tags=["questions"])


# ============================================================
# Endpoints
# ============================================================
@router.get("/questions/suggest")
async def suggest_questions(
    book_id: str | None = Query(None, description="Filter by book ID"),
    limit: int = Query(6, ge=1, le=20, description="Max questions to return"),
) -> dict[str, Any]:
    """Suggest high-quality questions for a book.

    Delegates to question_gen.suggest module for business logic.
    Returns existing questions from Payload CMS sorted by quality score.
    """
    logger.info("Suggest request: book_id={}, limit={}", book_id, limit)
    results = fetch_suggested_questions(book_id=book_id, limit=limit)

    questions = [
        {
            "id": q.id,
            "question": q.question,
            "bookId": q.book_id,
            "bookTitle": q.book_title,
            "difficulty": q.difficulty,
            "category": q.category,
            "likes": q.likes,
        }
        for q in results
    ]

    return {
        "questions": questions,
        "count": len(questions),
        "book_id": book_id,
    }
