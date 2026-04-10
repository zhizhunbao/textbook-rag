"""questions routes — Question generation endpoints.

Endpoints:
    POST   /engine/questions/generate   — generate + auto-score study questions via LLM
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from engine_v2.question_gen.generator import QuestionGenerator

# ============================================================
# Router
# ============================================================
router = APIRouter()


# ============================================================
# Request / Response models
# ============================================================
class GenerateRequest(BaseModel):
    """Request body for question generation.

    Supports both legacy single book_id and new multi-book book_ids.
    page_start / page_end use 0-indexed page numbers for ChromaDB filtering.
    """

    book_id: str | None = None
    book_ids: list[str] | None = None
    category: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    count: int = 5
    auto_score: bool = True


# ============================================================
# Endpoints
# ============================================================
@router.post("/questions/generate")
async def generate_questions(req: GenerateRequest):
    """Generate study questions from textbook chunks.

    Accepts book_ids array + category + chapter_key for fine-grained filtering.
    Falls back to legacy single book_id if book_ids is not provided.
    Auto-scores each question via LLM-as-Judge (relevance, clarity, difficulty).
    """
    # Normalise: merge legacy book_id into book_ids
    effective_book_ids = req.book_ids
    if not effective_book_ids and req.book_id:
        effective_book_ids = [req.book_id]

    logger.info(
        "Generating {} questions — book_ids={}, category={}, pages=[{}, {}), auto_score={}",
        req.count,
        effective_book_ids,
        req.category,
        req.page_start,
        req.page_end,
        req.auto_score,
    )

    gen = QuestionGenerator()
    questions = gen.generate(
        book_ids=effective_book_ids,
        category=req.category,
        page_start=req.page_start,
        page_end=req.page_end,
        count=req.count,
        auto_score=req.auto_score,
    )

    logger.info("Generated {} questions successfully", len(questions))

    return {
        "questions": [
            {
                "question": q.question,
                "difficulty": q.difficulty,
                "type": q.question_type,
                "question_category": q.question_category,
                "source_chunk_id": q.source_chunk_id,
                "book_id": q.book_id,
                "book_title": q.book_title,
                "source_page": q.source_page,
                # Scores from LLM-as-Judge
                "score_relevance": q.scores.relevance,
                "score_clarity": q.scores.clarity,
                "score_difficulty": q.scores.difficulty,
                "score_overall": q.scores.overall,
                "score_reasoning": q.scores.reasoning,
            }
            for q in questions
        ],
        "count": len(questions),
    }
