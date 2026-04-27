import type { CollectionAfterChangeHook } from 'payload'

/**
 * Queries afterChange hook — auto-trigger evaluation (EV2-T3-01).
 *
 * When a new Query is created, fires a non-blocking POST to the
 * engine's /engine/evaluation/auto-evaluate endpoint.
 *
 * The engine checks AUTO_EVAL_ENABLED internally; if disabled,
 * it returns immediately without running evaluation.
 *
 * This hook never blocks or fails the query creation — all errors
 * are silently logged.
 */

const ENGINE_URL = process.env.ENGINE_URL || 'http://127.0.0.1:8001'

export const afterChangeHook: CollectionAfterChangeHook = async ({
  doc,
  operation,
  req,
}) => {
  // Only trigger on new query creation, not updates
  if (operation !== 'create') return doc

  const queryId = doc.id
  if (!queryId) return doc

  // Fire-and-forget: POST to engine auto-evaluate endpoint
  try {
    fetch(`${ENGINE_URL}/engine/evaluation/auto-evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_id: queryId }),
    }).catch((err) => {
      req.payload.logger.warn(
        `[Queries.afterChange] Auto-eval trigger failed: ${err instanceof Error ? err.message : String(err)}`
      )
    })

    req.payload.logger.info(
      `[Queries.afterChange] Auto-eval triggered for query_id=${queryId}`
    )
  } catch {
    // Completely non-blocking — never fail the query creation
  }

  return doc
}
