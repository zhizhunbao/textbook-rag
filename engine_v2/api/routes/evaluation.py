"""Evaluation route — POST /engine/evaluation/run."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from engine_v2.evaluation.evaluator import evaluate_response, evaluate_dataset

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvalSingleRequest(BaseModel):
    question: str


class EvalBatchRequest(BaseModel):
    questions: list[str]
    reference_answers: list[str] | None = None


@router.post("/single")
async def eval_single(req: EvalSingleRequest):
    """Evaluate a single query — returns faithfulness + relevancy scores."""
    result = await evaluate_response(query=req.question)
    return {
        "query": result.query,
        "answer": result.answer,
        "scores": {
            "faithfulness": result.faithfulness,
            "relevancy": result.relevancy,
        },
        "feedback": result.feedback,
    }


@router.post("/batch")
async def eval_batch(req: EvalBatchRequest):
    """Batch-evaluate multiple queries — returns scores per query."""
    results = await evaluate_dataset(
        queries=req.questions,
        reference_answers=req.reference_answers,
    )
    return {
        "results": [
            {
                "query": r.query,
                "scores": {
                    "faithfulness": r.faithfulness,
                    "relevancy": r.relevancy,
                    "correctness": r.correctness,
                },
                "feedback": r.feedback,
            }
            for r in results
        ],
        "count": len(results),
    }
