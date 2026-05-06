"""evaluations — Persist evaluation results to Payload CMS.

Extracted from history.py to separate persistence from evaluation logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from loguru import logger

from engine_v2.settings import PAYLOAD_URL
from engine_v2.evaluation.persistence.auth import (
    PAYLOAD_TIMEOUT,
    get_payload_token,
    invalidate_token,
)

if TYPE_CHECKING:
    from engine_v2.evaluation.models import FullEvalResult, HistoryEvalResult


async def persist_evaluation(
    result: HistoryEvalResult,
    batch_id: str | None = None,
) -> int | None:
    """Write a HistoryEvalResult to Payload Evaluations collection.

    Returns the created evaluation record ID, or None on failure.
    """
    # Normalise question depth score (1-5) → 0-1 for consistency
    norm_depth = (result.question_depth_score / 5.0) if result.question_depth_score else None

    payload_data = {
        "query": result.question,
        "answer": result.answer,
        "faithfulness": result.faithfulness,
        "relevancy": result.relevancy,
        "contextRelevancy": result.context_relevancy,
        "answerRelevancy": result.answer_relevancy,
        "questionDepth": result.question_depth,
        "questionDepthScore": norm_depth,
        "feedback": result.feedback,
        "queryRef": result.query_id,
    }
    if batch_id:
        payload_data["batchId"] = batch_id

    url = f"{PAYLOAD_URL}/api/evaluations"
    try:
        token = await get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.post(url, json=payload_data, headers=headers)
            if resp.status_code == 403:
                invalidate_token()
                token = await get_payload_token()
                headers = {"Authorization": f"JWT {token}"}
                resp = await client.post(url, json=payload_data, headers=headers)
            resp.raise_for_status()
            created = resp.json()
            return created.get("doc", {}).get("id")
    except Exception:
        logger.warning(
            "Failed to persist evaluation for query_id={}",
            result.query_id,
        )
        return None


async def persist_full_evaluation(
    result: FullEvalResult,
    batch_id: str | None = None,
) -> int | None:
    """Write a FullEvalResult to Payload Evaluations collection.

    Maps all four-category fields to the extended Evaluations schema.
    Returns the created evaluation record ID, or None on failure.
    """
    # Normalise question depth score (1-5) → 0-1 for consistency
    norm_depth = (result.question_depth_score / 5.0) if result.question_depth_score else None

    payload_data: dict = {
        # Original fields
        "query": result.question,
        "answer": result.answer,
        "faithfulness": result.faithfulness,
        "relevancy": result.relevancy,
        "contextRelevancy": result.context_relevancy,
        "answerRelevancy": result.answer_relevancy,
        "questionDepth": result.question_depth,
        "questionDepthScore": norm_depth,
        "feedback": result.feedback,
        "queryRef": result.query_id,
        # Four-category aggregates (EV2-T2-04)
        "ragScore": result.rag_score,
        "llmScore": result.llm_score,
        "answerScore": result.answer_score,
        "overallScore": result.overall_score,
        # Answer sub-dimensions
        "guidelinesPass": result.guidelines_pass,
        "guidelinesFeedback": result.guidelines_feedback,
        # Retrieval strategy
        "retrievalMode": result.retrieval_mode,
        "bm25Hits": result.bm25_hit_count,
        "vectorHits": result.vector_hit_count,
        "bothHits": result.both_hit_count,
        # IR Metrics
        "hitRate": result.hit_rate,
        "mrr": result.mrr,
        "precisionAtK": result.precision_at_k,
        "recallAtK": result.recall_at_k,
        "ndcg": result.ndcg,
        "irScore": result.ir_score,
        "goldenMatchRef": result.golden_match_id,
        # Cross-model (EI-T3-03)
        "judgeModel": result.judge_model,
        # Evaluation metadata (EUX-T2)
        "answerModel": result.answer_model,
        "llmCalls": result.llm_calls,
        # Improvement suggestions (EUX-T3)
        "suggestions": result.suggestions,
        # AP metric (EUX-T4)
        "averagePrecision": result.average_precision,
        # Routing evaluation (EV2-T4-02)
        "routingDecision": result.routing_decision,
        "routingCorrect": result.routing_correct,
        "routingReasoning": result.routing_reasoning,
        # Status
        "status": result.status,
    }
    if batch_id:
        payload_data["batchId"] = batch_id

    url = f"{PAYLOAD_URL}/api/evaluations"
    try:
        token = await get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.post(url, json=payload_data, headers=headers)
            if resp.status_code == 403:
                invalidate_token()
                token = await get_payload_token()
                headers = {"Authorization": f"JWT {token}"}
                resp = await client.post(url, json=payload_data, headers=headers)
            resp.raise_for_status()
            created = resp.json()
            return created.get("doc", {}).get("id")
    except Exception:
        logger.warning(
            "Failed to persist full evaluation for query_id={}",
            result.query_id,
        )
        return None
