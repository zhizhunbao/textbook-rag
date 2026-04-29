"""evaluator — Unified RAG evaluation hub.

Responsibilities:
    - 5-dimensional response evaluation (faithfulness, relevancy, correctness,
      context_relevancy, answer_relevancy)
    - Four-category FullEvalResult (RAG / LLM / Answer / Question) — EV2-T2-02
    - Question cognitive depth assessment (surface / understanding / synthesis)
    - Question deduplication via semantic similarity
    - Factory function to build evaluator sets by mode

Ref: llama_index.core.evaluation — CorrectnessEvaluator, SemanticSimilarityEvaluator,
     ContextRelevancyEvaluator, AnswerRelevancyEvaluator, BatchEvalRunner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from loguru import logger

from llama_index.core.evaluation import (
    AnswerRelevancyEvaluator,
    BatchEvalRunner,
    ContextRelevancyEvaluator,
    CorrectnessEvaluator,
    FaithfulnessEvaluator,
    RelevancyEvaluator,
    SemanticSimilarityEvaluator,
)

if TYPE_CHECKING:
    from llama_index.core.query_engine import RetrieverQueryEngine

from engine_v2.evaluation.prompts import DEPTH_EVAL_TEMPLATE
from engine_v2.query_engine.citation import get_query_engine


# ============================================================
# Constants
# ============================================================
# Depth label thresholds: score ≥ threshold → label
DEPTH_THRESHOLDS = {
    "synthesis": 4.0,
    "understanding": 2.5,
    # < 2.5 → "surface"
}

# Deduplication similarity threshold
DEDUP_SIMILARITY_THRESHOLD = 0.85


# ============================================================
# Data classes
# ============================================================
@dataclass
class EvalResult:
    """Structured evaluation result for one query (5-dimensional)."""

    query: str
    answer: str
    faithfulness: float | None = None
    relevancy: float | None = None
    correctness: float | None = None
    context_relevancy: float | None = None
    answer_relevancy: float | None = None
    feedback: dict[str, str] = field(default_factory=dict)


@dataclass
class DepthResult:
    """Question cognitive depth assessment result."""

    question: str
    depth: str  # "surface" | "understanding" | "synthesis"
    score: float  # 1.0–5.0
    reasoning: str


@dataclass
class DedupResult:
    """Question deduplication result."""

    is_duplicate: bool
    most_similar: str | None  # Most similar existing question text
    similarity_score: float
    suggestion: str  # Suggested direction if duplicate


# ============================================================
# FullEvalResult — four-category scoring (EV2-T2-02)
# ============================================================
@dataclass
class FullEvalResult:
    """Four-category evaluation result for a single query.

    Groups:
        🔍 RAG Score   — context_relevancy, relevancy
        🤖 LLM Score   — faithfulness
        📝 Answer Score — correctness, answer_relevancy, completeness, clarity
        ❓ Question     — depth, depth_score

    Aggregates:
        rag_score     — mean of RAG dimensions
        llm_score     — faithfulness (only dimension)
        answer_score  — mean of Answer dimensions
        overall_score — weighted average of rag + llm + answer

    Retrieval strategy (from TrackedQueryFusionRetriever):
        retrieval_mode  — "hybrid" | "vector_only"
        bm25_hit_count  — sources from BM25
        vector_hit_count — sources from Vector
        both_hit_count  — sources matched by both
    """

    query_id: int
    question: str
    answer: str

    # ── 🔍 RAG Score ──
    context_relevancy: float | None = None
    relevancy: float | None = None
    rag_score: float | None = None

    # ── 🤖 LLM Score ──
    faithfulness: float | None = None
    llm_score: float | None = None

    # ── 📝 Answer Score ──
    correctness: float | None = None
    answer_relevancy: float | None = None
    completeness: float | None = None  # Deprecated in favor of guidelines
    clarity: float | None = None       # Deprecated in favor of guidelines
    guidelines_pass: bool | None = None
    guidelines_feedback: str | None = None
    answer_score: float | None = None

    # ── ❓ Question Score ──
    question_depth: str | None = None  # surface / understanding / synthesis
    question_depth_score: float | None = None  # 1.0–5.0 raw
    question_depth_reasoning: str = ""

    # ── Overall ──
    overall_score: float | None = None
    status: str = "pending"  # "pass" | "fail" | "pending"
    judge_model: str | None = None  # Cross-model: LLM used as judge (EI-T3-03)

    # ── Retrieval strategy (EV2-T1) ──
    retrieval_mode: str = "vector_only"  # "hybrid" | "vector_only"
    bm25_hit_count: int = 0
    vector_hit_count: int = 0
    both_hit_count: int = 0

    # ── 📊 IR Retrieval Metrics (EI-T2, pure math, needs Golden Dataset) ──
    hit_rate: float | None = None
    mrr: float | None = None
    precision_at_k: float | None = None
    recall_at_k: float | None = None
    ndcg: float | None = None
    ir_score: float | None = None  # Mean of 5 IR metrics
    golden_match_id: int | None = None  # Matched GoldenDataset record ID
    average_precision: float | None = None  # AP metric (EUX-T4)

    # ── 📋 Evaluation metadata (EUX-T2) ──
    answer_model: str | None = None  # LLM that generated the answer
    llm_calls: int = 0  # Total LLM API calls during evaluation

    # ── 💡 Improvement suggestions (EUX-T3) ──
    suggestions: list[dict] = field(default_factory=list)

    # ── 🧭 Routing evaluation (EV2-T4-02) ──
    routing_decision: str | None = None   # "standard" | "smart" | "deep" | None
    routing_correct: bool | None = None   # post-hoc assessment of routing quality
    routing_reasoning: str = ""           # why was this routing deemed correct/incorrect

    # ── Feedback ──
    feedback: dict[str, str] = field(default_factory=dict)


def compute_aggregate_scores(
    result: FullEvalResult,
    weights: dict[str, float] | None = None,
) -> FullEvalResult:
    """Compute aggregate scores (rag, llm, answer, overall) in place.

    Args:
        result: FullEvalResult with individual dimension scores filled.
        weights: Optional {"rag": w, "llm": w, "answer": w} for overall.
            Defaults to {"rag": 0.3, "llm": 0.3, "answer": 0.4}.

    Returns:
        The same result object with aggregate fields populated.
    """
    if weights is None:
        weights = {"rag": 0.3, "llm": 0.3, "answer": 0.4}

    # RAG score = mean(context_relevancy, relevancy)
    rag_dims = [v for v in (result.context_relevancy, result.relevancy) if v is not None]
    result.rag_score = (sum(rag_dims) / len(rag_dims)) if rag_dims else None

    # LLM score = faithfulness
    result.llm_score = result.faithfulness

    # Answer score = mean(correctness, answer_relevancy, completeness, clarity)
    # Plus guidelines_pass (True=1.0, False=0.0) if present
    ans_dims = [
        v for v in (
            result.correctness, result.answer_relevancy,
            result.completeness, result.clarity,
        ) if v is not None
    ]
    if result.guidelines_pass is not None:
        ans_dims.append(1.0 if result.guidelines_pass else 0.0)

    result.answer_score = (sum(ans_dims) / len(ans_dims)) if ans_dims else None

    # Overall = weighted average of group scores (including IR when available)
    group_scores = []
    group_weights = []
    for key, score in [("rag", result.rag_score), ("llm", result.llm_score),
                       ("answer", result.answer_score)]:
        if score is not None:
            group_scores.append(score)
            group_weights.append(weights.get(key, 1.0))

    # IR score participates in overall when Golden Dataset provides it (EI-T2)
    if result.ir_score is not None:
        group_scores.append(result.ir_score)
        group_weights.append(weights.get("ir", 0.2))

    if group_scores:
        total_w = sum(group_weights)
        result.overall_score = round(
            sum(s * w for s, w in zip(group_scores, group_weights)) / total_w, 4
        )

    return result


# ============================================================
# QuestionDepthEvaluator — inherits CorrectnessEvaluator
# ============================================================
# Ref: llama_index.core.evaluation.correctness — CorrectnessEvaluator
class QuestionDepthEvaluator(CorrectnessEvaluator):
    """Evaluate question cognitive depth (1–5 scale).

    Inherits CorrectnessEvaluator with a custom eval_template
    that scores question depth instead of answer correctness.

    Business-layer threshold mapping:
        ≥ 4.0 → synthesis
        ≥ 2.5 → understanding
        < 2.5 → surface
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            eval_template=DEPTH_EVAL_TEMPLATE,
            score_threshold=2.5,  # passing = understanding or above
            **kwargs,
        )
        logger.debug("QuestionDepthEvaluator initialized")


