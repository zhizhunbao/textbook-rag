/**
 * engine/acquisition/api.ts — Import module API calls.
 *
 * Endpoints:
 *   POST   /engine/classify                 — LLM auto-classification (AQ-05)
 *   GET    /engine/books/{id}/parse-stats   — MinerU parse statistics (AQ-03)
 *   DELETE /engine/books/{id}               — Engine cleanup (AQ-06)
 *   GET    /api/media                       — Payload Media collection (AQ-04)
 *   DELETE /api/media/{id}                  — Payload Media delete (AQ-06)
 *   DELETE /api/books/{id}                  — Payload Book delete (AQ-06)
 */

import type { ClassifyResult, ParseStats, MediaFile } from './types'
import { authFetch } from '@/features/shared/authFetch'

// ============================================================
// Constants
// ============================================================
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Classification (Engine API) — AQ-05
// ============================================================

/**
 * Classify a book by title/filename using LLM.
 * Returns suggested category, subcategory, and confidence score.
 */
export async function classifyBook(
  title: string,
  filename?: string,
): Promise<ClassifyResult> {
  const res = await fetch(`${ENGINE_URL}/engine/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, filename }),
  })
  if (!res.ok) {
    throw new Error(`Classification failed: ${res.status}`)
  }
  return res.json()
}

// ============================================================
// Parse stats (Engine API)
// ============================================================

/**
 * Fetch MinerU parse statistics for a specific book.
 * Returns item counts, page counts, type distribution, and content samples.
 */
export async function fetchParseStats(bookId: string): Promise<ParseStats> {
  const res = await fetch(`${ENGINE_URL}/engine/books/${bookId}/parse-stats`)
  if (!res.ok) {
    throw new Error(`Failed to fetch parse stats: ${res.status}`)
  }
  return res.json()
}

// ============================================================
// Media files (Payload REST API)
// ============================================================

/**
 * Fetch PDF media files from Payload Media collection.
 * Filters by mimeType=application/pdf.
 */
export async function fetchPdfMedia(): Promise<MediaFile[]> {
  const res = await authFetch(
    '/api/media?where[mimeType][equals]=application/pdf&limit=100&sort=-createdAt',
  )
  if (!res.ok) {
    throw new Error(`Failed to fetch media: ${res.status}`)
  }
  const data = await res.json()
  const docs = data.docs ?? []

  return docs.map((doc: Record<string, unknown>) => ({
    id: doc.id as number,
    filename: (doc.filename as string) ?? 'unknown',
    mimeType: (doc.mimeType as string) ?? '',
    filesize: (doc.filesize as number) ?? 0,
    url: (doc.url as string) ?? '',
    createdAt: (doc.createdAt as string) ?? '',
    relatedBookId: undefined, // populated by cross-referencing Books.pdfMedia
    relatedBookTitle: undefined,
  }))
}

// ============================================================
// Delete — Book + engine cleanup (AQ-06)
// ============================================================

/**
 * Delete a book with full engine cleanup (ChromaDB + MinerU + raw PDF).
 * Steps: engine cleanup (best-effort) → Payload CMS delete.
 */
export async function deleteBookWithCleanup(
  payloadBookId: number,
  engineBookId?: string,
): Promise<void> {
  // Step 1: Engine-side cleanup (best-effort)
  // engineBookId is a filename stem (e.g. "economic_update_q1_2022_en")
  // Skip if it looks like a URL (legacy records before the fix)
  if (engineBookId && !engineBookId.startsWith('http')) {
    try {
      await fetch(`${ENGINE_URL}/engine/books/${encodeURIComponent(engineBookId)}`, {
        method: 'DELETE',
      })
    } catch {
      console.warn(`Engine cleanup failed for ${engineBookId}`)
    }
  }

  // Step 2: Delete Payload CMS record
  const res = await authFetch(`/api/books/${payloadBookId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to delete book: ${res.status}`)
}

// ============================================================
// Delete — Media file (AQ-06)
// ============================================================

/**
 * Delete an uploaded media file from Payload CMS (media collection).
 */
export async function deleteMediaFile(mediaId: number): Promise<void> {
  const res = await authFetch(`/api/media/${mediaId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to delete media: ${res.status}`)
}

/**
 * Delete an uploaded PDF file from Payload CMS (pdf-uploads collection).
 */
export async function deletePdfUpload(uploadId: number): Promise<void> {
  const res = await authFetch(`/api/pdf-uploads/${uploadId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to delete PDF upload: ${res.status}`)
}

