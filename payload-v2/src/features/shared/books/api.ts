/**
 * shared/books API — unified book fetching from Payload CMS.
 *
 * Single entry point for /api/books queries.
 * Replaces: query_engine/api.ts::fetchBooks, question_gen/api.ts::fetchIndexedBooks
 */

import type { BookBase, BookCategory, BookStatus, PipelineInfo } from './types'

// ============================================================
// Fetch options
// ============================================================

export interface FetchBooksOptions {
  /** Filter by overall book status. */
  status?: BookStatus
  /** Filter by category. */
  category?: BookCategory
  /** Filter by title (partial match). */
  search?: string
  /** Max results. Default 200. */
  limit?: number
  /** Sort field. Default '-updatedAt'. */
  sort?: string
}

// ============================================================
// API
// ============================================================

/** Fetch books from Payload CMS with optional filters. */
export async function fetchBooks(opts?: FetchBooksOptions): Promise<BookBase[]> {
  const params = new URLSearchParams()
  params.set('limit', String(opts?.limit ?? 200))
  params.set('sort', opts?.sort ?? '-updatedAt')

  if (opts?.status) params.set('where[status][equals]', opts.status)
  if (opts?.category) params.set('where[category][equals]', opts.category)
  if (opts?.search) params.set('where[title][contains]', opts.search)

  const res = await fetch(`/api/books?${params}`)
  if (!res.ok) throw new Error(`Failed to fetch books: ${res.status}`)

  const data: { docs: Array<Record<string, any>> } = await res.json()
  return data.docs.map(mapPayloadBook)
}

/** Fetch indexed books only (convenience wrapper). */
export async function fetchIndexedBooks(): Promise<BookBase[]> {
  return fetchBooks({ status: 'indexed' })
}

// ============================================================
// Internal mapper
// ============================================================

function mapPipeline(p: Record<string, any> | undefined, bookStatus: string): PipelineInfo | undefined {
  // If pipeline group has explicit values, use them
  if (p && (p.parse !== 'pending' || p.ingest !== 'pending')) {
    return {
      parse: p.parse ?? 'pending',
      ingest: p.ingest ?? 'pending',
    }
  }
  // Infer from book status for legacy books without pipeline data
  if (bookStatus === 'indexed') {
    return { parse: 'done', ingest: 'done' }
  }
  if (bookStatus === 'processing') {
    return { parse: 'pending', ingest: 'pending' }
  }
  if (bookStatus === 'error') {
    return { parse: 'error', ingest: 'error' }
  }
  // Default: pending
  return p ? { parse: p.parse ?? 'pending', ingest: p.ingest ?? 'pending' } : undefined
}

function mapPayloadBook(b: Record<string, any>): BookBase {
  const status = b.status ?? 'pending'
  return {
    id: b.id,
    book_id: b.engineBookId ?? String(b.id),
    title: b.title ?? '(untitled)',
    authors: b.authors ?? '',
    chunk_count: b.chunkCount ?? 0,
    category: b.category ?? 'textbook',
    subcategory: b.subcategory ?? '',
    status,
    pageCount: b.metadata?.pageCount ?? 0,
    fileSize: b.metadata?.fileSize ?? 0,
    createdAt: b.createdAt ?? '',
    pipeline: mapPipeline(b.pipeline, status),
  }
}
