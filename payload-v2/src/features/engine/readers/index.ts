/**
 * engine/readers — Document source management
 * Aligned with: llama_index.readers → engine-v2/readers/ (MinerUReader)
 *
 * Manages book/document CRUD via Payload CMS Books collection.
 * LibraryPage removed — merged into acquisition/MediaTab.
 */

// ── Data layer ──────────────────────────────────────────────────────────────
export * from './types'
export * from './api'
export { useLibraryBooks } from './useLibraryBooks'

// ── UI components ───────────────────────────────────────────────────────────
export { default as BookCard } from './components/BookCard'
export { default as StatusBadge, StageDot, PipelineProgress } from './components/StatusBadge'
export { default as BookPicker } from './components/BookPicker'
export { default as BookSelector } from './components/BookSelector'
export { default as BookEditDialog } from './components/BookEditDialog'

