"""completeness — 回答的完整性。

Evaluates whether the answer fully covers all aspects of the question.
Uses a custom eval_template via CorrectnessEvaluator inheritance.

Status: Deprecated in favor of GuidelineEvaluator (EI-T3-01),
        but retained for backward compatibility.

Ref: llama_index.core.evaluation.correctness — CorrectnessEvaluator
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from llama_index.core.evaluation import CorrectnessEvaluator

from engine_v2.evaluation.models import MetricResult
from engine_v2.evaluation.prompts import COMPLETENESS_EVAL_TEMPLATE


class CompletenessEvaluator(CorrectnessEvaluator):
    """Evaluate whether an answer fully covers all aspects of the question.

    Inherits CorrectnessEvaluator with a custom eval_template.
    Outputs a 1–5 score where 5 = comprehensive coverage.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            eval_template=COMPLETENESS_EVAL_TEMPLATE,
            score_threshold=3.0,  # ≥3 = acceptable completeness
            **kwargs,
        )
        logger.debug("CompletenessEvaluator initialized")


async def evaluate_completeness(
    question: str,
    answer: str,
    reference: str = "",
    llm=None,
) -> MetricResult:
    """Evaluate answer completeness (1-5 scale).

    Args:
        question: The user's question.
        answer: The generated answer text.
        reference: Optional reference context.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="completeness" and score 1-5.
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = CompletenessEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, response=answer, reference=reference,
    )

    logger.debug(
        "completeness={} — question={}",
        result.score, question[:60],
    )
    return MetricResult(
        name="completeness",
        score=result.score,
        feedback=result.feedback or "",
    )
