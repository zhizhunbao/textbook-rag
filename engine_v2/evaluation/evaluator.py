"""RAG evaluation — faithfulness, relevancy, correctness.

Aligns with llama_index.core.evaluation module.
Uses LlamaIndex's built-in evaluators:
    - FaithfulnessEvaluator: is the answer grounded in the context?
    - RelevancyEvaluator: is the retrieved context relevant to the query?
    - CorrectnessEvaluator: is the answer factually correct? (needs reference)
    - BatchEvalRunner: run multiple evaluators in parallel
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from llama_index.core.evaluation import (
    BatchEvalRunner,
    CorrectnessEvaluator,
    FaithfulnessEvaluator,
    RelevancyEvaluator,
)
from llama_index.core.query_engine import CitationQueryEngine

from engine_v2.query_engine.citation import get_query_engine

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Structured evaluation result for one query."""

    query: str
    answer: str
    faithfulness: float | None = None
    relevancy: float | None = None
    correctness: float | None = None
    feedback: dict[str, str] = field(default_factory=dict)


async def evaluate_response(
    query: str,
    engine: CitationQueryEngine | None = None,
) -> EvalResult:
    """Evaluate a single query through the full RAG pipeline.

    Runs the query, then evaluates the response with:
        - FaithfulnessEvaluator (is answer grounded in context?)
        - RelevancyEvaluator (is context relevant to query?)

    Args:
        query: The question to evaluate.
        engine: Optional pre-built query engine.

    Returns:
        EvalResult with scores and feedback.
    """
    if engine is None:
        engine = get_query_engine()

    response = engine.query(query)

    faithfulness_eval = FaithfulnessEvaluator()
    relevancy_eval = RelevancyEvaluator()

    faith_result = await faithfulness_eval.aevaluate_response(
        query=query, response=response
    )
    relev_result = await relevancy_eval.aevaluate_response(
        query=query, response=response
    )

    return EvalResult(
        query=query,
        answer=str(response),
        faithfulness=faith_result.score,
        relevancy=relev_result.score,
        feedback={
            "faithfulness": faith_result.feedback or "",
            "relevancy": relev_result.feedback or "",
        },
    )


async def evaluate_dataset(
    queries: list[str],
    reference_answers: list[str] | None = None,
    engine: CitationQueryEngine | None = None,
) -> list[EvalResult]:
    """Batch-evaluate multiple queries using LlamaIndex BatchEvalRunner.

    Args:
        queries: List of questions to evaluate.
        reference_answers: Optional ground-truth answers (enables CorrectnessEvaluator).
        engine: Optional pre-built query engine.

    Returns:
        List of EvalResult, one per query.
    """
    if engine is None:
        engine = get_query_engine()

    evaluators: dict[str, Any] = {
        "faithfulness": FaithfulnessEvaluator(),
        "relevancy": RelevancyEvaluator(),
    }
    if reference_answers:
        evaluators["correctness"] = CorrectnessEvaluator()

    runner = BatchEvalRunner(evaluators=evaluators, show_progress=True)
    eval_results = await runner.aevaluate_queries(
        query_engine=engine,
        queries=queries,
    )

    results = []
    for i, q in enumerate(queries):
        faith_score = None
        relev_score = None
        correct_score = None
        feedback: dict[str, str] = {}

        if "faithfulness" in eval_results and i < len(eval_results["faithfulness"]):
            r = eval_results["faithfulness"][i]
            faith_score = r.score
            feedback["faithfulness"] = r.feedback or ""

        if "relevancy" in eval_results and i < len(eval_results["relevancy"]):
            r = eval_results["relevancy"][i]
            relev_score = r.score
            feedback["relevancy"] = r.feedback or ""

        if "correctness" in eval_results and i < len(eval_results["correctness"]):
            r = eval_results["correctness"][i]
            correct_score = r.score
            feedback["correctness"] = r.feedback or ""

        results.append(EvalResult(
            query=q,
            answer="",  # filled by batch runner internally
            faithfulness=faith_score,
            relevancy=relev_score,
            correctness=correct_score,
            feedback=feedback,
        ))

    logger.info("Evaluated %d queries", len(results))
    return results
