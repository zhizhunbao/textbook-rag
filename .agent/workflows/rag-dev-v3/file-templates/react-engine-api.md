# 3.22 `features/engine/<engine-module>/api.ts` — Engine API 调用

```typescript
/**
 * <engine-module> API — <一句话描述>.
 *
 * All API calls for the <engine-module> module.
 * Uses shared/api/client for unified fetch.
 */

import { engineClient, payloadClient } from '@/features/shared/api/client'
import type { PaginatedResponse } from '@/features/shared/api/types'
import type { <Entity> } from './types'

// ============================================================
// Payload CMS (same-origin)
// ============================================================

/** Fetch all <entities> from Payload CMS. */
export async function fetch<Entities>(opts?: {
  limit?: number
  page?: number
}): Promise<{ items: <Entity>[]; total: number }> {
  const params = new URLSearchParams()
  params.set('limit', String(opts?.limit ?? 200))
  params.set('sort', '-updatedAt')
  if (opts?.page) params.set('page', String(opts.page))

  const data = await payloadClient.get<PaginatedResponse<<Entity>>>(
    `/api/<resource>?${params}`
  )
  return { items: data.docs, total: data.totalDocs }
}

/** Fetch a single <entity> by Payload ID. */
export async function fetch<Entity>(id: number): Promise<<Entity>> {
  return payloadClient.get<<Entity>>(`/api/<resource>/${id}`)
}

// ============================================================
// Engine FastAPI (cross-origin)
// ============================================================

/** Trigger <action> via Engine backend. */
export async function trigger<Action>(data: unknown): Promise<unknown> {
  return engineClient.post<unknown>('/engine/<resource>/<action>', data)
}
```
