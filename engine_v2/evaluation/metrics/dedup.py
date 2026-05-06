"""dedup — 问题语义去重。

Uses SemanticSimilarityEvaluator to detect if a new question
duplicates any previously asked question.

Ref: llama_index.core.evaluation.semantic_similarity — SemanticSimilarityEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import SemanticSimilarityEvaluator

from engine_v2.evaluation.models import DedupResult, MetricResult


# Deduplication similarity threshold
DEDUP_SIMILARITY_THRESHOLD = 0.85


async def question_dedup(
    question: str,
    history_questions: list[str],
    threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> DedupResult:
    """Detect if a question duplicates any in the history set.

    Uses LlamaIndex SemanticSimilarityEvaluator (internally uses
    Settings.embed_model for vectorization + cosine similarity).

    Args:
        question: The new question to check.
        history_questions: List of previously asked question texts.
        threshold: Similarity threshold for flagging as duplicate.

    Returns:
        DedupResult with duplicate flag, most similar match, and suggestion.
    """
    if not history_questions:
        return DedupResult(
            is_duplicate=False,
            most_similar=None,
            similarity_score=0.0,
            suggestion="",
        )

    sim_eval = SemanticSimilarityEvaluator(
        similarity_threshold=threshold,
    )

    best_score = 0.0
    best_match: str | None = None

    for hist_q in history_questions:
        result = await sim_eval.aevaluate(
            response=question,
            reference=hist_q,
        )
        score = result.score or 0.0
        if score > best_score:
            best_score = score
            best_match = hist_q

    is_dup = best_score >= threshold

    suggestion = ""
    if is_dup and best_match:
        suggestion = (
            f"This question is very similar to: \"{best_match[:120]}\" "
            f"(similarity: {best_score:.2f}). "
            "Consider asking a deeper follow-up, e.g. comparing concepts, "
            "applying to a different scenario, or evaluating trade-offs."
        )

    logger.info(
        "Dedup check — is_dup={}, best_score={:.3f}, question={}",
        is_dup, best_score, question[:80],
    )
    return DedupResult(
        is_duplicate=is_dup,
        most_similar=best_match,
        similarity_score=best_score,
        suggestion=suggestion,
    )


async def evaluate_dedup(
    question: str,
    history_questions: list[str],
    threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> MetricResult:
    """Evaluate question dedup returning a MetricResult (unified interface).

    Args:
        question: The new question to check.
        history_questions: Previously asked questions.
        threshold: Similarity threshold.

    Returns:
        MetricResult with name="dedup", score = similarity, passed = not duplicate.
    """
    result = await question_dedup(question, history_questions, threshold)
    return MetricResult(
        name="dedup",
        score=result.similarity_score,
        feedback=result.suggestion,
        passed=not result.is_duplicate,
    )
