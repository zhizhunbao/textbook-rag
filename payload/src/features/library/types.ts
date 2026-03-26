/**
 * Library feature types
 *
 * Extends the shared BookSummary with additional library-specific fields
 * from the Payload Books collection.
 */

/** Book overall status from Payload collection */
export type BookStatus = 'pending' | 'processing' | 'indexed' | 'error'

/** Book category from Payload collection */
export type BookCategory = 'textbook' | 'ecdev' | 'real_estate'

/** 每个处理阶段的状态 */
export type StageStatus = 'pending' | 'done' | 'error'

/**
 * Pipeline 各阶段 — 对应 engine/ingest/pipeline.py
 *
 *   chunked — MinerU → chunks[]
 *   stored  — chunks → Payload PG
 *   vector  — chunks → ChromaDB
 *   fts     — chunks → SQLite FTS5
 *   toc     — TOC 提取
 */
export interface PipelineStages {
  chunked: StageStatus
  stored: StageStatus
  vector: StageStatus
  fts: StageStatus
  toc: StageStatus
}

/** Pipeline 阶段 key 列表 (用于遍历) */
export const PIPELINE_STAGE_KEYS = ['chunked', 'stored', 'vector', 'fts', 'toc'] as const
export type PipelineStageKey = (typeof PIPELINE_STAGE_KEYS)[number]

/** 阶段显示配置 */
export interface PipelineStageConfig {
  key: PipelineStageKey
  label: string
  labelZh: string
}

export const PIPELINE_STAGE_CONFIGS: PipelineStageConfig[] = [
  { key: 'chunked', label: 'Chunked', labelZh: '分块' },
  { key: 'stored',  label: 'Stored',  labelZh: '存储' },
  { key: 'vector',  label: 'Vector',  labelZh: '向量' },
  { key: 'fts',     label: 'FTS',     labelZh: 'FTS' },
  { key: 'toc',     label: 'TOC',     labelZh: 'TOC' },
]

/** Full book record as returned by Payload REST API */
export interface LibraryBook {
  id: number
  engineBookId: string
  title: string
  authors: string | null
  isbn: string | null
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

/** Category filter option for the UI */
export interface CategoryOption {
  value: BookCategory | 'all'
  label: string
  labelZh: string
}

export const CATEGORY_OPTIONS: CategoryOption[] = [
  { value: 'all', label: 'All', labelZh: '全部' },
  { value: 'textbook', label: 'Textbook', labelZh: '教材' },
  { value: 'ecdev', label: 'EC Dev', labelZh: '经济发展' },
  { value: 'real_estate', label: 'Real Estate', labelZh: '房地产' },
]
