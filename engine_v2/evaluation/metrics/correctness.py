"""correctness — 回答的正确性（需要 Golden Dataset 参考答案）。

Evaluates the factual correctness of a generated answer by comparing
it against a ground-truth reference answer from the Golden Dataset.

Ref: llama_index.core.evaluation — CorrectnessEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import CorrectnessEvaluator

from engine_v2.evaluation.models import MetricResult


async def evaluate_correctness(
    question: str,
    answer: str,
    reference: str,
    llm=None,
    normalize: bool = True,
) -> MetricResult:
    """Evaluate answer correctness against a reference answer (0-1).

    CorrectnessEvaluator returns a 1-5 score. When normalize=True,
    the score is divided by 5.0 to produce a 0-1 scale.

    Args:
        question: The user's question.
        answer: The generated answer text.
        reference: Ground-truth expected answer from Golden Dataset.
        llm: Optional LLM instance override.
        normalize: If True, normalize 1-5 score to 0-1 scale.

    Returns:
        MetricResult with name="correctness" and score 0-1 (normalized).
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = CorrectnessEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, response=answer, reference=reference,
    )

    score = result.score
    if normalize and score is not None:
        score = score / 5.0

    logger.debug(
        "correctness={} — question={}",
        score, question[:60],
    )
    return MetricResult(
        name="correctness",
        score=score,
        feedback=result.feedback or "",
    )
