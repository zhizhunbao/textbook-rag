/**
 * engine/readers — Document source management
 * Aligned with: llama_index.readers → engine-v2/readers/ (MinerUReader)
 *
 * Manages book/document CRUD via Payload CMS Books collection.
 * LibraryPage + useLibraryBooks removed — merged into acquisition/ImportPage.
 */

// ── Data layer ──────────────────────────────────────────────────────────────
export * from './types'
export * from './api'

// ── UI components ───────────────────────────────────────────────────────────
export { default as BookCard } from './components/BookCard'
export { default as StatusBadge, StageDot, PipelineProgress } from './components/StatusBadge'
export { default as BookPicker } from './components/BookPicker'
export { default as BookSelector } from './components/BookSelector'
export { default as BookEditDialog } from './components/BookEditDialog'

