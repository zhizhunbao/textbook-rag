"""ndcg — 归一化折损累计增益 (pure-math, zero LLM)。

Normalized Discounted Cumulative Gain — measures ranking quality
by discounting gains at lower positions.

Ref: llama_index.core.evaluation.retrieval.metrics — NDCG
"""

from __future__ import annotations

from llama_index.core.evaluation.retrieval.metrics import NDCG

from engine_v2.evaluation.models import MetricResult


def compute_ndcg(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> MetricResult:
    """Compute NDCG (0-1). Zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs from the retriever.
        expected_ids: Ground-truth chunk IDs from Golden Dataset.

    Returns:
        MetricResult with name="ndcg".
    """
    if not expected_ids or not retrieved_ids:
        return MetricResult(name="ndcg", score=0.0)

    metric = NDCG()
    score = metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    return MetricResult(name="ndcg", score=score)
