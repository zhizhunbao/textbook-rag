"""evaluation routes — Unified evaluation hub endpoints.

Endpoints:
    POST   /engine/evaluation/single                   — 5-dimensional single query evaluation
    POST   /engine/evaluation/batch                    — batch evaluation via BatchEvalRunner
    POST   /engine/evaluation/quality                  — question cognitive depth assessment
    POST   /engine/evaluation/dedup                    — question deduplication check
    POST   /engine/evaluation/evaluate-history         — evaluate existing query (no re-run)
    POST   /engine/evaluation/evaluate-batch           — batch-evaluate recent queries
    POST   /engine/evaluation/full-evaluate            — four-category evaluation (EV2-T2)
    POST   /engine/evaluation/auto-evaluate            — auto-eval trigger (EV2-T3)
    POST   /engine/evaluation/generate-golden-dataset  — generate Golden Dataset QA pairs (EI-T1-03)
    POST   /engine/evaluation/compare                  — pairwise A/B comparison (EI-T4-01)
    POST   /engine/evaluation/compare-batch             — batch A/B comparison (EI-T4-02)
    POST   /engine/evaluation/retrieval-eval           — retrieval recall evaluation on QuestionSet (QD-10)
    GET    /engine/evaluation/queries                  — list recent Queries for evaluation

Ref: llama_index.core.evaluation — CorrectnessEvaluator, SemanticSimilarityEvaluator,
     PairwiseComparisonEvaluator

Cross-model evaluation (EI-T3-03):
    full-evaluate accepts optional judge_model to use a different LLM as
    evaluation judge, eliminating self-evaluation bias.
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from engine_v2.evaluation.evaluator import (
    assess_question_depth,
    evaluate_dataset,
    evaluate_response,
    question_dedup,
)
from engine_v2.evaluation.history import (
    evaluate_batch_from_queries,
    evaluate_single_from_query,
    full_evaluate,
    auto_evaluate_query,
    _fetch_recent_queries,
)

# ============================================================
# Router
# ============================================================
router = APIRouter(prefix="/evaluation", tags=["evaluation"])


# ============================================================
# Request / Response models
# ============================================================
class EvalSingleRequest(BaseModel):
    """Single query for 5-dimensional evaluation."""

    question: str


class EvalBatchRequest(BaseModel):
    """Batch queries for 5-dimensional evaluation."""

    questions: list[str]
    reference_answers: list[str] | None = None


class QualityRequest(BaseModel):
    """Question cognitive depth assessment request."""

    question: str


class DedupRequest(BaseModel):
    """Question deduplication check request."""

    question: str
    history_questions: list[str]
    threshold: float = 0.85


class HistoryEvalRequest(BaseModel):
    """Evaluate a single existing query by Payload ID."""

    query_id: int
    model: str | None = None  # LLM model override for evaluation


class BatchHistoryEvalRequest(BaseModel):
    """Batch-evaluate recent queries from Payload."""

    n_recent: int = 20
    batch_id: str | None = None


class FullEvalRequest(BaseModel):
    """Four-category full evaluation request (EV2-T2/T3)."""

    query_id: int
    model: str | None = None
    judge_model: str | None = None  # Cross-model: separate judge LLM (EI-T3-03)


class AutoEvalRequest(BaseModel):
    """Auto-evaluation trigger request (EV2-T3)."""

    query_id: int


class GenerateGoldenDatasetRequest(BaseModel):
    """Request to generate Golden Dataset QA pairs (EI-T1-03)."""

    book_id: str
    n_questions: int = 50
    num_questions_per_chunk: int = 2


class PairwiseRequest(BaseModel):
    """Pairwise A/B comparison request (EI-T4-01)."""

    question: str
    answer_a: str
    answer_b: str
    reference: str | None = None  # Optional Golden Dataset answer
    judge_model: str | None = None


class CompareItemModel(BaseModel):
    """A single question + two answers for batch comparison."""

    question: str
    answer_a: str
    answer_b: str
    reference: str | None = None


class BatchPairwiseRequest(BaseModel):
    """Batch pairwise A/B comparison request (EI-T4-02)."""

    items: list[CompareItemModel]
    judge_model: str | None = None


# ============================================================
# Endpoints — Response evaluation (re-runs RAG)
# ============================================================
@router.post("/single")
async def eval_single(req: EvalSingleRequest):
    """Evaluate a single query — returns 5-dimensional scores."""
    logger.info("Evaluating single query: {}", req.question[:80])
    result = await evaluate_response(query=req.question)
    return {
        "query": result.query,
        "answer": result.answer,
        "scores": {
            "faithfulness": result.faithfulness,
            "relevancy": result.relevancy,
            "correctness": result.correctness,
            "context_relevancy": result.context_relevancy,
            "answer_relevancy": result.answer_relevancy,
        },
        "feedback": result.feedback,
    }


@router.post("/batch")
async def eval_batch(req: EvalBatchRequest):
    """Batch-evaluate multiple queries — returns 5-dimensional scores per query."""
    logger.info("Batch-evaluating {} queries", len(req.questions))
    results = await evaluate_dataset(
        queries=req.questions,
        reference_answers=req.reference_answers,
    )
    return {
        "results": [
            {
                "query": r.query,
                "scores": {
                    "faithfulness": r.faithfulness,
                    "relevancy": r.relevancy,
                    "correctness": r.correctness,
                    "context_relevancy": r.context_relevancy,
                    "answer_relevancy": r.answer_relevancy,
                },
                "feedback": r.feedback,
            }
            for r in results
        ],
        "count": len(results),
    }


# ============================================================
# Endpoints — Question quality + dedup
# ============================================================
@router.post("/quality")
async def assess_quality(req: QualityRequest):
    """Assess question cognitive depth — surface / understanding / synthesis."""
    logger.info("Assessing question depth: {}", req.question[:80])
    result = await assess_question_depth(question=req.question)
    return {
        "question": result.question,
        "depth": result.depth,
        "score": result.score,
        "reasoning": result.reasoning,
    }


@router.post("/dedup")
async def check_dedup(req: DedupRequest):
    """Check if a question duplicates any in the history set."""
    logger.info(
        "Dedup check — question={}, history_count={}",
        req.question[:80],
        len(req.history_questions),
    )
    result = await question_dedup(
        question=req.question,
        history_questions=req.history_questions,
        threshold=req.threshold,
    )
    return {
        "is_duplicate": result.is_duplicate,
        "most_similar": result.most_similar,
        "similarity_score": result.similarity_score,
        "suggestion": result.suggestion,
    }


# ============================================================
# Endpoints — History-based evaluation (no RAG re-run)
# ============================================================
@router.post("/evaluate-history")
async def eval_from_history(req: HistoryEvalRequest):
    """Evaluate an existing query from Payload Queries (no RAG re-run)."""
    logger.info("Evaluating from history — query_id={}", req.query_id)
    try:
        result = await evaluate_single_from_query(
            query_id=req.query_id,
            model=req.model,
        )
    except RuntimeError as exc:
        logger.error("evaluate-history failed for query_id={}: {}", req.query_id, exc)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=502,
            content={"detail": str(exc)},
        )
    return {
        "query_id": result.query_id,
        "question": result.question,
        "answer": result.answer,
        "scores": {
            "question": {
                "depth": result.question_depth,
                "depth_score": result.question_depth_score,
                "depth_normalized": (result.question_depth_score / 5.0) if result.question_depth_score else None,
            },
            "answer": {
                "faithfulness": result.faithfulness,
                "answer_relevancy": result.answer_relevancy,
            },
            "citation": {
                "context_relevancy": result.context_relevancy,
                "relevancy": result.relevancy,
            },
        },
        "feedback": result.feedback,
    }


@router.post("/evaluate-batch")
async def eval_batch_history(req: BatchHistoryEvalRequest):
    """Batch-evaluate recent queries from Payload (no RAG re-run)."""
    logger.info(
        "Batch evaluating from history — n_recent={}, batch_id={}",
        req.n_recent,
        req.batch_id,
    )
    results = await evaluate_batch_from_queries(
        n_recent=req.n_recent,
        batch_id=req.batch_id,
    )
    return {
        "results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "scores": {
                    "question": {
                        "depth": r.question_depth,
                        "depth_score": r.question_depth_score,
                        "depth_normalized": (r.question_depth_score / 5.0) if r.question_depth_score else None,
                    },
                    "answer": {
                        "faithfulness": r.faithfulness,
                        "answer_relevancy": r.answer_relevancy,
                    },
                    "citation": {
                        "context_relevancy": r.context_relevancy,
                        "relevancy": r.relevancy,
                    },
                },
            }
            for r in results
        ],
        "count": len(results),
        "batch_id": req.batch_id,
    }


# ============================================================
# Endpoints — Four-category evaluation (EV2-T2/T3)
# ============================================================
@router.post("/full-evaluate")
async def eval_full(req: FullEvalRequest):
    """Four-category evaluation of an existing query (RAG/LLM/Answer/Question).

    Returns grouped scores, aggregates, retrieval strategy stats, and status.
    Supports cross-model evaluation via optional judge_model (EI-T3-03).
    """
    logger.info(
        "Full-evaluate — query_id={}, model={}, judge={}",
        req.query_id, req.model, req.judge_model,
    )
    try:
        result = await full_evaluate(
            query_id=req.query_id,
            model=req.model,
            judge_model=req.judge_model,
        )
    except RuntimeError as exc:
        logger.error("full-evaluate failed for query_id={}: {}", req.query_id, exc)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    return {
        "query_id": result.query_id,
        "question": result.question,
        "judge_model": result.judge_model,
        "scores": {
            "rag": {
                "context_relevancy": result.context_relevancy,
                "relevancy": result.relevancy,
                "aggregate": result.rag_score,
            },
            "llm": {
                "faithfulness": result.faithfulness,
                "aggregate": result.llm_score,
            },
            "answer": {
                "answer_relevancy": result.answer_relevancy,
                "completeness": result.completeness,
                "clarity": result.clarity,
                "guidelines_pass": result.guidelines_pass,
                "guidelines_feedback": result.guidelines_feedback,
                "aggregate": result.answer_score,
            },
            "question": {
                "depth": result.question_depth,
                "depth_score": result.question_depth_score,
            },
            "ir": {
                "hit_rate": result.hit_rate,
                "mrr": result.mrr,
                "precision_at_k": result.precision_at_k,
                "recall_at_k": result.recall_at_k,
                "ndcg": result.ndcg,
                "aggregate": result.ir_score,
                "golden_match_id": result.golden_match_id,
            } if result.golden_match_id is not None else None,
        },
        "overall_score": result.overall_score,
        "status": result.status,
        "retrieval": {
            "mode": result.retrieval_mode,
            "bm25_hits": result.bm25_hit_count,
            "vector_hits": result.vector_hit_count,
            "both_hits": result.both_hit_count,
        },
        "feedback": result.feedback,
    }


@router.post("/auto-evaluate")
async def eval_auto(req: AutoEvalRequest):
    """Auto-evaluation trigger — called by Payload afterChange hook.

    Runs in the background via asyncio.create_task().
    Returns immediately with {"triggered": true}.
    """
    import asyncio

    logger.info("Auto-evaluate trigger — query_id={}", req.query_id)
    asyncio.create_task(auto_evaluate_query(req.query_id))
    return {"triggered": True, "query_id": req.query_id}


@router.get("/queries")
async def list_queries(limit: int = 50):
    """List recent Queries for the evaluation page."""
    logger.info("Listing recent {} queries for evaluation", limit)
    records = await _fetch_recent_queries(limit=limit)
    return {
        "queries": [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "model": r.model,
                "createdAt": r.created_at,
                "sourceCount": len(r.sources),
                "sources": [
                    {
                        "book_title": s.get("book_title", ""),
                        "chapter_title": s.get("chapter_title", ""),
                        "page": s.get("page"),
                        "snippet": (s.get("snippet") or "")[:200],
                    }
                    for s in r.sources
                ],
            }
            for r in records
        ],
        "count": len(records),
    }


@router.get("/providers")
async def list_llm_providers():
    """List available LLM providers for evaluation model selection."""
    from engine_v2.llms.resolver import list_providers

    return {"providers": list_providers()}


# ============================================================
# Endpoint — Golden Dataset generation (EI-T1-03)
# ============================================================
@router.post("/generate-golden-dataset")
async def generate_golden_dataset_endpoint(
    req: GenerateGoldenDatasetRequest,
):
    """Generate Golden Dataset QA pairs from a book's ChromaDB chunks.

    Spawns RagDatasetGenerator, maps output to GoldenRecord objects,
    and persists each record to Payload GoldenDataset collection.

    Ref: EI-T1-03 — Golden Dataset 生成 API
    """
    from engine_v2.evaluation.golden_dataset import (
        generate_golden_dataset,
        persist_golden_records,
    )
    from engine_v2.evaluation.history import _get_payload_token

    logger.info(
        "generate-golden-dataset — book_id={}, n_questions={}, per_chunk={}",
        req.book_id, req.n_questions, req.num_questions_per_chunk,
    )

    result = await generate_golden_dataset(
        book_id=req.book_id,
        n_questions=req.n_questions,
        num_questions_per_chunk=req.num_questions_per_chunk,
    )

    if result.errors and not result.records:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=422,
            content={"detail": result.errors[0]},
        )

    # Persist to Payload
    token = await _get_payload_token()
    created_ids = await persist_golden_records(result.records, token=token)

    return {
        "book_id": req.book_id,
        "total_generated": result.total_generated,
        "total_persisted": len(created_ids),
        "created_ids": created_ids,
        "errors": result.errors,
    }


# ============================================================
# Endpoint — Pairwise A/B comparison (EI-T4-01)
# ============================================================
@router.post("/compare")
async def compare_pipelines(req: PairwiseRequest):
    """Compare two answers via pairwise evaluation.

    Uses PairwiseComparisonEvaluator with enforce_consensus=True
    (flips answer order and runs twice to eliminate position bias).

    Returns winner ("A" / "B" / "tie") + reasoning.
    """
    from engine_v2.evaluation.pairwise import compare_answers

    logger.info(
        "Pairwise compare — question={}, judge={}",
        req.question[:60], req.judge_model,
    )

    result = await compare_answers(
        question=req.question,
        answer_a=req.answer_a,
        answer_b=req.answer_b,
        reference=req.reference,
        judge_model=req.judge_model,
    )

    return {
        "question": result.question,
        "winner": result.winner,
        "score": result.score,
        "reasoning": result.reasoning,
        "invalid": result.invalid,
    }


# ============================================================
# Endpoint — Batch A/B comparison (EI-T4-02)
# ============================================================
@router.post("/compare-batch")
async def compare_batch_endpoint(req: BatchPairwiseRequest):
    """Batch A/B comparison of multiple question/answer pairs.

    Runs PairwiseComparisonEvaluator on each item sequentially.
    Returns per-item results + summary (A wins / B wins / ties).
    """
    from engine_v2.evaluation.pairwise import CompareItem, compare_batch

    logger.info(
        "Batch compare — {} items, judge={}",
        len(req.items), req.judge_model,
    )

    items = [
        CompareItem(
            question=it.question,
            answer_a=it.answer_a,
            answer_b=it.answer_b,
            reference=it.reference,
        )
        for it in req.items
    ]

    result = await compare_batch(items=items, judge_model=req.judge_model)

    return {
        "summary": {
            "a_wins": result.a_wins,
            "b_wins": result.b_wins,
            "ties": result.ties,
            "total": result.total,
            "invalid_count": result.invalid_count,
        },
        "results": [
            {
                "question": r.question,
                "winner": r.winner,
                "score": r.score,
                "reasoning": r.reasoning,
                "invalid": r.invalid,
            }
            for r in result.results
        ],
    }


# ============================================================
# Endpoint — Retrieval Recall evaluation (QD-10)
# ============================================================
class RetrievalEvalRequest(BaseModel):
    """Retrieval recall evaluation on a QuestionSet (QD-10)."""

    dataset_id: int
    top_k: int = 5
    reranker: bool = False


@router.post("/retrieval-eval")
async def retrieval_eval_endpoint(req: RetrievalEvalRequest):
    """Evaluate retrieval recall on a QuestionSet.

    For each question with sourceChunkId, runs the retriever and checks
    if the source chunk appears in the top_k results.

    Returns hit_rate, mrr, and per-question hit/miss details.
    """
    from engine_v2.evaluation.retrieval_evaluator import (
        evaluate_retrieval_recall,
    )

    logger.info(
        "Retrieval eval — dataset_id={}, top_k={}, reranker={}",
        req.dataset_id, req.top_k, req.reranker,
    )

    result = await evaluate_retrieval_recall(
        dataset_id=req.dataset_id,
        top_k=req.top_k,
        reranker=req.reranker,
    )

    return result.to_dict()
