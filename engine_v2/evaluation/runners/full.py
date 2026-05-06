"""full — Four-category full evaluation (RAG/LLM/Answer/Question).

The most comprehensive evaluation runner. Composes all metric files,
Golden Dataset matching, IR metrics, routing assessment, and suggestions.
"""

from __future__ import annotations

from loguru import logger

from engine_v2.evaluation.models import FullEvalResult
from engine_v2.evaluation.metrics.faithfulness import evaluate_faithfulness
from engine_v2.evaluation.metrics.relevancy import evaluate_relevancy
from engine_v2.evaluation.metrics.context_relevancy import evaluate_context_relevancy
from engine_v2.evaluation.metrics.answer_relevancy import evaluate_answer_relevancy
from engine_v2.evaluation.metrics.correctness import evaluate_correctness
from engine_v2.evaluation.metrics.guidelines import evaluate_guidelines
from engine_v2.evaluation.metrics.question_depth import assess_question_depth
from engine_v2.evaluation.metrics.ir.aggregate import compute_all_ir_metrics
from engine_v2.evaluation.aggregation import compute_aggregate_scores, compute_status
from engine_v2.evaluation.routing import assess_routing_correctness
from engine_v2.evaluation.persistence.queries import (
    extract_contexts,
    fetch_query_by_id,
)
from engine_v2.evaluation.persistence.evaluations import persist_full_evaluation


async def full_evaluate(
    query_id: int,
    model: str | None = None,
    judge_model: str | None = None,
) -> FullEvalResult:
    """Run four-category evaluation on a stored query record.

    Args:
        query_id: Payload Queries record ID.
        model: Optional LLM model override.
        judge_model: Optional separate LLM for evaluation (EI-T3-03).

    Returns:
        FullEvalResult with per-dimension scores, aggregates, and feedback.
    """
    from engine_v2.llms.resolver import resolve_llm
    from engine_v2.evaluation.persistence.golden import match_golden_record

    effective_judge = judge_model or model
    llm_instance = resolve_llm(model=effective_judge)

    if effective_judge:
        effective_judge_name = effective_judge
    else:
        from engine_v2.settings import AZURE_OAI_DEPLOYMENT, OLLAMA_MODEL
        from engine_v2.llms.resolver import is_azure_configured
        effective_judge_name = AZURE_OAI_DEPLOYMENT if is_azure_configured() else OLLAMA_MODEL

    record = await fetch_query_by_id(query_id)
    contexts = extract_contexts(record.sources)
    feedback: dict[str, str] = {}

    # ── ❓ Question ──
    try:
        depth_r = await assess_question_depth(record.question, llm=llm_instance)
        q_depth, q_depth_score, q_depth_reasoning = depth_r.depth, depth_r.score, depth_r.reasoning
        feedback["question_depth"] = q_depth_reasoning
    except Exception as exc:
        logger.warning("Question depth failed: {}", exc)
        q_depth, q_depth_score, q_depth_reasoning = None, None, ""

    # ── 🤖 LLM ──
    faith_r = await evaluate_faithfulness(record.question, record.answer, contexts, llm=llm_instance)
    feedback["faithfulness"] = faith_r.feedback

    # ── 🔍 RAG ──
    relev_r = await evaluate_relevancy(record.question, record.answer, contexts, llm=llm_instance)
    ctx_r = await evaluate_context_relevancy(record.question, contexts, llm=llm_instance)
    feedback["relevancy"] = relev_r.feedback
    feedback["context_relevancy"] = ctx_r.feedback

    # ── 📝 Answer ──
    ans_r = await evaluate_answer_relevancy(record.question, record.answer, llm=llm_instance)
    feedback["answer_relevancy"] = ans_r.feedback

    guide_r = await evaluate_guidelines(record.question, record.answer, contexts, llm=llm_instance)
    feedback["guidelines"] = guide_r.feedback

    # ── Golden Dataset + IR ──
    golden_match = await match_golden_record(record.question)
    ir_metrics, correctness_score = {}, None
    llm_calls = 6

    if golden_match:
        retrieved_ids = [s["chunk_id"] for s in record.sources if s.get("chunk_id")]
        ir_result = compute_all_ir_metrics(retrieved_ids, golden_match.expected_chunk_ids)
        ir_metrics = ir_result.to_dict()
        try:
            corr_r = await evaluate_correctness(record.question, record.answer, golden_match.expected_answer, llm=llm_instance)
            correctness_score = corr_r.score
            feedback["correctness"] = corr_r.feedback
        except Exception as exc:
            feedback["correctness"] = f"evaluator error: {exc}"
        llm_calls += 1

    # ── Retrieval stats ──
    bm25_hits = sum(1 for s in record.sources if s.get("retrieval_source") == "bm25")
    both_hits = sum(1 for s in record.sources if s.get("retrieval_source") == "both")
    vector_hits = len(record.sources) - bm25_hits - both_hits
    has_bm25 = bm25_hits > 0 or both_hits > 0

    # ── Assemble ──
    result = FullEvalResult(
        query_id=record.id, question=record.question, answer=record.answer,
        context_relevancy=ctx_r.score, relevancy=relev_r.score,
        faithfulness=faith_r.score,
        answer_relevancy=ans_r.score, correctness=correctness_score,
        guidelines_pass=guide_r.passed, guidelines_feedback=guide_r.feedback,
        question_depth=q_depth, question_depth_score=q_depth_score,
        question_depth_reasoning=q_depth_reasoning or "",
        judge_model=effective_judge_name,
        retrieval_mode="hybrid" if has_bm25 else "vector_only",
        bm25_hit_count=bm25_hits, vector_hit_count=vector_hits, both_hit_count=both_hits,
        hit_rate=ir_metrics.get("hit_rate"), mrr=ir_metrics.get("mrr"),
        precision_at_k=ir_metrics.get("precision_at_k"), recall_at_k=ir_metrics.get("recall_at_k"),
        ndcg=ir_metrics.get("ndcg"), ir_score=ir_metrics.get("ir_score"),
        golden_match_id=golden_match.id if golden_match else None,
        answer_model=getattr(record, 'model', None), llm_calls=llm_calls,
        feedback=feedback,
    )

    compute_aggregate_scores(result)
    result.status = compute_status(result)
    result.routing_decision, result.routing_correct, result.routing_reasoning = assess_routing_correctness(result)

    from engine_v2.evaluation.suggestions import generate_suggestions
    result.suggestions = [s.to_dict() for s in generate_suggestions({
        "faithfulness": result.faithfulness, "relevancy": result.relevancy,
        "contextRelevancy": result.context_relevancy, "answerRelevancy": result.answer_relevancy,
        "completeness": result.completeness, "questionDepth": result.question_depth,
        "overallScore": result.overall_score,
    })]

    eval_id = await persist_full_evaluation(result)
    logger.info("Full-evaluated query_id={} — overall={}, status={} → eval_id={}", query_id, result.overall_score, result.status, eval_id)
    return result
