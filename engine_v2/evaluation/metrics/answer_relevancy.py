"""answer_relevancy — 回答与查询的相关性。

Evaluates how well the generated answer addresses the user's query,
independent of the retrieved context.

Ref: llama_index.core.evaluation — AnswerRelevancyEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import AnswerRelevancyEvaluator

from engine_v2.evaluation.models import MetricResult


async def evaluate_answer_relevancy(
    question: str,
    answer: str,
    llm=None,
) -> MetricResult:
    """Evaluate answer-to-query relevance (0-1).

    Args:
        question: The user's question.
        answer: The generated answer text.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="answer_relevancy" and score 0-1.
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = AnswerRelevancyEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, response=answer,
    )

    logger.debug(
        "answer_relevancy={} — question={}",
        result.score, question[:60],
    )
    return MetricResult(
        name="answer_relevancy",
        score=result.score,
        feedback=result.feedback or "",
    )
