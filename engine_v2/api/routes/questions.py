"""questions routes — Question generation endpoints.

Endpoints:
    POST   /engine/questions/generate           — generate + auto-score study questions via LLM
    POST   /engine/questions/generate-dataset   — batch generate a QuestionSet (QD-05)
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


class GenerateDatasetRequest(BaseModel):
    """Request body for batch QuestionSet generation (QD-05)."""

    name: str
    purpose: str = "eval"
    book_ids: list[str] | None = None
    k_per_book: int = 10
    strategy: str = "stratified"


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


# ============================================================
# QD-05: Generate Dataset — batch create a QuestionSet
# ============================================================
@router.post("/questions/generate-dataset")
async def generate_dataset(req: GenerateDatasetRequest):
    """Batch generate a QuestionSet via stratified chunk sampling.

    Flow:
        1. Create QuestionSet in Payload (status=generating)
        2. Sample chunks via StratifiedChunkSampler
        3. For each chunk: generate question + reference answer
        4. Save Questions with datasetId + sourceChunkId
        5. Update QuestionSet (status=ready, questionCount)

    Ref: llama_index.core.llama_dataset.generator — RagDatasetGenerator pattern
    """
    from engine_v2.evaluation.history import _get_payload_token
    from engine_v2.question_gen.sampler import StratifiedChunkSampler

    token = await _get_payload_token()
    headers = {
        "Authorization": f"JWT {token}",
        "Content-Type": "application/json",
    }

    logger.info(
        "generate-dataset — name={}, strategy={}, k_per_book={}, book_ids={}",
        req.name, req.strategy, req.k_per_book, req.book_ids,
    )

    # ── 1. Create QuestionSet (status=generating) ──
    dataset_id = await _create_question_set(
        name=req.name,
        purpose=req.purpose,
        book_ids=req.book_ids,
        config={"strategy": req.strategy, "k_per_book": req.k_per_book},
        headers=headers,
    )

    # ── 2. Sample chunks ──
    sampler = StratifiedChunkSampler()
    chunks = sampler.sample(
        book_ids=req.book_ids,
        k_per_book=req.k_per_book,
        strategy=req.strategy,
    )

    if not chunks:
        await _update_question_set_status(dataset_id, "ready", 0, headers)
        return {
            "dataset_id": dataset_id,
            "name": req.name,
            "total_generated": 0,
            "status": "ready",
        }

    # ── 3. Generate question + reference answer per chunk ──
    gen = QuestionGenerator()
    saved_count = 0

    for chunk in chunks:
        try:
            # Generate 1 question from this chunk
            questions = gen.generate(
                book_ids=[chunk.book_id] if chunk.book_id else None,
                count=1,
                chunk_sample_size=1,
                auto_score=True,
            )

            if not questions:
                continue

            q = questions[0]
            q.source_chunk_id = chunk.id

            # Generate reference answer
            ref_answer = _generate_reference_answer(chunk.text, q.question)

            # Persist to Payload
            ok = await _save_question_to_payload(
                question=q,
                dataset_id=dataset_id,
                reference_answer=ref_answer,
                headers=headers,
            )
            if ok:
                saved_count += 1

        except Exception as exc:
            logger.warning(
                "Failed to generate question for chunk {}: {}",
                chunk.id[:20], exc,
            )

    # ── 4. Update QuestionSet status ──
    await _update_question_set_status(
        dataset_id, "ready", saved_count, headers,
    )

    logger.info(
        "generate-dataset complete — name={}, saved={}",
        req.name, saved_count,
    )

    return {
        "dataset_id": dataset_id,
        "name": req.name,
        "total_generated": saved_count,
        "status": "ready",
    }


# ============================================================
# Helpers — Payload CRUD for QD-05
# ============================================================
def _generate_reference_answer(context: str, question: str) -> str:
    """Generate a reference answer using LLM predict."""
    from llama_index.core.settings import Settings
    from engine_v2.question_gen.prompts import REFANSWER_PROMPT_TMPL

    try:
        result = Settings.llm.predict(
            REFANSWER_PROMPT_TMPL,
            context=context[:3000],
            question=question,
        )
        return result.strip()
    except Exception as exc:
        logger.warning("Reference answer generation failed: {}", exc)
        return ""


async def _create_question_set(
    name: str,
    purpose: str,
    book_ids: list[str] | None,
    config: dict,
    headers: dict,
) -> int:
    """Create QuestionSet record in Payload, return its ID."""
    from engine_v2.settings import PAYLOAD_URL
    import httpx

    payload = {
        "name": name,
        "purpose": purpose,
        "bookIds": book_ids or [],
        "generationConfig": config,
        "status": "generating",
        "questionCount": 0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{PAYLOAD_URL}/api/question-sets",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        doc = resp.json().get("doc", {})
        return doc.get("id", 0)


async def _update_question_set_status(
    dataset_id: int,
    status: str,
    question_count: int,
    headers: dict,
) -> None:
    """Update QuestionSet status + question count."""
    from engine_v2.settings import PAYLOAD_URL
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.patch(
            f"{PAYLOAD_URL}/api/question-sets/{dataset_id}",
            json={"status": status, "questionCount": question_count},
            headers=headers,
        )


async def _save_question_to_payload(
    question,
    dataset_id: int,
    reference_answer: str,
    headers: dict,
) -> bool:
    """Save a single generated question to Payload Questions collection."""
    from engine_v2.settings import PAYLOAD_URL
    import httpx

    payload = {
        "question": question.question,
        "bookId": question.book_id,
        "bookTitle": question.book_title,
        "topicHint": question.question_category or "",
        "source": "ai",
        "likes": 0,
        "questionCategory": question.question_category,
        "sourcePage": question.source_page,
        "sourceChunkId": question.source_chunk_id,
        "referenceAnswer": reference_answer,
        "datasetId": dataset_id,
        "scoreRelevance": question.scores.relevance,
        "scoreClarity": question.scores.clarity,
        "scoreDifficulty": question.scores.difficulty,
        "scoreOverall": question.scores.overall,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{PAYLOAD_URL}/api/questions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Failed to save question: {}", exc)
        return False
