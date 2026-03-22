/**
 * API client for Textbook RAG v2.0
 *
 * v2.0 路径变更:
 *   Books:  GET /api/v1/books     → GET /api/books   (Payload auto REST)
 *   Query:  POST /api/v1/query    → POST /engine/query (Engine FastAPI, proxied)
 *   PDF:    GET /api/v1/books/:id/pdf → GET /api/books/:id/pdf (Payload media)
 *   Models: GET /api/v1/models    → GET /engine/models
 */

import type {
  BookSummary,
  BookDetail,
  ModelInfo,
  QueryRequest,
  QueryResponse,
  TocEntry,
} from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ─── Books (Payload auto REST API) ──────────────────────────────────────────

export async function fetchBooks(): Promise<BookSummary[]> {
  // Payload returns { docs: [], totalDocs, ... }
  const data = await request<{ docs: any[] }>('/api/books?limit=200&where[status][equals]=indexed')
  return data.docs.map((b) => ({
    id: b.id,
    book_id: b.engineBookId ?? String(b.id),
    title: b.title ?? '(untitled)',
    authors: b.authors ?? '',
    page_count: 0,
    chapter_count: 0,
    chunk_count: b.chunkCount ?? 0,
    category: b.category ?? 'textbook',
  }))
}

export async function fetchBook(bookId: number): Promise<BookDetail> {
  const b = await request<any>(`/api/books/${bookId}`)
  return {
    id: b.id,
    book_id: String(b.id),
    title: b.title ?? '(untitled)',
    authors: b.authors ?? '',
    page_count: 0,
    chapter_count: 0,
    chunk_count: b.chunkCount ?? 0,
    chapters: [],
  }
}

export async function fetchToc(bookId: string): Promise<TocEntry[]> {
  // TOC from engine API (uses engine book_id string)
  return request<TocEntry[]>(`${ENGINE}/engine/books/${bookId}/toc`)
}

export function getPdfUrl(bookId: string, variant: 'origin' | 'layout' = 'origin'): string {
  // PDF served by engine FastAPI (uses engine book_id string)
  return `${ENGINE}/engine/books/${bookId}/pdf?variant=${variant}`
}

export async function fetchSuggestions(_bookId: number): Promise<string[]> {
  return []
}

export async function fetchModels(): Promise<ModelInfo[]> {
  try {
    const data = await request<{ models: string[] }>(`${ENGINE}/engine/models`)
    return data.models.map((name, i) => ({ name, is_default: i === 0 }))
  } catch {
    return [{ name: 'llama3.2:3b', is_default: true }]
  }
}

// ─── Query (Engine FastAPI) ──────────────────────────────────────────────────

export async function queryTextbook(req: QueryRequest): Promise<QueryResponse> {
  // Engine returns v2.0 format — we map it to v1.1 QueryResponse shape
  const res = await request<any>(`${ENGINE}/engine/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: req.question,
      top_k: req.top_k ?? 5,
      filters: req.filters ?? {},
      model: req.model,
    }),
  })

  // Normalise Engine v2.0 response → v1.1 QueryResponse
  const sources = (res.sources ?? []).map((s: any) => ({
    source_id: s.chunk_id ?? String(s.page_number),
    book_id: s.book_id ?? 0,
    book_title: s.book_title ?? '',
    chapter_title: s.chapter_title ?? null,
    page_number: s.page_number ?? 1,
    snippet: s.text ?? s.snippet ?? '',
    bbox: s.locators?.[0]
      ? { x0: s.locators[0].x0, y0: s.locators[0].y0, x1: s.locators[0].x1, y1: s.locators[0].y1 }
      : null,
    page_dim: null,
    confidence: s.score ?? 1,
  }))

  return {
    answer: res.answer ?? '',
    sources,
    retrieval_stats: {
      fts_hits: res.stats?.fts_hits ?? 0,
      vector_hits: res.stats?.vector_hits ?? 0,
      pageindex_hits: res.stats?.pageindex_hits ?? 0,
      metadata_hits: res.stats?.metadata_hits ?? 0,
      fused_count: sources.length,
    },
    trace: res.trace ?? {
      question: req.question,
      top_k: req.top_k ?? 5,
      filters: req.filters ?? null,
      active_book_title: null,
      retrieval: {
        fetch_k: req.top_k ?? 5,
        fts_query: req.question,
        fts_results: [],
        vector_results: [],
        pageindex_results: [],
        metadata_results: [],
        fused_results: [],
      },
      generation: { model: req.model ?? '', system_prompt: '', user_prompt: '' },
    },
  }
}

export async function fetchDemo(): Promise<QueryResponse> {
  return queryTextbook({ question: 'What is BM25?', top_k: 3 })
}
