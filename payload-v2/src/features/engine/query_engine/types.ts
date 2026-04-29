/**
 * query_engine types — Query requests, responses, and full trace data.
 *
 * Shared type definitions for the query_engine module.
 */

import type { SourceInfo, RetrievalStats, RetrievalTrace } from '../retrievers/types'
import type { GenerationTrace } from '../response_synthesizers/types'

// ============================================================
// Domain types
// ============================================================

/** Optional filters to scope retrieval by book, chapter, or content type. */
export interface QueryFilters {
  book_ids?: number[]
  book_id_strings?: string[]
  chapter_ids?: number[]
  content_types?: string[]
}

/** Client request payload for a query engine call. */
export type RetrievalMode = 'standard' | 'auto' | 'smart' | 'deep'

export interface QueryRequest {
  question: string
  filters?: QueryFilters
  top_k?: number
  model?: string
  provider?: string
  /** Enable LLMRerank postprocessor (truthy = on). */
  reranker?: string | null
  /** Custom system prompt override — from PromptSelector. */
  custom_system_prompt?: string | null
  /** Retrieval strategy routing mode. Smart/deep currently fall back server-side. */
  retrieval_mode?: RetrievalMode | null
}

/** Complete execution trace including retrieval and generation stages. */
export interface QueryTrace {
  question: string
  top_k: number
  filters: QueryFilters | null
  active_book_title: string | null
  routing?: {
    requested_mode: RetrievalMode
    strategy: 'standard' | 'smart' | 'deep'
    depth?: string | null
    depth_score?: number | null
    reasoning?: string
    is_fallback?: boolean
  } | null
  retrieval: RetrievalTrace
  generation: GenerationTrace
}

/** LLM usage telemetry from the query pipeline. */
export interface LlmTelemetry {
  llm_calls: number
  input_tokens: number
  output_tokens: number
}

/** Response returned from a query engine call. */
export interface QueryResponse {
  answer: string
  sources: SourceInfo[]
  retrieval_stats: RetrievalStats
  trace: QueryTrace
  /** LLM token usage telemetry (populated from SSE stream). */
  telemetry?: LlmTelemetry
}

/** Lightweight book metadata used in query context selection. */
export interface BookSummary {
  id: number
  book_id: string
  title: string
  authors: string
  page_count: number
  chapter_count: number
  chunk_count: number
  category: string
  subcategory: string
}

/** Single chapter within a book. */
export interface ChapterInfo {
  id: number
  chapter_key: string
  title: string
  start_page: number | null
}

/** Extended book info with chapter list. */
export interface BookDetail extends BookSummary {
  chapters: ChapterInfo[]
}

// ============================================================
// API types
// ============================================================

/** Table-of-contents entry from PDF structural extraction. */
export interface TocEntry {
  id: number
  level: number
  number: string
  title: string
  pdf_page: number
}
