/**
 * collections/endpoints/seed.ts
 * Payload Custom Endpoint: POST /api/seed
 *
 * Seeds default data into Payload collections using Local API.
 * Strategy: **DELETE ALL → RECREATE** (覆盖更新，先清空再写入).
 * Uses overrideAccess to bypass auth — seed runs during initial setup.
 *
 * Body (optional): { collections?: string[] }
 *   - If omitted, seeds all collections
 *   - If provided, seeds only the specified slugs
 */

import type { Endpoint, PayloadRequest } from 'payload'

import { seedCollections, type SeedCollection } from '../../seed'
import { seedPersonaDataSources } from '../../seed/data-sources-persona'

interface SeedResult {
  slug: string
  label: string
  deleted: number
  created: number
  errors: string[]
}

/**
 * Seed one collection: delete all existing → create all from seed data.
 * Exception: 'users' collection skips delete to preserve admin accounts.
 */
async function seedOne(
  payload: PayloadRequest['payload'],
  col: SeedCollection,
): Promise<SeedResult> {
  const result: SeedResult = {
    slug: col.slug,
    label: col.label,
    deleted: 0,
    created: 0,
    errors: [],
  }

  // Step 1: Delete all existing records (except users)
  if (col.slug !== 'users') {
    try {
      const existing = await payload.find({
        collection: col.slug as any,
        limit: 500,
        overrideAccess: true,
      })
      for (const doc of existing.docs) {
        await payload.delete({
          collection: col.slug as any,
          id: doc.id,
          overrideAccess: true,
        })
        result.deleted++
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      result.errors.push(`delete-all: ${msg}`)
    }
  }

  // Step 2: Create all seed records
  for (const item of col.data) {
    try {
      if (col.slug === 'users') {
        // Users: upsert by uniqueField to avoid duplicates
        const uniqueValue = item[col.uniqueField] as string
        const existing = await payload.find({
          collection: col.slug as any,
          where: { [col.uniqueField]: { equals: uniqueValue } },
          limit: 1,
          overrideAccess: true,
        })
        if (existing.docs.length > 0) {
          // Skip — don't overwrite user's changed password
          continue
        }
      }

      await payload.create({
        collection: col.slug as any,
        data: item as any,
        overrideAccess: true,
      })
      result.created++
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      result.errors.push(`${item[col.uniqueField]}: ${msg}`)
    }
  }

  return result
}

export const seedEndpoint: Endpoint = {
  handler: async (req) => {
    try {
      const { payload } = req

      // Optionally filter which collections to seed
      let targetSlugs: string[] | undefined
      try {
        if (req.json) {
          const body = await req.json()
          if (body?.collections && Array.isArray(body.collections)) {
            targetSlugs = body.collections
          }
        }
      } catch {
        // No body or invalid JSON — seed all
      }

      const seedAll = !targetSlugs
      const seedDataSources = seedAll || targetSlugs?.includes('data-sources')

      // When data-sources is targeted individually, also seed consulting-personas first
      // (persona IDs are required to create data source records)
      const effectiveSlugs = targetSlugs
        ? (targetSlugs.includes('data-sources') && !targetSlugs.includes('consulting-personas'))
          ? [...targetSlugs, 'consulting-personas']
          : targetSlugs
        : undefined

      const collections = effectiveSlugs
        ? seedCollections.filter((c) => effectiveSlugs.includes(c.slug))
        : seedCollections

      const results: SeedResult[] = []
      for (const col of collections) {
        const r = await seedOne(payload, col)
        results.push(r)
      }

      // Seed persona-linked data sources (only when seed-all or data-sources targeted)
      if (seedDataSources) {
        const personaSeedResult = await seedPersonaDataSources(payload)
        results.push({
          slug: 'data-sources',
          label: 'Data Sources (Persona)',
          deleted: personaSeedResult.deleted,
          created: personaSeedResult.created,
          errors: personaSeedResult.errors,
        })
      }

      return Response.json({ success: true, results })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      return Response.json({ success: false, error: message }, { status: 500 })
    }
  },
  method: 'post',
  path: '/seed',
}
