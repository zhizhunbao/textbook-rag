"""backfill_evaluations — Re-evaluate historical queries with incomplete scores.

Scans Payload Evaluations for records with status='pending' or missing core
scores (ragScore/llmScore/answerScore all null), then re-runs full_evaluate()
to fill in the missing dimensions.

Usage:
    # Preview what would be updated (no changes)
    uv run python scripts/eval/backfill_evaluations.py --dry-run

    # Process up to 10 pending evaluations
    uv run python scripts/eval/backfill_evaluations.py --limit 10

    # Process all pending evaluations
    uv run python scripts/eval/backfill_evaluations.py

Ref: UEP-T2-03 — historical evaluation data backfill.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from loguru import logger

# Ensure project root is on sys.path so engine_v2 is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine_v2.settings import PAYLOAD_URL, init_settings  # noqa: E402


# ============================================================
# Constants
# ============================================================
PAYLOAD_TIMEOUT = 30.0


async def _get_token() -> str:
    """Authenticate with Payload and return a JWT token."""
    from engine_v2.settings import PAYLOAD_ADMIN_EMAIL, PAYLOAD_ADMIN_PASSWORD

    async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
        resp = await client.post(
            f"{PAYLOAD_URL}/api/users/login",
            json={"email": PAYLOAD_ADMIN_EMAIL, "password": PAYLOAD_ADMIN_PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()

    token = data.get("token")
    if not token:
        raise RuntimeError("Payload login succeeded but no token returned")
    return token


async def _fetch_pending_evaluations(
    token: str,
    limit: int | None = None,
) -> list[dict]:
    """Fetch evaluations with status='pending' from Payload.

    Returns raw evaluation docs that need re-processing.
    """
    params: dict[str, str] = {
        "where[status][equals]": "pending",
        "sort": "createdAt",
        "limit": str(limit or 100),
    }
    headers = {"Authorization": f"JWT {token}"}

    async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
        resp = await client.get(
            f"{PAYLOAD_URL}/api/evaluations",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    return data.get("docs", [])


async def _delete_evaluation(token: str, eval_id: int) -> bool:
    """Delete an evaluation record so full_evaluate() can create a fresh one."""
    headers = {"Authorization": f"JWT {token}"}
    try:
        async with httpx.AsyncClient(timeout=PAYLOAD_TIMEOUT) as client:
            resp = await client.delete(
                f"{PAYLOAD_URL}/api/evaluations/{eval_id}",
                headers=headers,
            )
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.warning("Failed to delete eval_id={}: {}", eval_id, exc)
        return False


async def run_backfill(dry_run: bool = False, limit: int | None = None) -> None:
    """Main backfill logic."""
    # Initialise LlamaIndex Settings (LLM + embeddings)
    init_settings()

    token = await _get_token()
    logger.info("Authenticated with Payload CMS")

    pending = await _fetch_pending_evaluations(token, limit=limit)
    logger.info("Found {} pending evaluations", len(pending))

    if not pending:
        logger.info("Nothing to backfill — all evaluations have scores.")
        return

    if dry_run:
        logger.info("=== DRY RUN — no changes will be made ===")
        for doc in pending:
            qref = doc.get("queryRef")
            q = (doc.get("query") or "")[:60]
            status = doc.get("status", "?")
            rag = doc.get("ragScore")
            llm = doc.get("llmScore")
            ans = doc.get("answerScore")
            logger.info(
                "  eval_id={} queryRef={} status={} rag={} llm={} answer={} q={}",
                doc["id"], qref, status, rag, llm, ans, q,
            )
        logger.info("Would re-evaluate {} records. Run without --dry-run to proceed.", len(pending))
        return

    # Import full_evaluate after init_settings
    from engine_v2.evaluation.history import full_evaluate

    success = 0
    failed = 0

    for i, doc in enumerate(pending, 1):
        eval_id = doc["id"]
        query_ref = doc.get("queryRef")

        if not query_ref:
            logger.warning(
                "[{}/{}] eval_id={} has no queryRef — skipping",
                i, len(pending), eval_id,
            )
            failed += 1
            continue

        logger.info(
            "[{}/{}] Re-evaluating eval_id={} queryRef={} q={}",
            i, len(pending), eval_id, query_ref, (doc.get("query") or "")[:50],
        )

        # Delete old incomplete record
        deleted = await _delete_evaluation(token, eval_id)
        if not deleted:
            logger.warning("Could not delete eval_id={}, skipping", eval_id)
            failed += 1
            continue

        # Re-run full evaluation (creates a new record)
        try:
            result = await full_evaluate(query_ref)
            logger.info(
                "  → overall={} status={} rag={} llm={} answer={}",
                result.overall_score, result.status,
                result.rag_score, result.llm_score, result.answer_score,
            )
            success += 1
        except Exception as exc:
            logger.error("  → FAILED: {}", exc)
            failed += 1

    logger.info(
        "Backfill complete: {}/{} succeeded, {} failed",
        success, len(pending), failed,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Re-evaluate pending/incomplete historical evaluations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview records that would be re-evaluated without making changes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of pending evaluations to process.",
    )
    args = parser.parse_args()

    asyncio.run(run_backfill(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
