"""batch — Batch-evaluate recent queries from Payload (no RAG re-run).

Fetches real production data, evaluates each answer using
individual metric files, and persists results with a shared batchId.
"""

from __future__ import annotations

import uuid

from loguru import logger

from engine_v2.evaluation.models import HistoryEvalResult
from engine_v2.evaluation.metrics.faithfulness import evaluate_faithfulness
from engine_v2.evaluation.metrics.relevancy import evaluate_relevancy
from engine_v2.evaluation.metrics.context_relevancy import evaluate_context_relevancy
from engine_v2.evaluation.metrics.answer_relevancy import evaluate_answer_relevancy
from engine_v2.evaluation.metrics.question_depth import assess_question_depth
from engine_v2.evaluation.persistence.queries import (
    extract_contexts,
    fetch_recent_queries,
)
from engine_v2.evaluation.persistence.evaluations import persist_evaluation


async def evaluate_batch_from_queries(
    n_recent: int = 20,
    batch_id: str | None = None,
) -> list[HistoryEvalResult]:
    """Batch-evaluate the most recent N Queries from Payload.

    Args:
        n_recent: Number of recent queries to evaluate.
        batch_id: Optional batch group ID. Auto-generated if not provided.

    Returns:
        List of HistoryEvalResult, one per query.
    """
    if not batch_id:
        batch_id = f"batch-{uuid.uuid4().hex[:8]}"

    records = await fetch_recent_queries(limit=n_recent)
    if not records:
        logger.warning("No queries found for batch evaluation")
        return []

    logger.info(
        "Batch evaluating {} queries — batch_id={}",
        len(records), batch_id,
    )

    results: list[HistoryEvalResult] = []
    for i, record in enumerate(records):
        contexts = extract_contexts(record.sources)

        try:
            # 1. Question quality
            try:
                depth_r = await assess_question_depth(record.question)
                q_depth = depth_r.depth
                q_depth_score = depth_r.score
                q_depth_reasoning = depth_r.reasoning
            except Exception:
                q_depth = None
                q_depth_score = None
                q_depth_reasoning = ""

            # 2. Answer quality
            faith_r = await evaluate_faithfulness(
                record.question, record.answer, contexts,
            )
            ans_r = await evaluate_answer_relevancy(
                record.question, record.answer,
            )

            # 3. Citation quality
            relev_r = await evaluate_relevancy(
                record.question, record.answer, contexts,
            )
            ctx_r = await evaluate_context_relevancy(
                record.question, contexts,
            )

            eval_result = HistoryEvalResult(
                query_id=record.id,
                question=record.question,
                answer=record.answer,
                question_depth=q_depth,
                question_depth_score=q_depth_score,
                question_depth_reasoning=q_depth_reasoning,
                faithfulness=faith_r.score,
                answer_relevancy=ans_r.score,
                context_relevancy=ctx_r.score,
                relevancy=relev_r.score,
                feedback={
                    "faithfulness": faith_r.feedback,
                    "answer_relevancy": ans_r.feedback,
                    "context_relevancy": ctx_r.feedback,
                    "relevancy": relev_r.feedback,
                    "question_depth": q_depth_reasoning,
                },
            )
        except Exception as exc:
            logger.error(
                "Failed to evaluate query_id={}: {}", record.id, exc,
            )
            eval_result = HistoryEvalResult(
                query_id=record.id,
                question=record.question,
                answer=record.answer,
            )

        await persist_evaluation(eval_result, batch_id=batch_id)
        results.append(eval_result)
        logger.debug(
            "Batch progress: {}/{} — query_id={}",
            i + 1, len(records), record.id,
        )

    logger.info(
        "Batch evaluation complete — {} results, batch_id={}",
        len(results), batch_id,
    )
    return results
