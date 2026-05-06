"""recall — 召回率@K (pure-math, zero LLM)。

Fraction of relevant results that were retrieved.

Ref: llama_index.core.evaluation.retrieval.metrics — Recall
"""

from __future__ import annotations

from llama_index.core.evaluation.retrieval.metrics import Recall

from engine_v2.evaluation.models import MetricResult


def compute_recall(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> MetricResult:
    """Compute Recall@K (0-1). Zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs from the retriever.
        expected_ids: Ground-truth chunk IDs from Golden Dataset.

    Returns:
        MetricResult with name="recall_at_k".
    """
    if not expected_ids or not retrieved_ids:
        return MetricResult(name="recall_at_k", score=0.0)

    metric = Recall()
    score = metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    return MetricResult(name="recall_at_k", score=score)
