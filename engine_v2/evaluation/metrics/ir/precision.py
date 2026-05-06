"""precision — 精确率@K (pure-math, zero LLM)。

Fraction of retrieved results that are relevant.

Ref: llama_index.core.evaluation.retrieval.metrics — Precision
"""

from __future__ import annotations

from llama_index.core.evaluation.retrieval.metrics import Precision

from engine_v2.evaluation.models import MetricResult


def compute_precision(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> MetricResult:
    """Compute Precision@K (0-1). Zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs from the retriever.
        expected_ids: Ground-truth chunk IDs from Golden Dataset.

    Returns:
        MetricResult with name="precision_at_k".
    """
    if not expected_ids or not retrieved_ids:
        return MetricResult(name="precision_at_k", score=0.0)

    metric = Precision()
    score = metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    return MetricResult(name="precision_at_k", score=score)
