"""models — Unified data classes for the evaluation module.

All dataclasses used across the evaluation pipeline are defined here.
Individual metric files, runners, and persistence layers import from this
single source of truth.

Groups:
    MetricResult        — universal return type for every metric file
    EvalResult          — legacy 5-dimensional single-query result
    FullEvalResult      — four-category (RAG/LLM/Answer/Question) evaluation
    DepthResult         — question cognitive depth assessment
    DedupResult         — question deduplication
    QueryRecord         — fetched Payload Queries record
    HistoryEvalResult   — historical query evaluation
    RetrievalMetrics    — pure-math IR metrics container
    GoldenRecord        — Golden Dataset QA pair
    GoldenDatasetResult — golden dataset generation result
    PairwiseResult      — A/B pairwise comparison
    BatchCompareResult  — batch pairwise summary
    CompareItem         — input for batch comparison
    Suggestion          — improvement suggestion
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# MetricResult — universal return type for all metric files
# ============================================================
@dataclass
class MetricResult:
    """Universal return type for a single evaluation metric.

    Every metric file (faithfulness.py, relevancy.py, etc.) returns this.
    """

    name: str
    score: float | None = None
    feedback: str = ""
    label: str | None = None    # categorical metrics (e.g. depth)
    passed: bool | None = None  # boolean metrics (e.g. guidelines)


# ============================================================
# EvalResult — legacy 5-dimensional single-query result
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


# ============================================================
# DepthResult — question cognitive depth assessment
# ============================================================
@dataclass
class DepthResult:
    """Question cognitive depth assessment result."""

    question: str
    depth: str  # "surface" | "understanding" | "synthesis"
    score: float  # 1.0–5.0
    reasoning: str


# ============================================================
# DedupResult — question deduplication
# ============================================================
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


# ============================================================
# QueryRecord — fetched Payload Queries record
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


# ============================================================
# HistoryEvalResult — historical query evaluation
# ============================================================
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
# RetrievalMetrics — pure-math IR metrics container
# ============================================================
@dataclass
class RetrievalMetrics:
    """Container for retrieval quality metrics (all 0-1 scale)."""

    hit_rate: float = 0.0
    mrr: float = 0.0
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    ndcg: float = 0.0
    ir_score: float = 0.0  # Mean of all metrics

    def to_dict(self) -> dict[str, float]:
        """Serialize to dict for API/Payload persistence."""
        return {
            "hit_rate": round(self.hit_rate, 4),
            "mrr": round(self.mrr, 4),
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "ndcg": round(self.ndcg, 4),
            "ir_score": round(self.ir_score, 4),
        }


# ============================================================
# GoldenRecord — Golden Dataset QA pair
# ============================================================
@dataclass
class GoldenRecord:
    """A single Golden Dataset QA pair."""

    question: str
    expected_answer: str
    expected_chunk_ids: list[str] = field(default_factory=list)
    book_id: str | None = None
    source_page: str = ""
    verified: bool = False
    verification_source: str | None = None  # 'auto' | 'manual' (EUX-T1-01)
    tags: list[str] = field(default_factory=list)
    id: int | None = None  # Payload record ID (set after persistence)


@dataclass
class GoldenDatasetResult:
    """Result of golden dataset generation."""

    book_id: str
    records: list[GoldenRecord]
    total_generated: int
    errors: list[str] = field(default_factory=list)


# ============================================================
# PairwiseResult — A/B comparison
# ============================================================
@dataclass
class PairwiseResult:
    """Result of an A/B pairwise comparison.

    Attributes:
        question: The query both answers respond to.
        winner: "A", "B", or "tie".
        score: 1.0 = A wins, 0.0 = B wins, 0.5 = tie.
        reasoning: LLM judge's explanation.
        invalid: True if the judge output could not be parsed.
    """

    question: str
    winner: str  # "A" | "B" | "tie"
    score: float  # 1.0=A, 0.0=B, 0.5=tie
    reasoning: str
    invalid: bool = False


@dataclass
class BatchCompareResult:
    """Summary of batch pairwise comparisons."""

    results: list[PairwiseResult]
    a_wins: int = 0
    b_wins: int = 0
    ties: int = 0
    total: int = 0
    invalid_count: int = 0


@dataclass
class CompareItem:
    """A single question + two answers for batch comparison."""

    question: str
    answer_a: str
    answer_b: str
    reference: str | None = None


# ============================================================
# Suggestion — improvement suggestion
# ============================================================
@dataclass
class Suggestion:
    """A single improvement suggestion."""

    dimension: str
    severity: str  # 'high' | 'medium' | 'low' | 'info'
    message_en: str
    message_zh: str

    def to_dict(self) -> dict[str, str]:
        """Serialise for JSON persistence."""
        return {
            "dimension": self.dimension,
            "severity": self.severity,
            "message_en": self.message_en,
            "message_zh": self.message_zh,
        }


# ============================================================
# QuestionHit / RetrievalEvalResult — QuestionSet-level retrieval
# ============================================================
@dataclass
class QuestionHit:
    """Per-question retrieval result."""

    question_id: int
    question: str
    source_chunk_id: str
    hit: bool
    rank: int | None = None  # Position of source chunk (1-indexed), None = miss
    retrieved_ids: list[str] = field(default_factory=list)


@dataclass
class RetrievalEvalResult:
    """Aggregate retrieval evaluation result for a QuestionSet."""

    dataset_id: int
    hit_rate: float = 0.0
    mrr: float = 0.0
    total_questions: int = 0
    hits: int = 0
    misses: int = 0
    per_question: list[QuestionHit] = field(default_factory=list)
    reranker_used: bool = False

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "dataset_id": self.dataset_id,
            "hit_rate": round(self.hit_rate, 4),
            "mrr": round(self.mrr, 4),
            "total_questions": self.total_questions,
            "hits": self.hits,
            "misses": self.misses,
            "reranker_used": self.reranker_used,
            "per_question": [
                {
                    "question_id": q.question_id,
                    "question": q.question,
                    "source_chunk_id": q.source_chunk_id,
                    "hit": q.hit,
                    "rank": q.rank,
                }
                for q in self.per_question
            ],
        }
