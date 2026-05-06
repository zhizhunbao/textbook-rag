"""single — Evaluate a single existing query from Payload (no RAG re-run).

Fetches stored (question, answer, sources) and runs three evaluation groups:
    1. Question quality  — cognitive depth (1-5)
    2. Answer quality    — faithfulness + answer_relevancy
    3. Citation quality  — context_relevancy + relevancy
"""

from __future__ import annotations

from loguru import logger

from engine_v2.evaluation.models import HistoryEvalResult
from engine_v2.evaluation.metrics.faithfulness import evaluate_faithfulness
from engine_v2.evaluation.metrics.relevancy import evaluate_relevancy
from engine_v2.evaluation.metrics.context_relevancy import evaluate_context_relevancy
from engine_v2.evaluation.metrics.answer_relevancy import evaluate_answer_relevancy
from engine_v2.evaluation.metrics.question_depth import assess_question_depth
from engine_v2.evaluation.persistence.queries import (
    extract_contexts,
    fetch_query_by_id,
)
from engine_v2.evaluation.persistence.evaluations import persist_evaluation


async def evaluate_single_from_query(
    query_id: int,
    model: str | None = None,
) -> HistoryEvalResult:
    """Evaluate a single existing query from Payload Queries.

    Fetches the stored (question, answer, sources), then runs
    three evaluation groups. Does NOT re-run the RAG pipeline.

    Args:
        query_id: Payload Queries record ID.
        model: Optional LLM model override.

    Returns:
        HistoryEvalResult with grouped scores + feedback.
    """
    from engine_v2.llms.resolver import resolve_llm

    # Resolve LLM for evaluators
    llm_instance = resolve_llm(model=model) if model else None

    record = await fetch_query_by_id(query_id)
    contexts = extract_contexts(record.sources)

    logger.info(
        "Evaluating query_id={} — question={}, contexts={}, model={}",
        query_id, record.question[:60], len(contexts), model or 'default',
    )

    # ── 1. Question quality ─────────────────────────────────
    try:
        depth_r = await assess_question_depth(record.question, llm=llm_instance)
        q_depth = depth_r.depth
        q_depth_score = depth_r.score  # 1.0-5.0 raw
        q_depth_reasoning = depth_r.reasoning
    except Exception as exc:
        logger.warning("Question depth assessment failed: {}", exc)
        q_depth = None
        q_depth_score = None
        q_depth_reasoning = ""

    # ── 2. Answer quality ───────────────────────────────────
    faith_r = await evaluate_faithfulness(
        record.question, record.answer, contexts, llm=llm_instance,
    )
    ans_r = await evaluate_answer_relevancy(
        record.question, record.answer, llm=llm_instance,
    )

    # ── 3. Citation quality ─────────────────────────────────
    relev_r = await evaluate_relevancy(
        record.question, record.answer, contexts, llm=llm_instance,
    )
    ctx_r = await evaluate_context_relevancy(
        record.question, contexts, llm=llm_instance,
    )

    result = HistoryEvalResult(
        query_id=record.id,
        question=record.question,
        answer=record.answer,
        # Question
        question_depth=q_depth,
        question_depth_score=q_depth_score,
        question_depth_reasoning=q_depth_reasoning,
        # Answer
        faithfulness=faith_r.score,
        answer_relevancy=ans_r.score,
        # Citation
        context_relevancy=ctx_r.score,
        relevancy=relev_r.score,
        feedback={
            "faithfulness": faith_r.feedback,
            "answer_relevancy": ans_r.feedback,
            "context_relevancy": ctx_r.feedback,
            "relevancy": relev_r.feedback,
            "question_depth": q_depth_reasoning,
        },
    )

    # Persist to Evaluations collection
    eval_id = await persist_evaluation(result)
    logger.info(
        "Evaluated query_id={} — depth={}, faith={}, ans_rel={}, ctx={}, relev={} → eval_id={}",
        query_id, result.question_depth, result.faithfulness,
        result.answer_relevancy, result.context_relevancy, result.relevancy,
        eval_id,
    )
    return result