# ============================================================
# Factory — build evaluator sets by mode
# ============================================================
def build_evaluators(mode: str = "response") -> dict[str, Any]:
    """Build evaluator dict by usage mode.

    Args:
        mode: "response" → 5-dimensional response evaluation;
              "question" → question depth evaluator.

    Returns:
        Dict[str, BaseEvaluator] suitable for BatchEvalRunner.
    """
    if mode == "response":
        return {
            "faithfulness": FaithfulnessEvaluator(),
            "relevancy": RelevancyEvaluator(),
            "correctness": CorrectnessEvaluator(),
            "context_relevancy": ContextRelevancyEvaluator(),
            "answer_relevancy": AnswerRelevancyEvaluator(),
        }
    if mode == "question":
        return {
            "depth": QuestionDepthEvaluator(),
        }
    msg = f"Unknown evaluator mode: {mode!r}. Use 'response' or 'question'."
    raise ValueError(msg)


# ============================================================
# 5-dimensional response evaluation
# ============================================================
async def evaluate_response(
    query: str,
    engine: RetrieverQueryEngine | None = None,
) -> EvalResult:
    """Evaluate a single query through the full RAG pipeline (5-dimensional).

    Runs the query, then evaluates the response with:
        - FaithfulnessEvaluator  (is answer grounded in context?)
        - RelevancyEvaluator     (is context relevant to query?)
        - ContextRelevancyEvaluator  (context quality score)
        - AnswerRelevancyEvaluator   (answer-to-query relevance score)

    Args:
        query: The question to evaluate.
        engine: Optional pre-built query engine.

    Returns:
        EvalResult with 5-dimensional scores and feedback.
    """
    if engine is None:
        engine = get_query_engine()

    response = engine.query(query)

    # Build evaluators
    faithfulness_eval = FaithfulnessEvaluator()
    relevancy_eval = RelevancyEvaluator()
    ctx_relevancy_eval = ContextRelevancyEvaluator()
    ans_relevancy_eval = AnswerRelevancyEvaluator()

    # Extract context strings for context-based evaluators
    contexts = [n.node.get_content() for n in response.source_nodes]

    # Run all evaluations
    faith_result = await faithfulness_eval.aevaluate_response(
        query=query, response=response
    )
    relev_result = await relevancy_eval.aevaluate_response(
        query=query, response=response
    )
    ctx_result = await ctx_relevancy_eval.aevaluate(
        query=query, contexts=contexts
    )
    ans_result = await ans_relevancy_eval.aevaluate(
        query=query, response=str(response)
    )

    result = EvalResult(
        query=query,
        answer=str(response),
        faithfulness=faith_result.score,
        relevancy=relev_result.score,
        context_relevancy=ctx_result.score,
        answer_relevancy=ans_result.score,
        feedback={
            "faithfulness": faith_result.feedback or "",
            "relevancy": relev_result.feedback or "",
            "context_relevancy": ctx_result.feedback or "",
            "answer_relevancy": ans_result.feedback or "",
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


# ============================================================
# Batch evaluation (5-dimensional)
# ============================================================
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
    if engine is None:
        engine = get_query_engine()

    evaluators = build_evaluators(mode="response")
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


# ============================================================
# Question depth assessment
# ============================================================
def _score_to_depth_label(score: float) -> str:
    """Map numeric depth score to categorical label."""
    if score >= DEPTH_THRESHOLDS["synthesis"]:
        return "synthesis"
    if score >= DEPTH_THRESHOLDS["understanding"]:
        return "understanding"
    return "surface"


async def assess_question_depth(
    question: str,
    llm: Any = None,
) -> DepthResult:
    """Assess cognitive depth of a question.

    Uses QuestionDepthEvaluator (inherits CorrectnessEvaluator with
    custom eval_template) to score 1–5, then maps to depth label.

    Args:
        question: The question text.
        llm: Optional LLM instance override. Uses Settings.llm if None.

    Returns:
        DepthResult with depth label, numeric score, and reasoning.
    """
    eval_kwargs = {"llm": llm} if llm else {}
    evaluator = QuestionDepthEvaluator(**eval_kwargs)

    # CorrectnessEvaluator.aevaluate(query, response, reference)
    # We pass the question as both query and response (the thing being judged).
    # Reference provides the rubric context for the LLM.
    result = await evaluator.aevaluate(
        query=question,
        response=question,
        reference=(
            "A high-depth question requires synthesis across multiple concepts, "
            "critical evaluation, or creative application. "
            "A low-depth question merely asks for definitions or factual recall."
        ),
    )

    score = result.score or 1.0
    depth = _score_to_depth_label(score)

    logger.info(
        "Question depth: {} (score={}) — {}",
        depth, score, question[:80],
    )
    return DepthResult(
        question=question,
        depth=depth,
        score=score,
        reasoning=result.feedback or "",
    )


# ============================================================
# Question deduplication — SemanticSimilarityEvaluator
# ============================================================
# Ref: llama_index.core.evaluation.semantic_similarity — SemanticSimilarityEvaluator
async def question_dedup(
    question: str,
    history_questions: list[str],
    threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> DedupResult:
    """Detect if a question duplicates any in the history set.

    Uses LlamaIndex SemanticSimilarityEvaluator (internally uses
    Settings.embed_model for vectorization + cosine similarity).

    Args:
        question: The new question to check.
        history_questions: List of previously asked question texts.
        threshold: Similarity threshold for flagging as duplicate.

    Returns:
        DedupResult with duplicate flag, most similar match, and suggestion.
    """
    if not history_questions:
        return DedupResult(
            is_duplicate=False,
            most_similar=None,
            similarity_score=0.0,
            suggestion="",
        )

    sim_eval = SemanticSimilarityEvaluator(
        similarity_threshold=threshold,
    )

    best_score = 0.0
    best_match: str | None = None

    for hist_q in history_questions:
        result = await sim_eval.aevaluate(
            response=question,
            reference=hist_q,
        )
        score = result.score or 0.0
        if score > best_score:
            best_score = score
            best_match = hist_q

    is_dup = best_score >= threshold

    suggestion = ""
    if is_dup and best_match:
        suggestion = (
            f"This question is very similar to: \"{best_match[:120]}\" "
            f"(similarity: {best_score:.2f}). "
            "Consider asking a deeper follow-up, e.g. comparing concepts, "
            "applying to a different scenario, or evaluating trade-offs."
        )

    logger.info(
        "Dedup check — is_dup={}, best_score={:.3f}, question={}",
        is_dup, best_score, question[:80],
    )
    return DedupResult(
        is_duplicate=is_dup,
        most_similar=best_match,
        similarity_score=best_score,
        suggestion=suggestion,
    )
