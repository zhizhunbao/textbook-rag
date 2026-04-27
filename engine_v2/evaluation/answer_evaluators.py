"""answer_evaluators — Completeness + Clarity evaluators for Answer scoring.

EV2-T2-01: Two custom evaluators that extend CorrectnessEvaluator with
domain-specific eval templates.  Both output a 1–5 score + reasoning.

    CompletenessEvaluator — does the answer fully cover all question aspects?
    ClarityEvaluator      — is the answer clear, well-structured, and readable?

Prompt templates are defined in ``evaluation/prompts.py``.

Ref: llama_index.core.evaluation.correctness — CorrectnessEvaluator
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from llama_index.core.evaluation import CorrectnessEvaluator

from engine_v2.evaluation.prompts import (
    CLARITY_EVAL_TEMPLATE,
    COMPLETENESS_EVAL_TEMPLATE,
)


# ============================================================
# CompletenessEvaluator
# ============================================================
class CompletenessEvaluator(CorrectnessEvaluator):
    """Evaluate whether an answer fully covers all aspects of the question.

    Inherits CorrectnessEvaluator with a custom eval_template.
    Outputs a 1–5 score where 5 = comprehensive coverage.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            eval_template=COMPLETENESS_EVAL_TEMPLATE,
            score_threshold=3.0,  # ≥3 = acceptable completeness
            **kwargs,
        )
        logger.debug("CompletenessEvaluator initialized")


# ============================================================
# ClarityEvaluator
# ============================================================
class ClarityEvaluator(CorrectnessEvaluator):
    """Evaluate answer clarity, structure, and readability.

    Inherits CorrectnessEvaluator with a custom eval_template.
    Outputs a 1–5 score where 5 = exceptionally clear.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            eval_template=CLARITY_EVAL_TEMPLATE,
            score_threshold=3.0,  # ≥3 = acceptable clarity
            **kwargs,
        )
        logger.debug("ClarityEvaluator initialized")
