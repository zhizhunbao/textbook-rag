/**
 * data-sources-persona/types.ts — Shared type for persona-linked data source seeds.
 *
 * Refactored: bilingual name (nameEn + nameZh), description, only essential fields.
 * Removed: shortName, category (always 'research'), icon, schedule (→ syncInterval).
 */

export interface PersonaDataSource {
  /** English name — displayed as primary identifier */
  nameEn: string
  /** Chinese name — 中文名称 */
  nameZh: string
  /** Brief description of what this source covers */
  description: string
  /** URL to crawl / scrape */
  discoveryUrl: string
  /** Source type: web_scrape | pdf_crawl | api | manual */
  type: string
  /** Whether this source is enabled for crawling */
  enabled: boolean
  /** Enable automatic scheduled sync */
  autoSync: boolean
  /** Sync frequency: daily | weekly | monthly */
  syncInterval: string
  /** Used during seed to resolve persona relationship by slug (not persisted) */
  _personaSlug: string
}
