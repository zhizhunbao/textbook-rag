"""evaluation — Unified RAG quality evaluation hub.

Public API — all imports from this package should come through here.
Internal subpackages: metrics/, metrics/ir/, runners/, persistence/
"""

# ── Models (dataclasses) ──
from engine_v2.evaluation.models import (
    BatchCompareResult,
    CompareItem,
    DedupResult,
    DepthResult,
    EvalResult,
    FullEvalResult,
    GoldenRecord,
    GoldenDatasetResult,
    HistoryEvalResult,
    MetricResult,
    PairwiseResult,
    QueryRecord,
    RetrievalMetrics,
    Suggestion,
)

# ── Metrics (one file per metric) ──
from engine_v2.evaluation.metrics.question_depth import (
    QuestionDepthEvaluator,
    assess_question_depth,
)
from engine_v2.evaluation.metrics.dedup import question_dedup
from engine_v2.evaluation.metrics.completeness import CompletenessEvaluator
from engine_v2.evaluation.metrics.clarity import ClarityEvaluator
from engine_v2.evaluation.metrics.pairwise import compare_answers, compare_batch

# ── IR Metrics ──
from engine_v2.evaluation.metrics.ir.aggregate import compute_all_ir_metrics

# ── Aggregation ──
from engine_v2.evaluation.aggregation import compute_aggregate_scores

# ── Runners ──
from engine_v2.evaluation.runners.response import evaluate_response, evaluate_dataset
from engine_v2.evaluation.runners.single import evaluate_single_from_query
from engine_v2.evaluation.runners.batch import evaluate_batch_from_queries
from engine_v2.evaluation.runners.full import full_evaluate
from engine_v2.evaluation.runners.auto import auto_evaluate_query

# ── Suggestions ──
from engine_v2.evaluation.suggestions import generate_suggestions

# ── Persistence (public helpers) ──
from engine_v2.evaluation.persistence.auth import get_payload_token
from engine_v2.evaluation.persistence.queries import fetch_recent_queries


__all__ = [
    # Models
    "BatchCompareResult",
    "ClarityEvaluator",
    "CompareItem",
    "CompletenessEvaluator",
    "DedupResult",
    "DepthResult",
    "EvalResult",
    "FullEvalResult",
    "GoldenRecord",
    "GoldenDatasetResult",
    "HistoryEvalResult",
    "MetricResult",
    "PairwiseResult",
    "QueryRecord",
    "QuestionDepthEvaluator",
    "RetrievalMetrics",
    "Suggestion",
    # Metrics
    "assess_question_depth",
    "compare_answers",
    "compare_batch",
    "compute_aggregate_scores",
    "compute_all_ir_metrics",
    "question_dedup",
    # Runners
    "auto_evaluate_query",
    "evaluate_batch_from_queries",
    "evaluate_dataset",
    "evaluate_response",
    "evaluate_single_from_query",
    "full_evaluate",
    # Suggestions
    "generate_suggestions",
    # Persistence
    "get_payload_token",
    "fetch_recent_queries",
]
