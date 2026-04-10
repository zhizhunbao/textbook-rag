/**
 * seed/index.ts — Seed registry barrel export.
 *
 * Aggregates per-collection seed data and exposes a unified
 * `seedCollections` array consumed by the POST /api/seed route.
 *
 * Each module maps 1:1 to a Payload collection:
 *   - llms         → Llms collection
 *   - prompt-modes → Prompts collection (type='mode')
 *   - prompt-templates → Prompts collection (type='template')
 *   - users        → Users collection
 *   - data-sources → DataSources collection
 */

export type { SeedCollection } from './types'

export { llmsData } from './llms'
export { promptModesData } from './prompt-modes'
export { promptTemplatesData } from './prompt-templates'
export { usersData } from './users'
export { dataSourcesData } from './data-sources'

// ── Registry ────────────────────────────────────────────────────────────────

import type { SeedCollection } from './types'
import { llmsData } from './llms'
import { promptModesData } from './prompt-modes'
import { promptTemplatesData } from './prompt-templates'
import { usersData } from './users'
import { dataSourcesData } from './data-sources'

export const seedCollections: SeedCollection[] = [
  { label: 'Users', slug: 'users', uniqueField: 'email', data: usersData },
  { label: 'LLMs', slug: 'llms', uniqueField: 'name', data: llmsData },
  { label: 'Prompt Modes', slug: 'prompts', uniqueField: 'slug', data: promptModesData },
  { label: 'Query Templates', slug: 'prompts', uniqueField: 'slug', data: promptTemplatesData },
  { label: 'Data Sources', slug: 'data-sources', uniqueField: 'shortName', data: dataSourcesData },
]
