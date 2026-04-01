"""Questions route — POST /engine/questions/generate."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from engine_v2.question_gen.generator import QuestionGenerator

router = APIRouter()


class GenerateRequest(BaseModel):
    book_id: str | None = None
    count: int = 5


@router.post("/questions/generate")
async def generate_questions(req: GenerateRequest):
    """Generate study questions from textbook chunks."""
    gen = QuestionGenerator()
    questions = gen.generate(book_id=req.book_id, count=req.count)
    return {
        "questions": [
            {
                "question": q.question,
                "difficulty": q.difficulty,
                "type": q.question_type,
                "source_chunk_id": q.source_chunk_id,
                "book_id": q.book_id,
            }
            for q in questions
        ],
        "count": len(questions),
    }
