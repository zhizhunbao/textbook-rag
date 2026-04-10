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
// Common values: 'textbook', 'ecdev', 'real_estate', 'research_paper', etc.
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
export type ImportTab = 'sources' | 'import' | 'files' | 'pipeline'

// ============================================================
// Parse preview types (AQ-03)
// ============================================================
export interface ParseStats {
  bookId: string
  bookTitle: string
  totalItems: number
  totalPages: number
  typeCounts: Record<string, number>
  samples: ParseSample[]
}

export interface ParseSample {
  text: string
  pageIdx: number
  contentType: string
  bbox?: number[]
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
