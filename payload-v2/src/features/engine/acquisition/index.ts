/**
 * engine/acquisition — Data import module (PDF upload + URL import).
 *
 * Aligned with: engine_v2/api/routes/ingest.py → collections/Books
 *
 * Manages PDF acquisition via file upload or URL import.
 * Separated from readers/ to enforce single responsibility:
 *   - acquisition/ = getting data IN (upload, download, parse, classify)
 *   - readers/     = browsing data (book catalog, TOC, content)
 *   - ingestion/   = processing data (pipeline, vectors, tasks)
 */

// ── Data layer ──────────────────────────────────────────────────────────────
export * from './types'
export { classifyBook, fetchParseStats, fetchPdfMedia, deleteBookWithCleanup, deleteMediaFile } from './api'
export { useFileUpload } from './useFileUpload'
export { useUrlImport } from './useUrlImport'

// ── UI components ───────────────────────────────────────────────────────────
export { default as ImportPage } from './components/ImportPage'
export { default as FileUploadCard } from './components/FileUploadCard'
export { default as UrlImportCard } from './components/UrlImportCard'
export { default as ClassifyDialog } from './components/ClassifyDialog'
export { default as ParsePreviewTab } from './components/ParsePreviewTab'
export { default as MediaTab } from './components/MediaTab'
export { default as SourcesTab } from './components/SourcesTab'
