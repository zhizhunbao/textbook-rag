/**
 * engine/retrievers/types.ts
 * Aligned with: llama_index.retrievers → engine-v2/retrievers/hybrid.py
 *
 * Retrieval trace types surfaced in the query UI.
 * The HybridRetriever (BM25 + Vector + RRF) is engine-internal;
 * these types represent the trace output visible to the frontend.
 */

// ── Source bounding box (for PDF highlight) ─────────────────────────────────
export interface BboxEntry {
  x0: number
  y0: number
  x1: number
  y1: number
  page_width: number
  page_height: number
  page_number: number
}

// ── Source info returned per retrieved chunk ─────────────────────────────────
export interface SourceInfo {
  source_id: string
  book_id: number
  book_id_string?: string
  citation_index?: number
  book_title: string
  chapter_title: string | null
  page_number: number
  /** Complete chunk text (≤2000 chars) for hover preview */
  full_content?: string
  snippet: string
  bbox: { x0: number; y0: number; x1: number; y1: number } | null
  bboxes?: BboxEntry[]
  page_dim: { width: number; height: number } | null
  confidence: number
  citation_label?: string
  /** Retrieval relevance score (0.0–1.0, higher = more relevant) */
  score?: number
  /** Retrieval strategy that found this source (EV2-T1-03). */
  retrieval_source?: 'bm25' | 'vector' | 'both'
}

// ── Per-strategy trace hit ──────────────────────────────────────────────────
export interface TraceChunkHit {
  strategy: 'fts' | 'vector' | 'toc' | 'fused'
  rank: number
  chunk_id: string
  book_title: string
  chapter_title: string | null
  page_number: number | null
  score: number | null
  snippet: string
}

// ── Retrieval statistics ────────────────────────────────────────────────────
export interface RetrievalStats {
  fts_hits: number
  vector_hits: number
  toc_hits: number
  fused_count: number
}

// ── Full retrieval trace ────────────────────────────────────────────────────
export interface RetrievalTrace {
  fetch_k: number
  fts_query: string
  fts_results: TraceChunkHit[]
  vector_results: TraceChunkHit[]
  toc_results: TraceChunkHit[]
  fused_results: TraceChunkHit[]
}
