"""guidelines — 回答质量指南合规性检查。

Evaluates whether the answer complies with configurable quality guidelines.
Returns a boolean pass/fail result instead of a numeric score.

Replaces deprecated completeness + clarity evaluators (EI-T3-01).

Ref: llama_index.core.evaluation — GuidelineEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import GuidelineEvaluator

from engine_v2.evaluation.models import MetricResult


async def evaluate_guidelines(
    question: str,
    answer: str,
    contexts: list[str],
    guidelines: str | None = None,
    llm=None,
) -> MetricResult:
    """Evaluate answer compliance with quality guidelines (pass/fail).

    Args:
        question: The user's question.
        answer: The generated answer text.
        contexts: Retrieved source context strings.
        guidelines: Quality guidelines string. Uses QUALITY_GUIDELINES
            from settings if not provided.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="guidelines", passed=True/False.
    """
    if guidelines is None:
        from engine_v2.settings import QUALITY_GUIDELINES
        guidelines = QUALITY_GUIDELINES

    kwargs = {"llm": llm} if llm else {}
    evaluator = GuidelineEvaluator(guidelines=guidelines, **kwargs)

    try:
        result = await evaluator.aevaluate(
            query=question, response=answer, contexts=contexts,
        )
        passed = result.score is not None and result.score > 0.5
        feedback = result.feedback or ""
    except Exception as exc:
        logger.warning("GuidelineEvaluator failed: {}", exc)
        passed = None
        feedback = f"evaluator error: {exc}"

    logger.debug(
        "guidelines={} — question={}",
        passed, question[:60],
    )
    return MetricResult(
        name="guidelines",
        score=1.0 if passed else 0.0 if passed is not None else None,
        feedback=feedback,
        passed=passed,
    )
