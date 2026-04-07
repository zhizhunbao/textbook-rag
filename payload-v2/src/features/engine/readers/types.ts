/**
 * engine/readers/types.ts
 * Aligned with: llama_index.readers → engine-v2/readers/ → collections/Books
 *
 * Type definitions for book/document sources managed by Payload CMS.
 */

// ── Book overall status from Payload collection ─────────────────────────────
export type BookStatus = 'pending' | 'processing' | 'indexed' | 'error'

// ── Book category (dynamic — LLM-suggested, user-editable) ─────────────────
// Common values: 'textbook', 'ecdev', 'real_estate', 'research_paper', etc.
export type BookCategory = string

// ── Pipeline stage status (per-stage) ───────────────────────────────────────
export type StageStatus = 'pending' | 'done' | 'error'

/**
 * Pipeline stages — maps to engine-v2/ingestion/pipeline.py (v2, LlamaIndex-native)
 *
 *   parse  — MinerU PDF parsing → content_list.json
 *   ingest — MinerUReader → IngestionPipeline → ChromaDB (chunking + embedding + upsert)
 */
export interface PipelineStages {
  parse: StageStatus
  ingest: StageStatus
}

// ── Stage keys and display config ───────────────────────────────────────────
export const PIPELINE_STAGE_KEYS = ['parse', 'ingest'] as const
export type PipelineStageKey = (typeof PIPELINE_STAGE_KEYS)[number]

export interface PipelineStageConfig {
  key: PipelineStageKey
  label: string
  labelZh: string
}

export const PIPELINE_STAGE_CONFIGS: PipelineStageConfig[] = [
  { key: 'parse',  label: 'Parse',  labelZh: '解析' },
  { key: 'ingest', label: 'Ingest', labelZh: '入库' },
]

// ── Cover image from Payload Media upload ───────────────────────────────────
export interface CoverImage {
  id: number
  url: string
  alt?: string
  sizes?: {
    thumbnail?: { url: string; width: number; height: number }
    card?: { url: string; width: number; height: number }
  }
}

// ── Full book record from Payload REST API ──────────────────────────────────
export interface LibraryBook {
  id: number
  engineBookId: string
  title: string
  authors: string | null
  isbn: string | null
  coverImage: CoverImage | null
  category: BookCategory
  subcategory: string | null
  status: BookStatus
  chunkCount: number | null
  metadata: {
    pageCount?: number
    chapterCount?: number
    source?: string
  } | null
  pipeline: PipelineStages
  createdAt: string
  updatedAt: string
}

// ── Category filter option (UI) ─────────────────────────────────────────────
export interface CategoryOption {
  value: string
  label: string
  labelZh: string
}

/** Well-known categories (UI display). Dynamic categories added at runtime. */
export const WELL_KNOWN_CATEGORIES: CategoryOption[] = [
  { value: 'textbook', label: 'Textbook', labelZh: '教材' },
  { value: 'ecdev', label: 'EC Dev', labelZh: '经济发展' },
  { value: 'real_estate', label: 'Real Estate', labelZh: '房地产' },
]
