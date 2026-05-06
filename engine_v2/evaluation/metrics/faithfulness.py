"""faithfulness — 回答是否基于检索上下文（忠实度）。

Evaluates whether the generated answer is grounded in the retrieved
source context, detecting potential hallucinations.

Ref: llama_index.core.evaluation — FaithfulnessEvaluator
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.evaluation import FaithfulnessEvaluator

from engine_v2.evaluation.models import MetricResult


async def evaluate_faithfulness(
    question: str,
    answer: str,
    contexts: list[str],
    llm=None,
) -> MetricResult:
    """Evaluate answer faithfulness to retrieved context (0-1).

    Args:
        question: The user's question.
        answer: The generated answer text.
        contexts: Retrieved source context strings.
        llm: Optional LLM instance override.

    Returns:
        MetricResult with name="faithfulness" and score 0-1.
    """
    kwargs = {"llm": llm} if llm else {}
    evaluator = FaithfulnessEvaluator(**kwargs)

    result = await evaluator.aevaluate(
        query=question, response=answer, contexts=contexts,
    )

    logger.debug(
        "faithfulness={} — question={}",
        result.score, question[:60],
    )
    return MetricResult(
        name="faithfulness",
        score=result.score,
        feedback=result.feedback or "",
    )
