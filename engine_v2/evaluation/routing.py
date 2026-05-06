"""routing — Post-hoc routing correctness assessment.

Extracted from history.py to isolate routing evaluation logic.
Determines whether the query routing strategy was appropriate
given the actual evaluation scores.
"""

from __future__ import annotations

from engine_v2.evaluation.models import FullEvalResult


def assess_routing_correctness(
    result: FullEvalResult,
) -> tuple[str | None, bool | None, str]:
    """Post-hoc assessment of routing decision correctness (EV2-T4-02).

    Infers what strategy *was* used from question depth, then evaluates
    whether that strategy was appropriate given the actual eval scores.

    Rules:
        - Routed to standard but rag_score < 0.5 → should have upgraded
        - Routed to smart/deep but rag_score >= 0.8 → standard was enough
        - answer_score low but rag_score high → LLM issue, not retrieval

    Returns:
        (routing_decision, routing_correct, reasoning)
    """
    from engine_v2.settings import ROUTING_UPGRADE_THRESHOLD, ROUTING_DOWNGRADE_THRESHOLD

    depth = result.question_depth
    if not depth:
        return None, None, ""

    # Infer what strategy the router would have chosen
    if depth == "synthesis":
        decision = "deep"
    elif depth == "understanding":
        decision = "smart"
    else:
        decision = "standard"

    rag = result.rag_score
    answer = result.answer_score

    # Cannot assess without scores
    if rag is None and answer is None:
        return decision, None, "Insufficient scores for routing assessment."

    reasons: list[str] = []
    correct = True

    # Rule 1: Standard route but poor RAG → should upgrade
    if decision == "standard" and rag is not None and rag < ROUTING_UPGRADE_THRESHOLD:
        correct = False
        reasons.append(
            f"Routed to standard but rag_score={rag:.2f} < {ROUTING_UPGRADE_THRESHOLD}; "
            "consider upgrading to smart retrieve."
        )

    # Rule 2: Upgraded route but RAG already excellent → wasted resources
    if decision in ("smart", "deep") and rag is not None and rag >= ROUTING_DOWNGRADE_THRESHOLD:
        correct = False
        reasons.append(
            f"Routed to {decision} but rag_score={rag:.2f} >= {ROUTING_DOWNGRADE_THRESHOLD}; "
            "standard retrieval would suffice."
        )

    # Rule 3: Good RAG but poor answer → LLM problem, not retrieval
    if (
        rag is not None and rag >= 0.7
        and answer is not None and answer < 0.5
    ):
        reasons.append(
            f"rag_score={rag:.2f} is good but answer_score={answer:.2f} is low; "
            "issue is in LLM generation, not retrieval strategy."
        )

    reasoning = " | ".join(reasons) if reasons else "Routing appropriate for observed scores."
    return decision, correct, reasoning
