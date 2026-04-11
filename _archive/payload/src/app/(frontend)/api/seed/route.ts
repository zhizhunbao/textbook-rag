/**
 * POST /api/seed
 *
 * Seed default data into Payload collections using Local API.
 * No HTTP auth needed — runs server-side with full access.
 *
 * Body (optional): { collections?: string[] }
 *   - If omitted, seeds all collections
 *   - If provided, seeds only the specified slugs
 *
 * Returns: { results: { slug, created, updated, errors }[] }
 */

import { NextResponse } from 'next/server'
import { getPayload } from 'payload'
import config from '@payload-config'
import { seedCollections, type SeedCollection } from '@/seed/data'

interface SeedResult {
  slug: string
  label: string
  created: number
  updated: number
  errors: string[]
}

async function seedOne(
  payload: Awaited<ReturnType<typeof getPayload>>,
  col: SeedCollection,
): Promise<SeedResult> {
  const result: SeedResult = {
    slug: col.slug,
    label: col.label,
    created: 0,
    updated: 0,
    errors: [],
  }

  for (const item of col.data) {
    try {
      const uniqueValue = item[col.uniqueField] as string

      // Check if doc already exists
      const existing = await payload.find({
        collection: col.slug as any,
        where: { [col.uniqueField]: { equals: uniqueValue } },
        limit: 1,
      })

      if (existing.docs.length > 0) {
        // Update existing
        await payload.update({
          collection: col.slug as any,
          id: existing.docs[0].id,
          data: item as any,
        })
        result.updated++
      } else {
        // Create new
        await payload.create({
          collection: col.slug as any,
          data: item as any,
        })
        result.created++
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      result.errors.push(`${item[col.uniqueField]}: ${msg}`)
    }
  }

  return result
}

export async function POST(request: Request) {
  try {
    const payload = await getPayload({ config })

    // Optionally filter which collections to seed
    let targetSlugs: string[] | undefined
    try {
      const body = await request.json()
      if (body?.collections && Array.isArray(body.collections)) {
        targetSlugs = body.collections
      }
    } catch {
      // No body or invalid JSON — seed all
    }

    const collections = targetSlugs
      ? seedCollections.filter((c) => targetSlugs!.includes(c.slug))
      : seedCollections

    const results: SeedResult[] = []
    for (const col of collections) {
      const r = await seedOne(payload, col)
      results.push(r)
    }

    return NextResponse.json({ success: true, results })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}
