/**
 * shared/books types — unified book type definitions.
 *
 * Single source of truth for book-related types across all modules.
 */

// ============================================================
// Category & status
// ============================================================

// Dynamic — LLM-suggested, user-editable. Common: 'textbooks', 'ecdev', 'real_estate'
export type BookCategory = string
export type BookStatus = 'pending' | 'processing' | 'indexed' | 'error'
export type PipelineStage = 'pending' | 'done' | 'error'

/** Per-stage pipeline status for the 2-stage ingestion flow. */
export interface PipelineInfo {
  parse: PipelineStage
  ingest: PipelineStage
}

// ============================================================
// Base book type (minimum common fields)
// ============================================================

/** Core book identity — shared by all modules. */
export interface BookBase {
  id: number
  book_id: string
  title: string
  authors: string
  category: string
  subcategory: string
  chunk_count: number
  status: BookStatus
  pageCount: number
  fileSize: number
  createdAt: string
  /** 2-stage pipeline status (only populated when pipeline group exists). */
  pipeline?: PipelineInfo
}

// ============================================================
// Category config (shared across sidebar consumers)
// ============================================================

export interface CategoryConfig {
  label: string
  labelFr: string
  icon: string
  color: string
}

/** Well-known category display config. */
export const CATEGORY_CONFIGS: Record<string, CategoryConfig> = {
  textbooks:   { label: 'Textbooks',      labelFr: 'Manuels',                  icon: 'BookOpen',  color: 'text-blue-400' },
  ecdev:       { label: 'EC Development', labelFr: 'Développement économique', icon: 'Building2', color: 'text-emerald-400' },
  real_estate: { label: 'Real Estate',    labelFr: 'Immobilier',               icon: 'Home',      color: 'text-amber-400' },
}

/** Get category config, with fallback for LLM-suggested dynamic categories. */
export function getCategoryConfig(category: string): CategoryConfig {
  if (CATEGORY_CONFIGS[category]) return CATEGORY_CONFIGS[category]

  // Auto-generate config for unknown categories
  const label = category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  return {
    label,
    labelFr: label,
    icon: 'FolderOpen',
    color: 'text-violet-400',
  }
}
