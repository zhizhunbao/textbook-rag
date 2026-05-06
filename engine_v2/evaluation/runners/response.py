"""response — 5-dimensional response evaluation (re-runs RAG pipeline).

Evaluates a single query by running it through the RAG pipeline,
then scoring the response on 5 dimensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from llama_index.core.evaluation import BatchEvalRunner

from engine_v2.evaluation.models import EvalResult
from engine_v2.evaluation.metrics.faithfulness import evaluate_faithfulness
from engine_v2.evaluation.metrics.relevancy import evaluate_relevancy
from engine_v2.evaluation.metrics.context_relevancy import evaluate_context_relevancy
from engine_v2.evaluation.metrics.answer_relevancy import evaluate_answer_relevancy

if TYPE_CHECKING:
    from llama_index.core.query_engine import RetrieverQueryEngine


async def evaluate_response(
    query: str,
    engine: RetrieverQueryEngine | None = None,
) -> EvalResult:
    """Evaluate a single query through the full RAG pipeline (5-dimensional).

    Runs the query, then evaluates the response with:
        - faithfulness  (is answer grounded in context?)
        - relevancy     (is context relevant to query?)
        - context_relevancy  (context quality score)
        - answer_relevancy   (answer-to-query relevance score)

    Args:
        query: The question to evaluate.
        engine: Optional pre-built query engine.

    Returns:
        EvalResult with 5-dimensional scores and feedback.
    """
    if engine is None:
        from engine_v2.query_engine.citation import get_query_engine
        engine = get_query_engine()

    response = engine.query(query)

    # Extract context strings for context-based evaluators
    contexts = [n.node.get_content() for n in response.source_nodes]
    answer = str(response)

    # Run all evaluations via individual metric files
    faith_r = await evaluate_faithfulness(query, answer, contexts)
    relev_r = await evaluate_relevancy(query, answer, contexts)
    ctx_r = await evaluate_context_relevancy(query, contexts)
    ans_r = await evaluate_answer_relevancy(query, answer)

    result = EvalResult(
        query=query,
        answer=answer,
        faithfulness=faith_r.score,
        relevancy=relev_r.score,
        context_relevancy=ctx_r.score,
        answer_relevancy=ans_r.score,
        feedback={
            "faithfulness": faith_r.feedback,
            "relevancy": relev_r.feedback,
            "context_relevancy": ctx_r.feedback,
            "answer_relevancy": ans_r.feedback,
        },
    )
    logger.info(
        "Evaluated query — faith={}, relev={}, ctx_relev={}, ans_relev={}",
        result.faithfulness,
        result.relevancy,
        result.context_relevancy,
        result.answer_relevancy,
    )
    return result


async def evaluate_dataset(
    queries: list[str],
    reference_answers: list[str] | None = None,
    engine: RetrieverQueryEngine | None = None,
) -> list[EvalResult]:
    """Batch-evaluate multiple queries using LlamaIndex BatchEvalRunner.

    Args:
        queries: List of questions to evaluate.
        reference_answers: Optional ground-truth answers (enables CorrectnessEvaluator).
        engine: Optional pre-built query engine.

    Returns:
        List of EvalResult, one per query.
    """
    from llama_index.core.evaluation import (
        AnswerRelevancyEvaluator,
        ContextRelevancyEvaluator,
        CorrectnessEvaluator,
        FaithfulnessEvaluator,
        RelevancyEvaluator,
    )

    if engine is None:
        from engine_v2.query_engine.citation import get_query_engine
        engine = get_query_engine()

    evaluators: dict = {
        "faithfulness": FaithfulnessEvaluator(),
        "relevancy": RelevancyEvaluator(),
        "correctness": CorrectnessEvaluator(),
        "context_relevancy": ContextRelevancyEvaluator(),
        "answer_relevancy": AnswerRelevancyEvaluator(),
    }
    if not reference_answers:
        # Remove correctness — requires reference answers
        evaluators.pop("correctness", None)

    runner = BatchEvalRunner(evaluators=evaluators, show_progress=True)
    eval_results = await runner.aevaluate_queries(
        query_engine=engine,
        queries=queries,
    )

    results: list[EvalResult] = []
    for i, q in enumerate(queries):
        scores: dict[str, float | None] = {}
        feedback: dict[str, str] = {}

        for key in ("faithfulness", "relevancy", "correctness",
                     "context_relevancy", "answer_relevancy"):
            if key in eval_results and i < len(eval_results[key]):
                r = eval_results[key][i]
                scores[key] = r.score
                feedback[key] = r.feedback or ""
            else:
                scores[key] = None

        results.append(EvalResult(
            query=q,
            answer="",  # filled internally by batch runner
            faithfulness=scores["faithfulness"],
            relevancy=scores["relevancy"],
            correctness=scores["correctness"],
            context_relevancy=scores["context_relevancy"],
            answer_relevancy=scores["answer_relevancy"],
            feedback=feedback,
        ))

    logger.info("Batch-evaluated {} queries (5-dimensional)", len(results))
    return results
