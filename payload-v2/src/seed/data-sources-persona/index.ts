/**
 * data-sources-persona/index.ts — Single unified table of all persona data sources.
 *
 * One big flat array with filter helpers by persona slug, category, or sync interval.
 * Total: ~56 data sources across 28 personas (ecdev-analyst uses existing sources).
 *
 * ── Filter examples ──
 *   byPersona('imm-pathways')     → 3 sources
 *   byCategory('education')       → all edu-* sources
 *   bySyncInterval('weekly')      → all weekly-synced sources
 */

import type { PersonaDataSource } from './types'
import { educationSources } from './education'
import { immigrationSources } from './immigration'
import { settlementSources } from './settlement'
import { healthcareSources } from './healthcare'
import { financeSources } from './finance'
import { careerSources } from './career'
import { legalSources } from './legal'

// ── Big unified table ───────────────────────────────────────
export const allPersonaDataSources: PersonaDataSource[] = [
  ...educationSources,
  ...immigrationSources,
  ...settlementSources,
  ...healthcareSources,
  ...financeSources,
  ...careerSources,
  ...legalSources,
]

// ── Slug → category mapping (for filter convenience) ────────
const slugCategoryMap: Record<string, string> = {
  'edu-school-planning': 'education',
  'edu-visa-compliance': 'education',
  'edu-academic-rules': 'education',
  'edu-work-permit': 'education',
  'edu-child-education': 'education',
  'imm-pathways': 'immigration',
  'imm-pr-renewal': 'immigration',
  'imm-family': 'immigration',
  'life-rental': 'settlement',
  'life-driving': 'settlement',
  'life-utilities': 'settlement',
  'life-home-buying': 'settlement',
  'life-car': 'settlement',
  'health-insurance': 'healthcare',
  'health-mental': 'healthcare',
  'health-childcare': 'healthcare',
  'fin-banking': 'finance',
  'fin-tax': 'finance',
  'fin-investment': 'finance',
  'fin-cost-saving': 'finance',
  'career-resume': 'career',
  'career-internship': 'career',
  'career-transition': 'career',
  'career-volunteer': 'career',
  'legal-labor': 'legal',
  'legal-disputes': 'legal',
  'legal-consumer': 'legal',
  'legal-basics': 'legal',
}

// ── Filter helpers ──────────────────────────────────────────

/** Filter by exact persona slug */
export function byPersona(slug: string): PersonaDataSource[] {
  return allPersonaDataSources.filter((s) => s._personaSlug === slug)
}

/** Filter by category (education / immigration / settlement / etc.) */
export function byCategory(category: string): PersonaDataSource[] {
  return allPersonaDataSources.filter(
    (s) => slugCategoryMap[s._personaSlug] === category,
  )
}

/** Filter by sync interval (daily / weekly / monthly) */
export function bySyncInterval(interval: string): PersonaDataSource[] {
  return allPersonaDataSources.filter((s) => s.syncInterval === interval)
}

/** Filter by enabled status */
export function byEnabled(enabled: boolean): PersonaDataSource[] {
  return allPersonaDataSources.filter((s) => s.enabled === enabled)
}

// ── Seed function ───────────────────────────────────────────

/**
 * Custom seed function for persona data sources.
 * Strategy: DELETE ALL persona-linked data-sources → RECREATE.
 *
 * 1. Delete all existing data-sources that have a persona association
 * 2. Look up all consulting-personas to build slug → id map
 * 3. Create each data source with resolved persona ID
 */
export async function seedPersonaDataSources(
  payload: any,
): Promise<{ deleted: number; created: number; errors: string[] }> {
  const result = { deleted: 0, created: 0, errors: [] as string[] }

  // Step 1: Delete ALL existing data sources (clean slate)
  try {
    const existing = await payload.find({
      collection: 'data-sources',
      limit: 500,
      overrideAccess: true,
    })
    for (const doc of existing.docs) {
      await payload.delete({
        collection: 'data-sources',
        id: doc.id,
        overrideAccess: true,
      })
      result.deleted++
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    result.errors.push(`delete-all: ${msg}`)
  }

  // Step 2: Build slug → id map
  const personas = await payload.find({
    collection: 'consulting-personas',
    limit: 100,
    overrideAccess: true,
  })
  const slugToId: Record<string, number> = {}
  for (const p of personas.docs) {
    slugToId[p.slug] = p.id
  }

  // Step 3: Create each data source with resolved persona ID
  for (const src of allPersonaDataSources) {
    try {
      const personaId = slugToId[src._personaSlug]
      if (!personaId) {
        result.errors.push(`${src.nameEn}: persona '${src._personaSlug}' not found`)
        continue
      }

      const { _personaSlug, ...fields } = src
      const data = { ...fields, persona: personaId }

      await payload.create({
        collection: 'data-sources',
        data,
        overrideAccess: true,
      })
      result.created++
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      result.errors.push(`${src.nameEn}: ${msg}`)
    }
  }

  return result
}

