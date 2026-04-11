/**
 * engine/retrievers — Retrieval configuration, types, and UI components
 * Aligned with: llama_index.retrievers → engine-v2/retrievers/ (HybridRetriever)
 *
 * The retriever is an internal engine component (BM25 + Vector + RRF fusion).
 * This module exposes the retrieval trace/config types used by the query UI,
 * plus PDF viewer components for visualizing retrieval results.
 */

// ── Data layer ──────────────────────────────────────────────────────────────
export * from './types'

// ── UI components ───────────────────────────────────────────────────────────
export { default as PdfViewer } from './components/PdfViewer'
export { default as BboxOverlay } from './components/BboxOverlay'
export { default as RetrieverTestPage } from './components/RetrieverTestPage'

