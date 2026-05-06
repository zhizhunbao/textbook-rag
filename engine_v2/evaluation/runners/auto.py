"""auto — Fire-and-forget auto-evaluation trigger.

Called by the Payload afterChange hook on the Queries collection.
"""

from __future__ import annotations

from loguru import logger


async def auto_evaluate_query(query_id: int) -> None:
    """Fire-and-forget auto-evaluation for a newly created query.

    Silently catches all exceptions to avoid disrupting the query flow.

    Args:
        query_id: Payload Queries record ID.
    """
    from engine_v2.settings import AUTO_EVAL_ENABLED

    if not AUTO_EVAL_ENABLED:
        logger.debug("Auto-eval disabled, skipping query_id={}", query_id)
        return

    try:
        from engine_v2.evaluation.runners.full import full_evaluate

        logger.info("Auto-eval triggered for query_id={}", query_id)
        result = await full_evaluate(query_id)
        logger.info(
            "Auto-eval complete for query_id={} — overall={}, status={}",
            query_id, result.overall_score, result.status,
        )
    except Exception as exc:
        logger.warning("Auto-eval failed for query_id={}: {}", query_id, exc)
