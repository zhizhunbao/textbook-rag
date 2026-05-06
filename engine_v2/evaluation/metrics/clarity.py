"""clarity — 回答的清晰度与可读性。

Evaluates answer clarity, structure, and readability.
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
from engine_v2.evaluation.prompts import CLARITY_EVAL_TEMPLATE


class ClarityEvaluator(CorrectnessEvaluator):
    """Evaluate answer clarity, structure, and readability.

    Inherits CorrectnessEvaluator with a custom eval_template.
    Outputs a 1–5 score where 5 = exceptionally clear.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            eval_template=CLARITY_EVAL_TEMPLATE,
            score_threshold=3.0,  # ≥3 = acceptable clarity
            **kwargs,
        )
        logger.debug("ClarityEvaluator initialized")


async def evaluate_clarity(
    question: str,
    answer: str,
    reference: str = "",
    llm=None,
) -> MetricResult:
    """Evaluate answer clarity (1-5 scale).

    Args:
        question: The user's question.
        answer: The generated answer text.
        reference: Optional reference context (unused — judge clarity only).
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="clarity" and score 1-5.
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = ClarityEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, response=answer, reference=reference,
    )

    logger.debug(
        "clarity={} — question={}",
        result.score, question[:60],
    )
    return MetricResult(
        name="clarity",
        score=result.score,
        feedback=result.feedback or "",
    )
