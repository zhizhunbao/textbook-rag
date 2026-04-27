"""history — Evaluate real production data from Payload Queries.

Responsibilities:
    - Fetch existing (query, answer, sources) from Payload Queries collection
    - Evaluate already-generated answers using BatchEvalRunner.aevaluate_response_strs()
    - Persist evaluation results to Payload Evaluations collection
    - Support single-query and batch evaluation modes
    - Four-category full evaluation (RAG/LLM/Answer/Question) — EV2-T2-03

Ref: llama_index.core.evaluation — BatchEvalRunner.aevaluate_response_strs()
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from llama_index.core.evaluation import (
    AnswerRelevancyEvaluator,
    ContextRelevancyEvaluator,
    FaithfulnessEvaluator,
    RelevancyEvaluator,
)

from engine_v2.settings import PAYLOAD_URL

if TYPE_CHECKING:
    from engine_v2.evaluation.evaluator import FullEvalResult


# ============================================================
# Constants
# ============================================================
PAYLOAD_TIMEOUT = 30.0

# Cached JWT token for Payload admin access
_payload_token: str | None = None


async def _get_payload_token() -> str:
    """Authenticate with Payload CMS and cache the JWT token.

    Uses PAYLOAD_ADMIN_EMAIL / PAYLOAD_ADMIN_PASSWORD from settings.
    Token is cached module-level to avoid re-login on every request.
    """
    global _payload_token
    if _payload_token:
        return _payload_token

    from engine_v2.settings import PAYLOAD_ADMIN_EMAIL, PAYLOAD_ADMIN_PASSWORD

    if not PAYLOAD_ADMIN_EMAIL or not PAYLOAD_ADMIN_PASSWORD:
        raise RuntimeError(
            "PAYLOAD_ADMIN_EMAIL and PAYLOAD_ADMIN_PASSWORD must be set in .env "
            "for the engine to authenticate with Payload CMS."
        )

    url = f"{PAYLOAD_URL}/api/users/login"
    async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
        resp = await client.post(url, json={
            "email": PAYLOAD_ADMIN_EMAIL,
            "password": PAYLOAD_ADMIN_PASSWORD,
        })
        resp.raise_for_status()
        data = resp.json()

    _payload_token = data.get("token")
    if not _payload_token:
        raise RuntimeError("Payload login succeeded but no token returned")

    logger.info("Authenticated with Payload CMS as {}", PAYLOAD_ADMIN_EMAIL)
    return _payload_token


def _invalidate_token() -> None:
    """Clear the cached JWT token so the next request triggers re-login."""
    global _payload_token
    _payload_token = None


# ============================================================
# Data classes
# ============================================================
@dataclass
class QueryRecord:
    """A single record fetched from Payload Queries collection."""

    id: int
    question: str
    answer: str
    sources: list[dict] = field(default_factory=list)
    model: str | None = None
    created_at: str = ""


@dataclass
class HistoryEvalResult:
    """Evaluation result for a single historical query.

    Three evaluation groups:
        - Question:  cognitive depth (1-5 scale, mapped to 0-1 for consistency)
        - Answer:    faithfulness + answer_relevancy
        - Citation:  context_relevancy + relevancy (source-answer alignment)
    """

    query_id: int
    question: str
    answer: str
    # Question quality
    question_depth: str | None = None  # surface / understanding / synthesis
    question_depth_score: float | None = None  # 1.0-5.0 raw, normalised to 0-1
    question_depth_reasoning: str = ""
    # Answer quality
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    # Citation quality
    context_relevancy: float | None = None
    relevancy: float | None = None
    feedback: dict[str, str] = field(default_factory=dict)


# ============================================================
# Payload API helpers
# ============================================================
async def _fetch_query_by_id(query_id: int) -> QueryRecord:
    """Fetch a single Queries record from Payload CMS by ID."""
    url = f"{PAYLOAD_URL}/api/queries/{query_id}"
    token = await _get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    try:
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            # Token expired → invalidate, re-login, retry once
            if resp.status_code == 403:
                logger.warning("JWT expired for query_id={}, re-authenticating…", query_id)
                _invalidate_token()
                token = await _get_payload_token()
                headers = {"Authorization": f"JWT {token}"}
                resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            raw = resp.json()
    except httpx.ConnectError:
        logger.error("Cannot connect to Payload CMS at {} — is it running?", PAYLOAD_URL)
        raise RuntimeError(
            f"Cannot connect to Payload CMS at {PAYLOAD_URL}. "
            "Ensure the Payload server is running and PAYLOAD_URL is correct."
        )
    except httpx.HTTPStatusError as exc:
        logger.error("Payload returned {} for query_id={}", exc.response.status_code, query_id)
        raise RuntimeError(
            f"Payload returned HTTP {exc.response.status_code} for query_id={query_id}"
        )

    return _map_query_record(raw)


async def _fetch_recent_queries(limit: int = 20) -> list[QueryRecord]:
    """Fetch the most recent N Queries records from Payload CMS."""
    params = {
        "limit": str(limit),
        "sort": "-createdAt",
    }
    url = f"{PAYLOAD_URL}/api/queries"
    token = await _get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code == 403:
            _invalidate_token()
            token = await _get_payload_token()
            headers = {"Authorization": f"JWT {token}"}
            resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("docs", [])
    return [_map_query_record(d) for d in docs]


def _map_query_record(raw: dict) -> QueryRecord:
    """Map raw Payload JSON to a QueryRecord dataclass."""
    return QueryRecord(
        id=raw.get("id", 0),
        question=raw.get("question", ""),
        answer=raw.get("answer", ""),
        sources=raw.get("sources") or [],
        model=raw.get("model"),
        created_at=raw.get("createdAt", ""),
    )


def _extract_contexts(sources: list[dict]) -> list[str]:
    """Extract context strings from sources array.

    Each source may have 'full_content' (preferred) or 'snippet' as fallback.
    """
    contexts: list[str] = []
    for src in sources:
        text = src.get("full_content") or src.get("snippet") or ""
        if text:
            contexts.append(text)
    return contexts


async def _persist_evaluation(
    result: HistoryEvalResult,
    batch_id: str | None = None,
) -> int | None:
    """Write an evaluation result to Payload Evaluations collection.

    Returns the created evaluation record ID, or None on failure.
    """
    # Normalise question depth score (1-5) → 0-1 for consistency
    norm_depth = (result.question_depth_score / 5.0) if result.question_depth_score else None

    payload_data = {
        "query": result.question,
        "answer": result.answer,
        "faithfulness": result.faithfulness,
        "relevancy": result.relevancy,
        "contextRelevancy": result.context_relevancy,
        "answerRelevancy": result.answer_relevancy,
        "questionDepth": result.question_depth,
        "questionDepthScore": norm_depth,
        "feedback": result.feedback,
        "queryRef": result.query_id,
    }
    if batch_id:
        payload_data["batchId"] = batch_id

    url = f"{PAYLOAD_URL}/api/evaluations"
    try:
        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.post(url, json=payload_data, headers=headers)
            if resp.status_code == 403:
                _invalidate_token()
                token = await _get_payload_token()
                headers = {"Authorization": f"JWT {token}"}
                resp = await client.post(url, json=payload_data, headers=headers)
            resp.raise_for_status()
            created = resp.json()
            return created.get("doc", {}).get("id")
    except Exception:
        logger.warning(
            "Failed to persist evaluation for query_id={}",
            result.query_id,
        )
        return None


# ============================================================
# Core evaluation functions
# ============================================================
async def evaluate_single_from_query(
    query_id: int,
    model: str | None = None,
) -> HistoryEvalResult:
    """Evaluate a single existing query from Payload Queries.

    Fetches the stored (question, answer, sources), then runs
    three evaluation groups:
        1. Question quality  — cognitive depth (1-5)
        2. Answer quality    — faithfulness + answer_relevancy
        3. Citation quality  — context_relevancy + relevancy

    Does NOT re-run the RAG pipeline.

    Args:
        query_id: Payload Queries record ID.
        model: Optional LLM model override (e.g. 'gpt-4o-mini', 'llama3.2:3b').
               Uses global Settings.llm if None.

    Returns:
        HistoryEvalResult with grouped scores + feedback.
    """
    from engine_v2.evaluation.evaluator import assess_question_depth
    from engine_v2.llms.resolver import resolve_llm

    # Resolve LLM for evaluators
    llm_instance = resolve_llm(model=model) if model else None
    eval_kwargs = {"llm": llm_instance} if llm_instance else {}

    record = await _fetch_query_by_id(query_id)
    contexts = _extract_contexts(record.sources)

    logger.info(
        "Evaluating query_id={} — question={}, contexts={}, model={}",
        query_id,
        record.question[:60],
        len(contexts),
        model or 'default',
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
    faithfulness_eval = FaithfulnessEvaluator(**eval_kwargs)
    ans_relevancy_eval = AnswerRelevancyEvaluator(**eval_kwargs)

    faith_r = await faithfulness_eval.aevaluate(
        query=record.question,
        response=record.answer,
        contexts=contexts,
    )
    ans_r = await ans_relevancy_eval.aevaluate(
        query=record.question,
        response=record.answer,
    )

    # ── 3. Citation quality ─────────────────────────────────
    relevancy_eval = RelevancyEvaluator(**eval_kwargs)
    ctx_relevancy_eval = ContextRelevancyEvaluator(**eval_kwargs)

    relev_r = await relevancy_eval.aevaluate(
        query=record.question,
        response=record.answer,
        contexts=contexts,
    )
    ctx_r = await ctx_relevancy_eval.aevaluate(
        query=record.question,
        contexts=contexts,
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
            "faithfulness": faith_r.feedback or "",
            "answer_relevancy": ans_r.feedback or "",
            "context_relevancy": ctx_r.feedback or "",
            "relevancy": relev_r.feedback or "",
            "question_depth": q_depth_reasoning,
        },
    )

    # Persist to Evaluations collection
    eval_id = await _persist_evaluation(result)
    logger.info(
        "Evaluated query_id={} — depth={}, faith={}, ans_rel={}, ctx={}, relev={} → eval_id={}",
        query_id,
        result.question_depth,
        result.faithfulness,
        result.answer_relevancy,
        result.context_relevancy,
        result.relevancy,
        eval_id,
    )
    return result


async def evaluate_batch_from_queries(
    n_recent: int = 20,
    batch_id: str | None = None,
) -> list[HistoryEvalResult]:
    """Batch-evaluate the most recent N Queries from Payload.

    Fetches real production data, evaluates each answer using
    individual evaluator calls, and persists results with a shared batchId.

    Args:
        n_recent: Number of recent queries to evaluate.
        batch_id: Optional batch group ID. Auto-generated if not provided.

    Returns:
        List of HistoryEvalResult, one per query.
    """
    if not batch_id:
        batch_id = f"batch-{uuid.uuid4().hex[:8]}"

    records = await _fetch_recent_queries(limit=n_recent)
    if not records:
        logger.warning("No queries found for batch evaluation")
        return []

    logger.info(
        "Batch evaluating {} queries — batch_id={}",
        len(records),
        batch_id,
    )

    results: list[HistoryEvalResult] = []
    for i, record in enumerate(records):
        contexts = _extract_contexts(record.sources)

        try:
            # 1. Question quality
            from engine_v2.evaluation.evaluator import assess_question_depth

            try:
                depth_r = await assess_question_depth(record.question)
                q_depth = depth_r.depth
                q_depth_score = depth_r.score
                q_depth_reasoning = depth_r.reasoning
            except Exception:
                q_depth = None
                q_depth_score = None
                q_depth_reasoning = ""

            # 2. Answer quality
            faithfulness_eval = FaithfulnessEvaluator()
            ans_relevancy_eval = AnswerRelevancyEvaluator()

            faith_r = await faithfulness_eval.aevaluate(
                query=record.question,
                response=record.answer,
                contexts=contexts,
            )
            ans_r = await ans_relevancy_eval.aevaluate(
                query=record.question,
                response=record.answer,
            )

            # 3. Citation quality
            relevancy_eval = RelevancyEvaluator()
            ctx_relevancy_eval = ContextRelevancyEvaluator()

            relev_r = await relevancy_eval.aevaluate(
                query=record.question,
                response=record.answer,
                contexts=contexts,
            )
            ctx_r = await ctx_relevancy_eval.aevaluate(
                query=record.question,
                contexts=contexts,
            )

            eval_result = HistoryEvalResult(
                query_id=record.id,
                question=record.question,
                answer=record.answer,
                question_depth=q_depth,
                question_depth_score=q_depth_score,
                question_depth_reasoning=q_depth_reasoning,
                faithfulness=faith_r.score,
                answer_relevancy=ans_r.score,
                context_relevancy=ctx_r.score,
                relevancy=relev_r.score,
                feedback={
                    "faithfulness": faith_r.feedback or "",
                    "answer_relevancy": ans_r.feedback or "",
                    "context_relevancy": ctx_r.feedback or "",
                    "relevancy": relev_r.feedback or "",
                    "question_depth": q_depth_reasoning,
                },
            )
        except Exception as exc:
            logger.error(
                "Failed to evaluate query_id={}: {}",
                record.id,
                exc,
            )
            eval_result = HistoryEvalResult(
                query_id=record.id,
                question=record.question,
                answer=record.answer,
            )

        await _persist_evaluation(eval_result, batch_id=batch_id)
        results.append(eval_result)
        logger.debug(
            "Batch progress: {}/{} — query_id={}",
            i + 1,
            len(records),
            record.id,
        )

    logger.info(
        "Batch evaluation complete — {} results, batch_id={}",
        len(results),
        batch_id,
    )
    return results


# ============================================================
# Four-category full evaluation (EV2-T2-03)
# ============================================================
async def full_evaluate(
    query_id: int,
    model: str | None = None,
) -> "FullEvalResult":
    """Run four-category evaluation on a stored query record.

    Groups:
        🔍 RAG    — context_relevancy + relevancy
        🤖 LLM    — faithfulness
        📝 Answer — answer_relevancy + completeness + clarity
        ❓ Question — cognitive depth

    Also extracts retrieval strategy stats from stored sources
    (bm25_hit_count / vector_hit_count / both_hit_count).

    Args:
        query_id: Payload Queries record ID.
        model: Optional LLM model override.

    Returns:
        FullEvalResult with per-dimension scores, aggregates, and feedback.
    """
    from llama_index.core.evaluation import CorrectnessEvaluator, GuidelineEvaluator
    from engine_v2.evaluation.evaluator import (
        FullEvalResult,
        assess_question_depth,
        compute_aggregate_scores,
    )
    from engine_v2.llms.resolver import resolve_llm
    from engine_v2.evaluation.golden_dataset import match_golden_record
    from engine_v2.evaluation.retrieval_metrics import compute_retrieval_metrics
    from engine_v2.settings import QUALITY_GUIDELINES

    # Resolve LLM
    llm_instance = resolve_llm(model=model) if model else None
    eval_kwargs = {"llm": llm_instance} if llm_instance else {}

    record = await _fetch_query_by_id(query_id)
    contexts = _extract_contexts(record.sources)

    logger.info(
        "Full-evaluate query_id={} — question={}, contexts={}, model={}",
        query_id, record.question[:60], len(contexts), model or 'default',
    )

    feedback: dict[str, str] = {}

    # ── ❓ Question quality ─────────────────────────────
    try:
        depth_r = await assess_question_depth(record.question, llm=llm_instance)
        q_depth = depth_r.depth
        q_depth_score = depth_r.score
        q_depth_reasoning = depth_r.reasoning
        feedback["question_depth"] = q_depth_reasoning
    except Exception as exc:
        logger.warning("Question depth assessment failed: {}", exc)
        q_depth = None
        q_depth_score = None
        q_depth_reasoning = ""

    # ── 🤖 LLM quality (faithfulness) ────────────────
    faithfulness_eval = FaithfulnessEvaluator(**eval_kwargs)
    faith_r = await faithfulness_eval.aevaluate(
        query=record.question, response=record.answer, contexts=contexts,
    )
    feedback["faithfulness"] = faith_r.feedback or ""

    # ── 🔍 RAG quality (context + relevancy) ───────────
    relevancy_eval = RelevancyEvaluator(**eval_kwargs)
    ctx_relevancy_eval = ContextRelevancyEvaluator(**eval_kwargs)

    relev_r = await relevancy_eval.aevaluate(
        query=record.question, response=record.answer, contexts=contexts,
    )
    ctx_r = await ctx_relevancy_eval.aevaluate(
        query=record.question, contexts=contexts,
    )
    feedback["relevancy"] = relev_r.feedback or ""
    feedback["context_relevancy"] = ctx_r.feedback or ""

    # ── 📝 Answer quality (Guidelines + Correctness) ──
    ans_relevancy_eval = AnswerRelevancyEvaluator(**eval_kwargs)

    ans_r = await ans_relevancy_eval.aevaluate(
        query=record.question, response=record.answer,
    )
    feedback["answer_relevancy"] = ans_r.feedback or ""

    # GuidelineEvaluator (replaces Completeness/Clarity) (EI-T3-01)
    guideline_eval = GuidelineEvaluator(
        guidelines=QUALITY_GUIDELINES, **eval_kwargs
    )
    guidelines_pass: bool | None = None
    try:
        # evaluate() returns an EvaluationResult with score 1.0 (pass) or 0.0 (fail)
        guide_r = await guideline_eval.aevaluate(
            query=record.question, response=record.answer, contexts=contexts
        )
        guidelines_pass = (guide_r.score is not None and guide_r.score > 0.5)
        feedback["guidelines"] = guide_r.feedback or ""
    except Exception as exc:
        logger.warning("GuidelineEvaluator failed: {}", exc)
        feedback["guidelines"] = f"evaluator error: {exc}"

    # Golden Dataset Match (EI-T2-02)
    # Check if there is a golden record for this query
    golden_match = await match_golden_record(record.question)
    
    ir_metrics = {}
    correctness_score: float | None = None
    
    if golden_match:
        # Calculate Pure-math IR Metrics (Zero-LLM)
        retrieved_ids = []
        for src in record.sources:
            if src.get("chunk_id"):
                retrieved_ids.append(src["chunk_id"])
        
        ir_result = compute_retrieval_metrics(
            retrieved_ids=retrieved_ids,
            expected_ids=golden_match.expected_chunk_ids,
        )
        ir_metrics = ir_result.to_dict()
        
        # Calculate True Correctness via F1 vs Expected Answer
        correctness_eval = CorrectnessEvaluator(**eval_kwargs)
        try:
            corr_r = await correctness_eval.aevaluate(
                query=record.question,
                response=record.answer,
                reference=golden_match.expected_answer
            )
            feedback["correctness"] = corr_r.feedback or ""
            correctness_score = (corr_r.score / 5.0) if corr_r.score is not None else None
        except Exception as exc:
            logger.warning("CorrectnessEvaluator failed: {}", exc)
            feedback["correctness"] = f"evaluator error: {exc}"
    else:
        feedback["golden_match"] = "No Golden Dataset record found for this query."

    feedback["answer_relevancy"] = ans_r.feedback or ""

    # ── Retrieval strategy stats from stored sources ─────
    bm25_hits = 0
    vector_hits = 0
    both_hits = 0
    has_bm25 = False
    for src in record.sources:
        rs = src.get("retrieval_source", "vector")
        if rs == "both":
            both_hits += 1
            has_bm25 = True
        elif rs == "bm25":
            bm25_hits += 1
            has_bm25 = True
        else:
            vector_hits += 1

    # ── Assemble FullEvalResult ─────────────────────────
    result = FullEvalResult(
        query_id=record.id,
        question=record.question,
        answer=record.answer,
        # RAG
        context_relevancy=ctx_r.score,
        relevancy=relev_r.score,
        # LLM
        faithfulness=faith_r.score,
        # Answer
        answer_relevancy=ans_r.score,
        correctness=correctness_score,
        guidelines_pass=guidelines_pass,
        guidelines_feedback=feedback.get("guidelines", ""),
        # Question
        question_depth=q_depth,
        question_depth_score=q_depth_score,
        question_depth_reasoning=q_depth_reasoning or "",
        # Retrieval
        retrieval_mode="hybrid" if has_bm25 else "vector_only",
        bm25_hit_count=bm25_hits,
        vector_hit_count=vector_hits,
        both_hit_count=both_hits,
        # IR Metrics
        hit_rate=ir_metrics.get("hit_rate"),
        mrr=ir_metrics.get("mrr"),
        precision_at_k=ir_metrics.get("precision_at_k"),
        recall_at_k=ir_metrics.get("recall_at_k"),
        ndcg=ir_metrics.get("ndcg"),
        ir_score=ir_metrics.get("ir_score"),
        golden_match_id=golden_match.id if golden_match else None,
        # Feedback
        feedback=feedback,
    )

    # Compute aggregates + status
    compute_aggregate_scores(result)
    result.status = _compute_status(result)

    # Persist to Payload Evaluations collection
    eval_id = await _persist_full_evaluation(result)

    logger.info(
        "Full-evaluated query_id={} — rag={}, llm={}, answer={}, overall={}, status={} → eval_id={}",
        query_id, result.rag_score, result.llm_score,
        result.answer_score, result.overall_score, result.status, eval_id,
    )
    return result


# ============================================================
# Status computation (EV2-T3-02)
# ============================================================
def _compute_status(result: FullEvalResult) -> str:
    """Determine pass/fail status based on configurable thresholds.

    Rules (UEP-T2-02):
        - Need at least faithfulness + answer_score to judge
        - faithfulness >= threshold AND answer_score >= threshold → "pass"
        - Otherwise → "fail"
        - If both scores are None → "pending"
    """
    from engine_v2.settings import EVAL_PASS_ANSWER_SCORE, EVAL_PASS_FAITHFULNESS

    # Fallback: if answer_score is None but answer_relevancy exists, use that
    effective_answer = result.answer_score
    if effective_answer is None:
        effective_answer = result.answer_relevancy

    if result.faithfulness is None and effective_answer is None:
        return "pending"

    # If we have at least one, we can make a judgement
    faith_ok = result.faithfulness is None or result.faithfulness >= EVAL_PASS_FAITHFULNESS
    answer_ok = effective_answer is None or effective_answer >= EVAL_PASS_ANSWER_SCORE

    if faith_ok and answer_ok:
        return "pass"

    return "fail"


# ============================================================
# Persist FullEvalResult (EV2-T3-01)
# ============================================================
async def _persist_full_evaluation(
    result: FullEvalResult,
    batch_id: str | None = None,
) -> int | None:
    """Write a FullEvalResult to Payload Evaluations collection.

    Maps all four-category fields to the extended Evaluations schema.
    Returns the created evaluation record ID, or None on failure.
    """
    # Normalise question depth score (1-5) → 0-1 for consistency
    norm_depth = (result.question_depth_score / 5.0) if result.question_depth_score else None

    payload_data: dict = {
        # Original fields
        "query": result.question,
        "answer": result.answer,
        "faithfulness": result.faithfulness,
        "relevancy": result.relevancy,
        "contextRelevancy": result.context_relevancy,
        "answerRelevancy": result.answer_relevancy,
        "questionDepth": result.question_depth,
        "questionDepthScore": norm_depth,
        "feedback": result.feedback,
        "queryRef": result.query_id,
        # Four-category aggregates (EV2-T2-04)
        "ragScore": result.rag_score,
        "llmScore": result.llm_score,
        "answerScore": result.answer_score,
        "overallScore": result.overall_score,
        # Answer sub-dimensions
        "guidelinesPass": result.guidelines_pass,
        "guidelinesFeedback": result.guidelines_feedback,
        # Retrieval strategy
        "retrievalMode": result.retrieval_mode,
        "bm25Hits": result.bm25_hit_count,
        "vectorHits": result.vector_hit_count,
        "bothHits": result.both_hit_count,
        # IR Metrics
        "hitRate": result.hit_rate,
        "mrr": result.mrr,
        "precisionAtK": result.precision_at_k,
        "recallAtK": result.recall_at_k,
        "ndcg": result.ndcg,
        "irScore": result.ir_score,
        "goldenMatchRef": result.golden_match_id,
        # Status
        "status": result.status,
    }
    if batch_id:
        payload_data["batchId"] = batch_id

    url = f"{PAYLOAD_URL}/api/evaluations"
    try:
        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.post(url, json=payload_data, headers=headers)
            if resp.status_code == 403:
                _invalidate_token()
                token = await _get_payload_token()
                headers = {"Authorization": f"JWT {token}"}
                resp = await client.post(url, json=payload_data, headers=headers)
            resp.raise_for_status()
            created = resp.json()
            return created.get("doc", {}).get("id")
    except Exception:
        logger.warning(
            "Failed to persist full evaluation for query_id={}",
            result.query_id,
        )
        return None


# ============================================================
# Auto-eval trigger (EV2-T3-01)
# ============================================================
async def auto_evaluate_query(query_id: int) -> None:
    """Fire-and-forget auto-evaluation for a newly created query.

    Called by the Payload afterChange hook on the Queries collection.
    Silently catches all exceptions to avoid disrupting the query flow.

    Args:
        query_id: Payload Queries record ID.
    """
    from engine_v2.settings import AUTO_EVAL_ENABLED

    if not AUTO_EVAL_ENABLED:
        logger.debug("Auto-eval disabled, skipping query_id={}", query_id)
        return

    try:
        logger.info("Auto-eval triggered for query_id={}", query_id)
        result = await full_evaluate(query_id)
        logger.info(
            "Auto-eval complete for query_id={} — overall={}, status={}",
            query_id, result.overall_score, result.status,
        )
    except Exception as exc:
        logger.warning("Auto-eval failed for query_id={}: {}", query_id, exc)

