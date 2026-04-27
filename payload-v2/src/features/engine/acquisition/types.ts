/**
 * engine/acquisition/types.ts — Import module type definitions.
 *
 * Aligned with: engine_v2/api/routes/ingest.py → collections/Books
 *
 * Note: BookCategory redefined locally because engine/<A> → engine/<B>
 * import is forbidden (see project-structure.md dependency rules).
 */

// ============================================================
// Book category (dynamic — LLM-suggested, user-editable)
// Common values: 'textbooks', 'ecdev', 'real_estate', 'research_paper', etc.
// ============================================================
export type BookCategory = string

// ============================================================
// File upload types
// ============================================================
export interface FileUploadPayload {
  file: File
  title?: string
  category?: BookCategory
  subcategory?: string
}

export interface FileUploadState {
  uploading: boolean
  progress: number // 0-100
  error: string | null
  fileName: string | null
  stage: string | null
}

// ============================================================
// URL import types
// ============================================================
export interface UrlImportState {
  importing: boolean
  progress: number // 0-100
  error: string | null
  url: string | null
  stage: string | null
}

// ============================================================
// Import Tab type
// ============================================================
export type ImportTab = 'sources' | 'import' | 'files' | 'pipeline' | 'vectors' | 'toc' | 'chunks'

// ============================================================
// Parse preview types (AQ-03 + AQ-07)
// ============================================================

/** Content types supported by MinerU parser sub-tabs (AQ-07). */
export type ContentFilterType = 'text' | 'image' | 'table' | 'equation' | 'discarded'

export interface ParseStats {
  bookId: string
  bookTitle: string
  totalItems: number
  totalPages: number
  typeCounts: Record<string, number>
  /** Count after content_type filter (AQ-07). */
  filteredCount?: number
  samples: ParseSample[]
  /** Pagination offset (AQ-07). */
  offset?: number
  /** Pagination limit (AQ-07). */
  limit?: number
}

export interface ParseSample {
  text: string
  pageIdx: number
  contentType: string
  bbox?: number[]
  /** Image file path relative to auto/ (AQ-07, image items only). */
  imgPath?: string
}

// ============================================================
// Classification types (AQ-05)
// ============================================================
export interface ClassifyResult {
  category: BookCategory
  subcategory: string
  confidence: number
}

// ============================================================
// Media file types (AQ-04)
// ============================================================
export interface MediaFile {
  id: number
  filename: string
  mimeType: string
  filesize: number
  url: string
  createdAt: string
  relatedBookId?: number
  relatedBookTitle?: string
}

// ============================================================
// Vector stats types (AQ-09)
// ============================================================
export interface VectorSample {
  chunkId: string
  text: string
  metadata: {
    book_id: string
    content_type: string
    page_idx: number
  }
  vectorPreview?: number[]
  dimensions?: number
}

export interface VectorStats {
  totalVectors: number
  bookVectors: number
  dimensions: number
  collectionName: string
  samples: VectorSample[]
}

