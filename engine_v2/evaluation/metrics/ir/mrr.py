"""mrr — 平均倒数排名 (pure-math, zero LLM)。

Mean Reciprocal Rank — rewards earlier placement of relevant results.

Ref: llama_index.core.evaluation.retrieval.metrics — MRR
"""

from __future__ import annotations

from llama_index.core.evaluation.retrieval.metrics import MRR

from engine_v2.evaluation.models import MetricResult


def compute_mrr(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> MetricResult:
    """Compute MRR (0-1). Zero LLM calls.

    Args:
        retrieved_ids: Ordered list of chunk IDs from the retriever.
        expected_ids: Ground-truth chunk IDs from Golden Dataset.

    Returns:
        MetricResult with name="mrr".
    """
    if not expected_ids or not retrieved_ids:
        return MetricResult(name="mrr", score=0.0)

    metric = MRR()
    score = metric.compute(
        retrieved_ids=retrieved_ids,
        expected_ids=expected_ids,
    ).score

    return MetricResult(name="mrr", score=score)
