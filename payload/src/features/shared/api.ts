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
    subcategory: b.subcategory ?? '',
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
    category: b.category ?? 'textbook',
    subcategory: b.subcategory ?? '',
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

/**
 * Transform an engine per-strategy hit into the frontend TraceChunkHit shape.
 */
function mapTraceHit(h: any): { rank: number; chunk_id: string; score: number | null; snippet: string; page_number: number | null; book_title: string } {
  return {
    rank: h.rank ?? 0,
    chunk_id: h.chunk_id ?? '',
    score: h.score ?? null,
    snippet: h.snippet ?? '',
    page_number: h.page_number ?? null,
    book_title: h.book_title ?? '',
  }
}

/**
 * Transform engine v2 trace → frontend QueryTrace shape.
 *
 * Engine returns:  { retrieval: { per_strategy: { fts5_bm25: { hits: [...] }, vector: {...}, ... }, fused_count, ... }, generation: {...} }
 * Frontend wants:  { retrieval: { fts_results: [], vector_results: [], toc_results: [], fused_results: [] }, generation: {...} }
 */
function normaliseTrace(raw: any, req: QueryRequest, sources: any[]): any {
  const retr = raw?.retrieval ?? {}
  const perStrategy = retr.per_strategy ?? {}
  const gen = raw?.generation ?? {}

  // Map engine strategy names → frontend array keys
  const ftsHits    = (perStrategy['fts5_bm25']?.hits ?? []).map(mapTraceHit)
  const vectorHits = (perStrategy['vector']?.hits ?? []).map(mapTraceHit)
  const tocHits    = (perStrategy['toc_heading']?.hits ?? []).map(mapTraceHit)

  // Build fused results from the top-level sources (which are the final fused chunks)
  const fusedResults = sources.map((s: any, i: number) => ({
    rank: i + 1,
    chunk_id: s.source_id ?? '',
    score: s.confidence ?? null,
    snippet: s.snippet ?? '',
    page_number: s.page_number ?? null,
    book_title: s.book_title ?? '',
  }))

  // FTS query used (grab from fts5_bm25 strategy if available)
  const ftsQuery = perStrategy['fts5_bm25']?.query_used ?? req.question

  return {
    question: retr.question ?? req.question,
    top_k: retr.top_k ?? req.top_k ?? 5,
    filters: retr.filters ?? req.filters ?? null,
    active_book_title: null,
    retrieval: {
      fetch_k: retr.fetch_k ?? (req.top_k ?? 5) * 3,
      fts_query: ftsQuery,
      fts_results: ftsHits,
      vector_results: vectorHits,
      toc_results: tocHits,
      fused_results: fusedResults,
    },
    generation: {
      model: gen.model ?? req.model ?? '',
      system_prompt: gen.custom_system_prompt ?? '',
      user_prompt: '',
    },
  }
}

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
    book_id_string: s.book_id_string ?? '',
    citation_index: s.citation_index ?? undefined,
    book_title: s.book_title ?? '',
    chapter_title: s.chapter_title ?? null,
    page_number: s.page_number ?? 1,
    snippet: s.text ?? s.snippet ?? '',
    bbox: s.bbox
      ? { x0: s.bbox.x0, y0: s.bbox.y0, x1: s.bbox.x1, y1: s.bbox.y1 }
      : null,
    page_dim: s.bbox?.page_width && s.bbox?.page_height
      ? { width: s.bbox.page_width, height: s.bbox.page_height }
      : null,
    confidence: s.score ?? 1,
  }))

  return {
    answer: res.answer ?? '',
    sources,
    retrieval_stats: {
      fts_hits: res.stats?.fts5_bm25_hits ?? res.stats?.fts_hits ?? 0,
      vector_hits: res.stats?.vector_hits ?? 0,
      toc_hits: res.stats?.toc_heading_hits ?? 0,
      fused_count: sources.length,
    },
    trace: normaliseTrace(res.trace, req, sources),
  }
}

export async function fetchDemo(): Promise<QueryResponse> {
  return queryTextbook({ question: 'What is BM25?', top_k: 3 })
}

// ─── Auto-generated Questions ────────────────────────────────────────────────

export interface GeneratedQuestion {
  question: string
  book_id: string
  book_title: string
  topic_hint: string
}

export async function fetchGeneratedQuestions(
  bookIds: string[],
  count = 6,
  model?: string,
): Promise<GeneratedQuestion[]> {
  try {
    const body: Record<string, unknown> = { book_ids: bookIds, count }
    if (model) body.model = model
    const data = await request<{ questions: GeneratedQuestion[] }>(
      `${ENGINE}/engine/questions`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
    )
    return data.questions ?? []
  } catch {
    return []
  }
}
