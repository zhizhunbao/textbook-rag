"""aggregation — Compute aggregate scores and pass/fail status.

Extracted from evaluator.py (compute_aggregate_scores) and
history.py (_compute_status) to separate scoring logic from
evaluation execution.
"""

from __future__ import annotations

from engine_v2.evaluation.models import FullEvalResult


def compute_aggregate_scores(
    result: FullEvalResult,
    weights: dict[str, float] | None = None,
) -> FullEvalResult:
    """Compute aggregate scores (rag, llm, answer, overall) in place.

    Args:
        result: FullEvalResult with individual dimension scores filled.
        weights: Optional {"rag": w, "llm": w, "answer": w} for overall.
            Defaults to {"rag": 0.3, "llm": 0.3, "answer": 0.4}.

    Returns:
        The same result object with aggregate fields populated.
    """
    if weights is None:
        weights = {"rag": 0.3, "llm": 0.3, "answer": 0.4}

    # RAG score = mean(context_relevancy, relevancy)
    rag_dims = [v for v in (result.context_relevancy, result.relevancy) if v is not None]
    result.rag_score = (sum(rag_dims) / len(rag_dims)) if rag_dims else None

    # LLM score = faithfulness
    result.llm_score = result.faithfulness

    # Answer score = mean(correctness, answer_relevancy, completeness, clarity)
    # guidelines_pass is a separate boolean check — not included in numeric average
    ans_dims = [
        v for v in (
            result.correctness, result.answer_relevancy,
            result.completeness, result.clarity,
        ) if v is not None
    ]

    result.answer_score = (sum(ans_dims) / len(ans_dims)) if ans_dims else None

    # Overall = weighted average of group scores (including IR when available)
    group_scores = []
    group_weights = []
    for key, score in [("rag", result.rag_score), ("llm", result.llm_score),
                       ("answer", result.answer_score)]:
        if score is not None:
            group_scores.append(score)
            group_weights.append(weights.get(key, 1.0))

    # IR score participates in overall when Golden Dataset provides it (EI-T2)
    if result.ir_score is not None:
        group_scores.append(result.ir_score)
        group_weights.append(weights.get("ir", 0.2))

    if group_scores:
        total_w = sum(group_weights)
        result.overall_score = round(
            sum(s * w for s, w in zip(group_scores, group_weights)) / total_w, 4
        )

    return result


def compute_status(result: FullEvalResult) -> str:
    """Determine pass/fail status based on configurable thresholds.

    Rules (UEP-T2-02):
        - Need at least faithfulness + answer_score to judge
        - faithfulness >= threshold AND answer_score >= threshold → "pass"
        - Otherwise → "fail"
        - If both scores are None → "pending"
    """
    from engine_v2.settings import EVAL_PASS_ANSWER_SCORE, EVAL_PASS_FAITHFULNESS

    # Fallback: if answer_score is None but answer_relevancy exists, use that
    effective_answer = result.answer_score
    if effective_answer is None:
        effective_answer = result.answer_relevancy

    if result.faithfulness is None and effective_answer is None:
        return "pending"

    # If we have at least one, we can make a judgement
    faith_ok = result.faithfulness is None or result.faithfulness >= EVAL_PASS_FAITHFULNESS
    answer_ok = effective_answer is None or effective_answer >= EVAL_PASS_ANSWER_SCORE

    if faith_ok and answer_ok:
        return "pass"

    return "fail"
