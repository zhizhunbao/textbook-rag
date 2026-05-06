"""context_relevancy — 检索文档块与查询的相关性。

Evaluates the quality of retrieved context chunks relative to the query,
independent of the generated answer.

Ref: llama_index.core.evaluation — ContextRelevancyEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import ContextRelevancyEvaluator

from engine_v2.evaluation.models import MetricResult


async def evaluate_context_relevancy(
    question: str,
    contexts: list[str],
    llm=None,
) -> MetricResult:
    """Evaluate context chunk relevancy to the query (0-1).

    Args:
        question: The user's question.
        contexts: Retrieved source context strings.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="context_relevancy" and score 0-1.
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = ContextRelevancyEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, contexts=contexts,
    )

    logger.debug(
        "context_relevancy={} — question={}",
        result.score, question[:60],
    )
    return MetricResult(
        name="context_relevancy",
        score=result.score,
        feedback=result.feedback or "",
    )
