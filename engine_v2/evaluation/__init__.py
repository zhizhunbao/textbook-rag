"""evaluation — Unified RAG quality evaluation hub.

Public API:
    evaluate_response              — 5-dimensional single-query evaluation
    evaluate_dataset               — batch evaluation via BatchEvalRunner
    assess_question_depth          — question cognitive depth (surface/understanding/synthesis)
    question_dedup                 — semantic similarity deduplication
    build_evaluators               — factory: build evaluator dicts by mode
    QuestionDepthEvaluator         — CorrectnessEvaluator subclass for depth scoring
    evaluate_single_from_query     — evaluate a single existing Queries record
    evaluate_batch_from_queries    — batch-evaluate recent Queries records
    full_evaluate                  — four-category evaluation (RAG/LLM/Answer/Question) — EV2-T2
    EvalResult                     — 5-dimensional evaluation result dataclass
    FullEvalResult                 — four-category evaluation result dataclass — EV2-T2
    DepthResult                    — depth assessment result dataclass
    DedupResult                    — deduplication result dataclass
    QueryRecord                    — fetched Queries record dataclass
    HistoryEvalResult              — history evaluation result dataclass
    CompletenessEvaluator          — answer completeness evaluator — EV2-T2
    ClarityEvaluator               — answer clarity evaluator — EV2-T2
    compute_aggregate_scores       — compute rag/llm/answer/overall aggregates — EV2-T2
    generate_suggestions           — rule-based improvement suggestions — EUX-T3
    Suggestion                     — improvement suggestion dataclass — EUX-T3
"""

from engine_v2.evaluation.answer_evaluators import (
    ClarityEvaluator,
    CompletenessEvaluator,
)
from engine_v2.evaluation.evaluator import (
    DedupResult,
    DepthResult,
    EvalResult,
    FullEvalResult,
    QuestionDepthEvaluator,
    assess_question_depth,
    build_evaluators,
    compute_aggregate_scores,
    evaluate_dataset,
    evaluate_response,
    question_dedup,
)
from engine_v2.evaluation.history import (
    HistoryEvalResult,
    QueryRecord,
    auto_evaluate_query,
    evaluate_batch_from_queries,
    evaluate_single_from_query,
    full_evaluate,
)
from engine_v2.evaluation.suggestions import (
    Suggestion,
    generate_suggestions,
)

__all__ = [
    "ClarityEvaluator",
    "CompletenessEvaluator",
    "DedupResult",
    "DepthResult",
    "EvalResult",
    "FullEvalResult",
    "HistoryEvalResult",
    "QueryRecord",
    "QuestionDepthEvaluator",
    "assess_question_depth",
    "auto_evaluate_query",
    "build_evaluators",
    "compute_aggregate_scores",
    "evaluate_batch_from_queries",
    "evaluate_dataset",
    "evaluate_response",
    "evaluate_single_from_query",
    "full_evaluate",
    "generate_suggestions",
    "question_dedup",
    "Suggestion",
]
