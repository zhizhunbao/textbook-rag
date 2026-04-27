"""router — Depth→retrieval strategy router (EV2-T4-01).

Routes queries to different retrieval strategies based on cognitive depth:

    | Depth           | Route          | Strategy                          |
    |-----------------|----------------|-----------------------------------|
    | surface (1-2)   | standard       | Existing get_query_engine()       |
    | understanding 3 | smart          | Multi-query parallel (Sprint 5)   |
    | synthesis (4-5) | deep           | Plan→ReAct→Write (Sprint 5)      |

Currently only ``standard`` is implemented; ``smart`` and ``deep``
fall back to ``standard`` until Sprint 5 provides those engines.

Ref: engine_v2/evaluation/evaluator.py — assess_question_depth()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from loguru import logger

# ============================================================
# Types
# ============================================================
RetrievalStrategy = Literal["standard", "smart", "deep"]
RetrievalMode = Literal["standard", "smart", "deep", "auto"]


@dataclass
class RoutingDecision:
    """Result of the query router's decision.

    Attributes:
        strategy: The retrieval strategy to use.
        depth: Cognitive depth label (surface/understanding/synthesis).
        depth_score: Raw depth score (1-5 scale).
        reasoning: Why this strategy was chosen.
        is_fallback: True if the chosen strategy is a fallback
            (i.e., the preferred strategy is not yet implemented).
    """

    strategy: RetrievalStrategy
    depth: str | None = None
    depth_score: float | None = None
    reasoning: str = ""
    is_fallback: bool = False


# ============================================================
# Depth → strategy mapping
# ============================================================
# Thresholds: score ≥ N → strategy
_DEPTH_STRATEGY_MAP: list[tuple[float, RetrievalStrategy]] = [
    (4.0, "deep"),        # synthesis → deep solve
    (2.5, "smart"),       # understanding → smart retrieve
    # < 2.5 → standard
]

# Strategies that have working implementations
_IMPLEMENTED_STRATEGIES: set[RetrievalStrategy] = {"standard"}


# ============================================================
# Router
# ============================================================
class QueryRouter:
    """Route queries to retrieval strategies based on cognitive depth.

    Usage::

        router = QueryRouter()
        decision = await router.route("What are the key differences between...")
        # decision.strategy == "smart"

    When the preferred strategy is not yet implemented, falls back to
    ``standard`` and sets ``decision.is_fallback = True``.
    """

    async def route(
        self,
        question: str,
        *,
        mode: RetrievalMode = "auto",
        llm=None,
    ) -> RoutingDecision:
        """Route a question to a retrieval strategy.

        Args:
            question: The user's question.
            mode: Override mode. "auto" uses the depth-based router;
                "standard"/"smart"/"deep" skip routing.
            llm: Optional LLM override for depth assessment.

        Returns:
            RoutingDecision with chosen strategy and reasoning.
        """
        # Explicit mode — skip depth assessment
        if mode != "auto":
            is_fb = mode not in _IMPLEMENTED_STRATEGIES
            actual = mode if not is_fb else "standard"
            logger.info(
                "Router: explicit mode={} → strategy={} (fallback={})",
                mode, actual, is_fb,
            )
            return RoutingDecision(
                strategy=actual,
                reasoning=f"Explicit mode: {mode}",
                is_fallback=is_fb,
            )

        # Auto mode — assess depth then route
        try:
            from engine_v2.evaluation.evaluator import assess_question_depth

            depth_result = await assess_question_depth(question, llm=llm)
            depth = depth_result.depth
            score = depth_result.score
            reasoning = depth_result.reasoning
        except Exception as exc:
            logger.warning("Router: depth assessment failed, falling back: {}", exc)
            return RoutingDecision(
                strategy="standard",
                reasoning=f"Depth assessment failed: {exc}",
                is_fallback=False,
            )

        # Map depth score to strategy
        preferred: RetrievalStrategy = "standard"
        for threshold, strat in _DEPTH_STRATEGY_MAP:
            if score >= threshold:
                preferred = strat
                break

        # Check implementation availability
        is_fb = preferred not in _IMPLEMENTED_STRATEGIES
        actual = preferred if not is_fb else "standard"

        logger.info(
            "Router: auto — depth={}, score={:.1f} → preferred={}, actual={} (fallback={})",
            depth, score, preferred, actual, is_fb,
        )

        return RoutingDecision(
            strategy=actual,
            depth=depth,
            depth_score=score,
            reasoning=reasoning,
            is_fallback=is_fb,
        )


# Module-level singleton
_router: QueryRouter | None = None


def get_router() -> QueryRouter:
    """Get the module-level QueryRouter singleton."""
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router
