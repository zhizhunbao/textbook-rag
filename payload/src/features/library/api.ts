/**
 * Library API — Payload Books collection helpers
 *
 * Wraps Payload REST API (/api/books) for the Library feature.
 * Separate from shared/api.ts which is for the Chat feature.
 */

import type { LibraryBook, BookCategory, BookStatus } from './types'

const PAYLOAD_BASE = '' // same-origin, proxied by Next.js

interface PayloadListResponse {
  docs: any[]
  totalDocs: number
  totalPages: number
  page: number
}

/** Fetch all books with optional filters */
export async function fetchLibraryBooks(opts?: {
  category?: BookCategory
  status?: BookStatus
  search?: string
  limit?: number
  page?: number
}): Promise<{ books: LibraryBook[]; total: number }> {
  const params = new URLSearchParams()
  params.set('limit', String(opts?.limit ?? 200))
  params.set('sort', '-updatedAt')

  if (opts?.page) params.set('page', String(opts.page))
  if (opts?.category) params.set('where[category][equals]', opts.category)
  if (opts?.status) params.set('where[status][equals]', opts.status)
  if (opts?.search) params.set('where[title][contains]', opts.search)

  const res = await fetch(`${PAYLOAD_BASE}/api/books?${params}`)
  if (!res.ok) throw new Error(`Failed to fetch books: ${res.status}`)

  const data: PayloadListResponse = await res.json()

  return {
    books: data.docs.map(mapPayloadBook),
    total: data.totalDocs,
  }
}

/** Fetch a single book by Payload ID */
export async function fetchLibraryBook(id: number): Promise<LibraryBook> {
  const res = await fetch(`${PAYLOAD_BASE}/api/books/${id}`)
  if (!res.ok) throw new Error(`Failed to fetch book: ${res.status}`)
  const data = await res.json()
  return mapPayloadBook(data)
}

/** Delete a book (admin only) */
export async function deleteBook(id: number): Promise<void> {
  const res = await fetch(`${PAYLOAD_BASE}/api/books/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to delete book: ${res.status}`)
}

/** Map Payload response to our typed interface */
function mapPayloadBook(raw: any): LibraryBook {
  const p = raw.pipeline ?? {}

  return {
    id: raw.id,
    engineBookId: raw.engineBookId ?? '',
    title: raw.title ?? '(untitled)',
    authors: raw.authors ?? null,
    isbn: raw.isbn ?? null,
    category: raw.category ?? 'textbook',
    subcategory: raw.subcategory ?? null,
    status: raw.status ?? 'pending',
    chunkCount: raw.chunkCount ?? null,
    metadata: raw.metadata ?? null,
    pipeline: {
      chunked: p.chunked ?? 'pending',
      stored: p.stored ?? 'pending',
      vector: p.vector ?? 'pending',
      fts: p.fts ?? 'pending',
      toc: p.toc ?? 'pending',
    },
    createdAt: raw.createdAt ?? '',
    updatedAt: raw.updatedAt ?? '',
  }
}
