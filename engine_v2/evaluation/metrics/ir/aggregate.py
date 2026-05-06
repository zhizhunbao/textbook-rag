"""aggregate — 一次性计算所有 5 个 IR 指标。

Convenience function that calls all individual IR metric files
and returns a unified RetrievalMetrics container.
"""

from __future__ import annotations

from loguru import logger

from engine_v2.evaluation.models import RetrievalMetrics
from engine_v2.evaluation.metrics.ir.hit_rate import compute_hit_rate
from engine_v2.evaluation.metrics.ir.mrr import compute_mrr
from engine_v2.evaluation.metrics.ir.precision import compute_precision
from engine_v2.evaluation.metrics.ir.recall import compute_recall
from engine_v2.evaluation.metrics.ir.ndcg import compute_ndcg


def compute_all_ir_metrics(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> RetrievalMetrics:
    """Compute all 5 IR retrieval metrics in one call.

    All metrics are pure mathematical calculations — zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs returned by the retriever.
        expected_ids: Ground-truth chunk IDs from the Golden Dataset.

    Returns:
        RetrievalMetrics with all 5 scores (0-1 scale) + ir_score mean.
    """
    if not expected_ids:
        logger.warning("compute_all_ir_metrics called with empty expected_ids")
        return RetrievalMetrics()

    if not retrieved_ids:
        logger.warning("compute_all_ir_metrics called with empty retrieved_ids")
        return RetrievalMetrics()

    hr = compute_hit_rate(retrieved_ids, expected_ids)
    m = compute_mrr(retrieved_ids, expected_ids)
    p = compute_precision(retrieved_ids, expected_ids)
    r = compute_recall(retrieved_ids, expected_ids)
    n = compute_ndcg(retrieved_ids, expected_ids)

    scores = [hr.score or 0, m.score or 0, p.score or 0, r.score or 0, n.score or 0]
    ir_score = sum(scores) / len(scores)

    result = RetrievalMetrics(
        hit_rate=hr.score or 0,
        mrr=m.score or 0,
        precision_at_k=p.score or 0,
        recall_at_k=r.score or 0,
        ndcg=n.score or 0,
        ir_score=ir_score,
    )

    logger.debug(
        "IR metrics — hit={:.2f}, mrr={:.2f}, p@k={:.2f}, r@k={:.2f}, "
        "ndcg={:.2f}, ir={:.2f} (retrieved={}, expected={})",
        result.hit_rate, result.mrr, result.precision_at_k,
        result.recall_at_k, result.ndcg, result.ir_score,
        len(retrieved_ids), len(expected_ids),
    )

    return result
