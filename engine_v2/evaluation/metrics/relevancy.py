"""relevancy — 检索上下文与回答的相关性。

Evaluates whether the retrieved context is relevant to the query
and the generated answer addresses the query.

Ref: llama_index.core.evaluation — RelevancyEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import RelevancyEvaluator

from engine_v2.evaluation.models import MetricResult


async def evaluate_relevancy(
    question: str,
    answer: str,
    contexts: list[str],
    llm=None,
) -> MetricResult:
    """Evaluate source-answer relevancy (0-1).

    Args:
        question: The user's question.
        answer: The generated answer text.
        contexts: Retrieved source context strings.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="relevancy" and score 0-1.
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = RelevancyEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, response=answer, contexts=contexts,
    )

    logger.debug(
        "relevancy={} — question={}",
        result.score, question[:60],
    )
    return MetricResult(
        name="relevancy",
        score=result.score,
        feedback=result.feedback or "",
    )
