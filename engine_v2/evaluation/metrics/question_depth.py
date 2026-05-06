"""question_depth — 问题认知深度评估。

Assesses the cognitive depth of a question on a 1-5 scale,
then maps to categorical labels: surface / understanding / synthesis.

Ref: llama_index.core.evaluation.correctness — CorrectnessEvaluator
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from llama_index.core.evaluation import CorrectnessEvaluator

from engine_v2.evaluation.models import DepthResult, MetricResult
from engine_v2.evaluation.prompts import DEPTH_EVAL_TEMPLATE


# ============================================================
# Constants
# ============================================================
# Depth label thresholds: score ≥ threshold → label
DEPTH_THRESHOLDS = {
    "synthesis": 4.0,
    "understanding": 2.5,
    # < 2.5 → "surface"
}


# ============================================================
# QuestionDepthEvaluator — inherits CorrectnessEvaluator
# ============================================================
class QuestionDepthEvaluator(CorrectnessEvaluator):
    """Evaluate question cognitive depth (1–5 scale).

    Inherits CorrectnessEvaluator with a custom eval_template
    that scores question depth instead of answer correctness.

    Business-layer threshold mapping:
        ≥ 4.0 → synthesis
        ≥ 2.5 → understanding
        < 2.5 → surface
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            eval_template=DEPTH_EVAL_TEMPLATE,
            score_threshold=2.5,  # passing = understanding or above
            **kwargs,
        )
        logger.debug("QuestionDepthEvaluator initialized")


def _score_to_depth_label(score: float) -> str:
    """Map numeric depth score to categorical label."""
    if score >= DEPTH_THRESHOLDS["synthesis"]:
        return "synthesis"
    if score >= DEPTH_THRESHOLDS["understanding"]:
        return "understanding"
    return "surface"


async def assess_question_depth(
    question: str,
    llm: Any = None,
) -> DepthResult:
    """Assess cognitive depth of a question.

    Uses QuestionDepthEvaluator (inherits CorrectnessEvaluator with
    custom eval_template) to score 1–5, then maps to depth label.

    Args:
        question: The question text.
        llm: Optional LLM instance override. Uses Settings.llm if None.

    Returns:
        DepthResult with depth label, numeric score, and reasoning.
    """
    eval_kwargs = {"llm": llm} if llm else {}
    evaluator = QuestionDepthEvaluator(**eval_kwargs)

    # CorrectnessEvaluator.aevaluate(query, response, reference)
    # We pass the question as both query and response (the thing being judged).
    # Reference provides the rubric context for the LLM.
    result = await evaluator.aevaluate(
        query=question,
        response=question,
        reference=(
            "A high-depth question requires synthesis across multiple concepts, "
            "critical evaluation, or creative application. "
            "A low-depth question merely asks for definitions or factual recall."
        ),
    )

    score = result.score or 1.0
    depth = _score_to_depth_label(score)

    logger.info(
        "Question depth: {} (score={}) — {}",
        depth, score, question[:80],
    )
    return DepthResult(
        question=question,
        depth=depth,
        score=score,
        reasoning=result.feedback or "",
    )


async def evaluate_question_depth(
    question: str,
    llm: Any = None,
) -> MetricResult:
    """Evaluate question depth returning a MetricResult (unified interface).

    Args:
        question: The question text.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="question_depth", score 1-5, label.
    """
    depth_result = await assess_question_depth(question, llm=llm)
    return MetricResult(
        name="question_depth",
        score=depth_result.score,
        feedback=depth_result.reasoning,
        label=depth_result.depth,
    )
