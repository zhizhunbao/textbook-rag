/* ── API response types ── */

import type { BookBase } from './books'

export interface BookSummary extends BookBase {
  page_count: number;
  chapter_count: number;
}

export interface ChapterInfo {
  id: number;
  chapter_key: string;
  title: string;
  start_page: number | null;
}

export interface BookDetail extends BookSummary {
  chapters: ChapterInfo[];
}

export interface TocEntry {
  id: number;
  level: number;
  number: string;
  title: string;
  pdf_page: number;
}

export interface BboxEntry {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  page_width: number;
  page_height: number;
  page_number: number;
}

export interface SourceInfo {
  source_id: string;
  book_id: number;
  book_id_string?: string;
  citation_index?: number;
  book_title: string;
  chapter_title: string | null;
  page_number: number;
  /** Complete chunk text (≤2000 chars) for hover preview + paragraph-level highlight */
  full_content?: string;
  snippet: string;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  bboxes?: BboxEntry[];
  page_dim: { width: number; height: number } | null;
  confidence: number;
  citation_label?: string;
  /** Retrieval relevance score (0.0–1.0, higher = more relevant) */
  score?: number;
  /** Retrieval strategy that found this source (EV2-T1-03). */
  retrieval_source?: 'bm25' | 'vector' | 'both';
  /** Consulting source class (C4): persona KB or user private document. */
  source_type?: 'persona' | 'user_doc';
}

export interface RetrievalStats {
  fts_hits: number;
  vector_hits: number;
  both_hits?: number;
  toc_hits: number;
  fused_count?: number;
  retrieval_mode?: 'hybrid' | 'vector_only';
}

export interface TraceChunkHit {
  strategy: "fts" | "vector" | "toc" | "fused";
  rank: number;
  chunk_id: string;
  book_title: string;
  chapter_title: string | null;
  page_number: number | null;
  score: number | null;
  snippet: string;
}

export interface RetrievalTrace {
  fetch_k: number;
  fts_query: string;
  fts_results: TraceChunkHit[];
  vector_results: TraceChunkHit[];
  toc_results: TraceChunkHit[];
  fused_results: TraceChunkHit[];
}

export interface GenerationTrace {
  model: string;
  system_prompt: string;
  user_prompt: string;
}

export interface QueryTrace {
  question: string;
  top_k: number;
  filters: QueryFilters | null;
  active_book_title: string | null;
  retrieval: RetrievalTrace;
  generation: GenerationTrace;
}

export interface QueryResponse {
  answer: string;
  sources: SourceInfo[];
  retrieval_stats: RetrievalStats;
  trace: QueryTrace;
}

export interface QueryFilters {
  book_ids?: number[];
  book_id_strings?: string[];
  chapter_ids?: number[];
  content_types?: string[];
}

export interface QueryRequest {
  question: string;
  filters?: QueryFilters;
  top_k?: number;
  model?: string;
  provider?: string;
}

export interface ModelInfo {
  name: string;
  is_default: boolean;
  provider?: string;
}
