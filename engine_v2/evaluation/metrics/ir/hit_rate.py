"""hit_rate — 检索命中率 (pure-math, zero LLM)。

Whether at least one expected chunk appears in the retrieved set.

Ref: llama_index.core.evaluation.retrieval.metrics — HitRate
"""

from __future__ import annotations

from llama_index.core.evaluation.retrieval.metrics import HitRate

from engine_v2.evaluation.models import MetricResult


def compute_hit_rate(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> MetricResult:
    """Compute Hit Rate (0-1). Zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs from the retriever.
        expected_ids: Ground-truth chunk IDs from Golden Dataset.

    Returns:
        MetricResult with name="hit_rate".
    """
    if not expected_ids or not retrieved_ids:
        return MetricResult(name="hit_rate", score=0.0)

    metric = HitRate()
    score = metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    return MetricResult(name="hit_rate", score=score)
