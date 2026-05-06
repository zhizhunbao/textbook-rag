"""pairwise — A/B 对比评估。

Compares two RAG pipeline answers to the same question using
PairwiseComparisonEvaluator with consensus enforcement.

Ref: llama_index.core.evaluation.pairwise — PairwiseComparisonEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import PairwiseComparisonEvaluator

from engine_v2.evaluation.models import (
    BatchCompareResult,
    CompareItem,
    MetricResult,
    PairwiseResult,
)


def _score_to_winner(score: float | None) -> str:
    """Map numeric score to winner label."""
    if score is None:
        return "tie"
    if score > 0.5:
        return "A"
    if score < 0.5:
        return "B"
    return "tie"


def _build_eval_kwargs(judge_model: str | None) -> dict:
    """Build kwargs for the evaluator, optionally resolving a judge LLM."""
    if not judge_model:
        return {}
    from engine_v2.llms.resolver import resolve_llm

    return {"llm": resolve_llm(model=judge_model)}


async def compare_answers(
    question: str,
    answer_a: str,
    answer_b: str,
    reference: str | None = None,
    judge_model: str | None = None,
) -> PairwiseResult:
    """Compare two answers using PairwiseComparisonEvaluator.

    Uses enforce_consensus=True to flip answer order and run twice,
    eliminating position bias.

    Args:
        question: The query both answers respond to.
        answer_a: First pipeline's answer.
        answer_b: Second pipeline's answer.
        reference: Optional ground-truth answer from Golden Dataset.
        judge_model: Optional LLM model for the judge.

    Returns:
        PairwiseResult with winner, score, and reasoning.
    """
    eval_kwargs = _build_eval_kwargs(judge_model)

    evaluator = PairwiseComparisonEvaluator(
        enforce_consensus=True,
        **eval_kwargs,
    )

    logger.info(
        "Pairwise comparison — question={}, judge={}",
        question[:60], judge_model or "default",
    )

    result = await evaluator.aevaluate(
        query=question,
        response=answer_a,
        second_response=answer_b,
        reference=reference,
    )

    if result.invalid_result:
        logger.warning(
            "Pairwise judge output unparseable: {}",
            result.invalid_reason,
        )
        return PairwiseResult(
            question=question,
            winner="tie",
            score=0.5,
            reasoning=result.feedback or result.invalid_reason or "",
            invalid=True,
        )

    winner = _score_to_winner(result.score)

    logger.info(
        "Pairwise result — winner={}, score={}, question={}",
        winner, result.score, question[:60],
    )
    return PairwiseResult(
        question=question,
        winner=winner,
        score=result.score if result.score is not None else 0.5,
        reasoning=result.feedback or "",
    )


async def compare_batch(
    items: list[CompareItem],
    judge_model: str | None = None,
) -> BatchCompareResult:
    """Run pairwise comparison on multiple question/answer pairs.

    Args:
        items: List of CompareItem (question + two answers).
        judge_model: Optional LLM model for the judge.

    Returns:
        BatchCompareResult with per-item results and summary counts.
    """
    results: list[PairwiseResult] = []

    for i, item in enumerate(items):
        try:
            r = await compare_answers(
                question=item.question,
                answer_a=item.answer_a,
                answer_b=item.answer_b,
                reference=item.reference,
                judge_model=judge_model,
            )
        except Exception as exc:
            logger.error("Batch compare failed for item {}: {}", i, exc)
            r = PairwiseResult(
                question=item.question,
                winner="tie",
                score=0.5,
                reasoning=f"Error: {exc}",
                invalid=True,
            )
        results.append(r)
        logger.debug("Batch compare progress: {}/{}", i + 1, len(items))

    a_wins = sum(1 for r in results if r.winner == "A")
    b_wins = sum(1 for r in results if r.winner == "B")
    ties = sum(1 for r in results if r.winner == "tie")
    invalid_count = sum(1 for r in results if r.invalid)

    logger.info(
        "Batch compare done — A={}, B={}, tie={}, invalid={}, total={}",
        a_wins, b_wins, ties, invalid_count, len(results),
    )

    return BatchCompareResult(
        results=results,
        a_wins=a_wins,
        b_wins=b_wins,
        ties=ties,
        total=len(results),
        invalid_count=invalid_count,
    )


async def evaluate_pairwise(
    question: str,
    answer_a: str,
    answer_b: str,
    reference: str | None = None,
    judge_model: str | None = None,
) -> MetricResult:
    """Evaluate pairwise comparison returning a MetricResult (unified interface).

    Returns:
        MetricResult with name="pairwise", score (1.0=A, 0.0=B, 0.5=tie), label=winner.
    """
    result = await compare_answers(question, answer_a, answer_b, reference, judge_model)
    return MetricResult(
        name="pairwise",
        score=result.score,
        feedback=result.reasoning,
        label=result.winner,
    )
