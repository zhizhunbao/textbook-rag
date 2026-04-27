"""retrieval_metrics — Pure-math IR metrics for retrieval evaluation.

Responsibilities:
    - Compute HitRate, MRR, Precision@K, Recall@K, NDCG from retrieved vs expected chunk IDs
    - Zero LLM calls — all metrics are pure mathematical calculations
    - Provide a unified interface for the evaluation pipeline

Ref: llama_index.core.evaluation.retrieval.metrics — HitRate, MRR, Precision, Recall, NDCG
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from llama_index.core.evaluation.retrieval.metrics import (
    HitRate,
    MRR,
    NDCG,
    Precision,
    Recall,
)


# ============================================================
# Data classes
# ============================================================
@dataclass
class RetrievalMetrics:
    """Container for retrieval quality metrics (all 0-1 scale)."""

    hit_rate: float = 0.0
    mrr: float = 0.0
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    ndcg: float = 0.0
    ir_score: float = 0.0  # Mean of all metrics

    def to_dict(self) -> dict[str, float]:
        """Serialize to dict for API/Payload persistence."""
        return {
            "hit_rate": round(self.hit_rate, 4),
            "mrr": round(self.mrr, 4),
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "ndcg": round(self.ndcg, 4),
            "ir_score": round(self.ir_score, 4),
        }


# ============================================================
# Core computation — zero LLM calls
# ============================================================
def compute_retrieval_metrics(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> RetrievalMetrics:
    """Compute 5 retrieval quality metrics.

    All metrics are pure mathematical calculations — zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs returned by the retriever.
        expected_ids: Ground-truth chunk IDs from the Golden Dataset.

    Returns:
        RetrievalMetrics with all 5 scores (0-1 scale).
    """
    if not expected_ids:
        logger.warning("compute_retrieval_metrics called with empty expected_ids")
        return RetrievalMetrics()

    if not retrieved_ids:
        logger.warning("compute_retrieval_metrics called with empty retrieved_ids")
        return RetrievalMetrics()

    # Compute each metric using LlamaIndex built-in implementations
    hit_rate_metric = HitRate()
    mrr_metric = MRR()
    precision_metric = Precision()
    recall_metric = Recall()
    ndcg_metric = NDCG()

    hit_rate = hit_rate_metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    mrr = mrr_metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    precision = precision_metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    recall = recall_metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    ndcg = ndcg_metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    # IR score = mean of all 5 metrics
    scores = [hit_rate, mrr, precision, recall, ndcg]
    ir_score = sum(scores) / len(scores)

    result = RetrievalMetrics(
        hit_rate=hit_rate,
        mrr=mrr,
        precision_at_k=precision,
        recall_at_k=recall,
        ndcg=ndcg,
        ir_score=ir_score,
    )

    logger.debug(
        "IR metrics — hit={:.2f}, mrr={:.2f}, p@k={:.2f}, r@k={:.2f}, "
        "ndcg={:.2f}, ir={:.2f} (retrieved={}, expected={})",
        hit_rate, mrr, precision, recall, ndcg, ir_score,
        len(retrieved_ids), len(expected_ids),
    )

    return result
