/**
 * collections/endpoints/sync-catalog.ts
 * Payload Custom Endpoint: POST /api/llms/sync-catalog
 *
 * Fetches the full model catalog from Engine v2 (which builds it from
 * Ollama + HuggingFace APIs), then upserts every model into the Llms
 * collection so the data persists across engine restarts.
 *
 * Usage:
 *   POST /api/llms/sync-catalog          — sync all models
 *   POST /api/llms/sync-catalog?force=1  — force engine cache rebuild first
 */

import type { PayloadRequest } from 'payload'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

interface CatalogModel {
  name: string
  displayName: string
  family: string
  category: string
  modelType: string   // 'chat' | 'embedding' | 'vision'
  parameterSize: string
  description: string
  advantages: string[]
  bestFor: string[]
  contextWindow: number
  released: string
  minRamGb: number
  languages: string
  downloads: number
  likes: number
  license: string
  hfRepo: string
  installed: boolean
  source: string
}

/**
 * Diff check: return true only when at least one tracked field has changed.
 * Avoids issuing a Payload write for models that haven't changed.
 *
 * Volatile fields (re-checked every sync): installed, downloads, likes, released
 * Stable fields: only update when existing value is absent/empty or differs
 */
function hasChanged(existing: Record<string, any>, next: Record<string, any>): boolean {
  // Always re-check volatile fields (change frequently)
  const volatile = ['installed', 'downloads', 'likes', 'released'] as const
  for (const key of volatile) {
    if (existing[key] !== next[key]) return true
  }
  // Stable scalar fields: update only when existing is empty or value changed
  const stable = [
    'displayName', 'family', 'category', 'modelType', 'source',
    'parameterSize', 'contextWindow', 'minRamGb', 'languages',
    'license', 'hfRepo', 'description',
  ] as const
  for (const key of stable) {
    const existingVal = existing[key]
    const nextVal = next[key]
    const existingEmpty = existingVal === null || existingVal === undefined || existingVal === ''
    if (existingEmpty && nextVal) return true
    if (!existingEmpty && existingVal !== nextVal) return true
  }
  // JSON array fields: advantages, bestFor
  for (const key of ['advantages', 'bestFor'] as const) {
    const existingArr: string[] = Array.isArray(existing[key]) ? existing[key] : []
    const nextArr: string[] = Array.isArray(next[key]) ? next[key] : []
    if (existingArr.join('|') !== nextArr.join('|')) return true
  }
  return false
}

export async function syncCatalogEndpoint(req: PayloadRequest): Promise<Response> {
  try {
    const { payload } = req

    // 1. Fetch full catalog from Engine (force=true bypasses SWR cache)
    const t0 = Date.now()
    const engineRes = await fetch(`${ENGINE}/engine/llms/library/search?sort=downloads&force=true`)
    if (!engineRes.ok) {
      return Response.json(
        { success: false, error: `Engine returned ${engineRes.status}` },
        { status: 502 },
      )
    }

    const data = await engineRes.json() as { models: CatalogModel[]; count: number }
    const models = data.models ?? []
    console.log(`[sync-catalog] Engine fetch: ${models.length} models in ${Date.now() - t0}ms`)

    // 2. ONE bulk read — load all existing DB records into memory
    const t1 = Date.now()
    const existingDocs = await payload.find({
      collection: 'llms',
      limit: 1000,
      depth: 0,  // no relation expansion needed
    })
    // Build name → doc map for O(1) lookup
    const existingMap = new Map<string, Record<string, any>>(
      (existingDocs.docs as Record<string, any>[]).map((doc) => [doc.name as string, doc])
    )
    const catalogNames = new Set(models.map((m) => m.name))
    console.log(`[sync-catalog] DB bulk read: ${existingDocs.docs.length} records in ${Date.now() - t1}ms`)

    const results = {
      created: 0,
      updated: 0,
      skipped: 0,
      errors: [] as string[],
      total: models.length,
    }

    // 3. In-memory diff → targeted writes only
    const toCatalogData = (m: CatalogModel) => ({
      displayName: m.displayName || undefined,
      family: m.family || undefined,
      category: (m.category as 'recommended' | 'reasoning' | 'lightweight' | 'specialized') || undefined,
      modelType: (m.modelType as 'chat' | 'embedding' | 'vision') || 'chat',
      installed: m.installed,
      source: (m.source as 'ollama' | 'huggingface') || 'ollama',
      released: m.released || undefined,
      downloads: m.downloads || undefined,
      likes: m.likes || undefined,
      license: m.license || undefined,
      hfRepo: m.hfRepo || undefined,
      advantages: m.advantages?.length ? m.advantages : undefined,
      bestFor: m.bestFor?.length ? m.bestFor : undefined,
      description: m.description || undefined,
      parameterSize: m.parameterSize || undefined,
      contextWindow: m.contextWindow || undefined,
      minRamGb: m.minRamGb || undefined,
      languages: m.languages || undefined,
    })

    const t2 = Date.now()
    const BATCH_SIZE = 10

    // Process models in concurrent batches for faster DB writes
    // 分批并发写入数据库，比逐条 await 快 ~10 倍
    for (let i = 0; i < models.length; i += BATCH_SIZE) {
      const batch = models.slice(i, i + BATCH_SIZE)
      const settled = await Promise.allSettled(
        batch.map(async (m) => {
          const catalogData = toCatalogData(m)
          const existing = existingMap.get(m.name)

          if (existing) {
            if (!hasChanged(existing, catalogData)) {
              results.skipped++
              return
            }
            await payload.update({ collection: 'llms', id: existing.id, data: catalogData })
            results.updated++
          } else {
            await payload.create({
              collection: 'llms',
              data: {
                name: m.name,
                provider: 'ollama',
                isFree: true,
                isEnabled: true,
                isDefault: false,
                sortOrder: 0,
                ...catalogData,
              },
            })
            results.created++
          }
        })
      )
      for (const r of settled) {
        if (r.status === 'rejected') {
          results.errors.push(String(r.reason))
        }
      }
    }

    // 4. Prune stale records (already loaded in existingMap — no extra DB read needed)
    //    Only prune: not in new catalog + not installed + not default
    let pruned = 0
    for (const [name, doc] of existingMap) {
      if (!catalogNames.has(name) && !doc.installed && !doc.isDefault) {
        try {
          await payload.delete({ collection: 'llms', id: doc.id })
          pruned++
        } catch (err) {
          results.errors.push(`prune ${name}: ${err instanceof Error ? err.message : String(err)}`)
        }
      }
    }
    console.log(`[sync-catalog] Writes done in ${Date.now() - t2}ms — created:${results.created} updated:${results.updated} skipped:${results.skipped}`)

    return Response.json({ success: true, ...results, pruned })

  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return Response.json({ success: false, error: message }, { status: 500 })
  }
}

