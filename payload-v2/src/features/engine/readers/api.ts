/**
 * engine/readers/api.ts
 * Aligned with: llama_index.readers → engine-v2/readers/ → collections/Books
 *
 * Payload CMS REST API wrappers for Books collection.
 */

import type { LibraryBook, BookCategory, BookStatus, CoverImage } from './types'

const PAYLOAD_BASE = '' // same-origin, proxied by Next.js

interface PayloadListResponse {
  docs: any[]
  totalDocs: number
  totalPages: number
  page: number
}

// ── Fetch all books with optional filters ───────────────────────────────────
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

// ── Fetch a single book by Payload ID ───────────────────────────────────────
export async function fetchLibraryBook(id: number): Promise<LibraryBook> {
  const res = await fetch(`${PAYLOAD_BASE}/api/books/${id}`)
  if (!res.ok) throw new Error(`Failed to fetch book: ${res.status}`)
  const data = await res.json()
  return mapPayloadBook(data)
}

// ── Delete a book (Payload CMS + engine cleanup) ────────────────────────────
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

export async function deleteBook(id: number): Promise<void> {
  // Step 1: Fetch book to get engineBookId for engine cleanup
  let engineBookId: string | null = null
  try {
    const book = await fetchLibraryBook(id)
    engineBookId = book.engineBookId || null
  } catch {
    // If fetch fails, still proceed with Payload delete
  }

  // Step 2: Engine-side cleanup (ChromaDB vectors + MinerU output)
  if (engineBookId) {
    try {
      await fetch(`${ENGINE_URL}/engine/books/${engineBookId}`, {
        method: 'DELETE',
      })
    } catch {
      // Best-effort — don't block CMS delete if engine is down
      console.warn(`Engine cleanup failed for ${engineBookId}`)
    }
  }

  // Step 3: Delete Payload CMS record
  const res = await fetch(`${PAYLOAD_BASE}/api/books/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`Failed to delete book: ${res.status}`)
}

// ── Update book metadata (title, authors, category, etc.) ───────────────────
export async function updateBook(
  id: number,
  data: Partial<Pick<LibraryBook, 'title' | 'authors' | 'category' | 'subcategory'>>,
): Promise<LibraryBook> {
  const res = await fetch(`${PAYLOAD_BASE}/api/books/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`Failed to update book: ${res.status}`)
  const body = await res.json()
  return mapPayloadBook(body.doc ?? body)
}

// ── Internal: map cover image from Payload response ─────────────────────────
function mapCoverImage(raw: any): CoverImage | null {
  if (!raw) return null
  // Payload returns either an ID (number) or a populated object
  if (typeof raw === 'number') return null
  return {
    id: raw.id,
    url: raw.url ?? '',
    alt: raw.alt ?? undefined,
    sizes: raw.sizes ?? undefined,
  }
}

// ── Internal: map Payload response → typed interface ────────────────────────
function mapPayloadBook(raw: any): LibraryBook {
  const p = raw.pipeline ?? {}
  const parse = p.parse ?? (raw.status === 'indexed' ? 'done' : 'pending')
  const ingest = p.ingest ?? p.vector ?? p.chunked ?? (raw.status === 'indexed' ? 'done' : 'pending')

  return {
    id: raw.id,
    engineBookId: raw.engineBookId ?? '',
    title: raw.title ?? '(untitled)',
    authors: raw.authors ?? null,
    isbn: raw.isbn ?? null,
    coverImage: mapCoverImage(raw.coverImage),
    category: raw.category ?? 'textbooks',
    subcategory: raw.subcategory ?? null,
    status: raw.status ?? 'pending',
    chunkCount: raw.chunkCount ?? null,
    metadata: raw.metadata ?? null,
    pipeline: {
      parse,
      ingest,
    },
    createdAt: raw.createdAt ?? '',
    updatedAt: raw.updatedAt ?? '',
  }
}
