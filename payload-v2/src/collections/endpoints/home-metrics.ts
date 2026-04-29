/**
 * collections/endpoints/home-metrics.ts
 * Payload Custom Endpoint: GET /api/home-metrics
 *
 * Public aggregate metrics for the marketing homepage. Returns counts only;
 * no document content or user-owned records are exposed.
 */

import type { Endpoint, PayloadRequest, Where } from 'payload'

async function countDocs(
  payload: PayloadRequest['payload'],
  collection: string,
  where?: Where,
) {
  const result = await payload.find({
    collection: collection as any,
    where,
    limit: 0,
    depth: 0,
    overrideAccess: true,
  })

  return result.totalDocs
}

export const homeMetricsEndpoint: Endpoint = {
  method: 'get',
  path: '/home-metrics',
  handler: async (req) => {
    try {
      const { payload } = req
      const [expertRoles, indexedBooks, knowledgeChunks, evaluations] = await Promise.all([
        countDocs(payload, 'consulting-personas', { isEnabled: { equals: true } }),
        countDocs(payload, 'books', { status: { equals: 'indexed' } }),
        countDocs(payload, 'chunks'),
        countDocs(payload, 'evaluations'),
      ])

      return Response.json({
        expertRoles,
        indexedBooks,
        knowledgeChunks,
        evaluations,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      return Response.json({ error: message }, { status: 500 })
    }
  },
}
