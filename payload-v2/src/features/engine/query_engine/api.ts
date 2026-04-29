/**
 * query_engine API — Query engine FastAPI wrappers.
 *
 * All API calls for the query_engine module.
 * Wraps Engine FastAPI query endpoints (sync + streaming).
 */

import type { BboxEntry, SourceInfo } from '../retrievers/types'
import type {
  BookSummary,
  BookDetail,
  QueryRequest,
  QueryResponse,
  TocEntry,
} from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

/** Generic JSON fetch with error handling. */
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ============================================================
// Books (for query context)
// ============================================================

export async function fetchBooks(): Promise<BookSummary[]> {
  const data = await request<{ docs: any[] }>('/api/books?limit=200&where[status][equals]=indexed')
  return data.docs.map((b) => ({
    id: b.id,
    book_id: b.engineBookId ?? String(b.id),
    title: b.title ?? '(untitled)',
    authors: b.authors ?? '',
    page_count: 0,
    chapter_count: 0,
    chunk_count: b.chunkCount ?? 0,
    category: b.category ?? 'textbooks',
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
    category: b.category ?? 'textbooks',
    subcategory: b.subcategory ?? '',
    chapters: [],
  }
}

/** Fetch TOC entries for a specific book from Engine. */
export async function fetchToc(bookId: string): Promise<TocEntry[]> {
  return request<TocEntry[]>(`${ENGINE}/engine/books/${bookId}/toc`)
}

/** Build the PDF download URL for a book. */
export function getPdfUrl(bookId: string, variant: 'origin' | 'layout' = 'origin'): string {
  return `${ENGINE}/engine/books/${bookId}/pdf?variant=${variant}`
}

// ============================================================
// Query (sync)
// ============================================================

/** Map raw trace hit payload to a normalised object. */
function mapTraceHit(h: any) {
  return {
    rank: h.rank ?? 0,
    chunk_id: h.chunk_id ?? '',
    score: h.score ?? null,
    snippet: h.snippet ?? '',
    page_number: h.page_number ?? null,
    book_title: h.book_title ?? '',
  }
}

/** Normalise a raw source object into a typed SourceInfo. */
function normaliseSource(s: any): SourceInfo {
  const bboxes: BboxEntry[] = (s.bboxes ?? [])
    .filter((b: any) => b.x0 != null && b.y0 != null && b.x1 != null && b.y1 != null)
    .map((b: any) => ({
      x0: b.x0,
      y0: b.y0,
      x1: b.x1,
      y1: b.y1,
      page_width: b.page_width ?? 0,
      page_height: b.page_height ?? 0,
      page_number: b.page_number ?? 1,
    }))

  // Backend sends book_id as a string directory name (e.g. "appB");
  // use it as book_id_string fallback since book_id_string isn't sent separately
  const bookIdStr = s.book_id_string ?? (typeof s.book_id === 'string' ? s.book_id : '')

  return {
    source_id: s.chunk_id ?? String(s.page_number),
    book_id: s.book_id ?? 0,
    book_id_string: bookIdStr,
    citation_index: s.citation_index ?? undefined,
    book_title: s.book_title ?? '',
    chapter_title: s.chapter_title ?? null,
    page_number: s.page_number ?? 1,
    full_content: s.full_content ?? undefined,
    snippet: s.text ?? s.snippet ?? '',
    bbox: s.bbox
      ? { x0: s.bbox.x0, y0: s.bbox.y0, x1: s.bbox.x1, y1: s.bbox.y1 }
      : null,
    bboxes: bboxes.length > 0 ? bboxes : undefined,
    page_dim: s.bbox?.page_width && s.bbox?.page_height
      ? { width: s.bbox.page_width, height: s.bbox.page_height }
      : null,
    confidence: s.score ?? 1,
    score: s.score ?? undefined,
    // EV2-T1-03: pass through retrieval strategy provenance from backend
    retrieval_source: s.retrieval_source ?? undefined,
  }
}

/** Normalise raw trace payload into a structured QueryTrace. */
function normaliseTrace(raw: any, req: QueryRequest, sources: any[]): any {
  const retr = raw?.retrieval ?? {}
  const perStrategy = retr.per_strategy ?? {}
  const gen = raw?.generation ?? {}

  const ftsHits    = (perStrategy['fts5_bm25']?.hits ?? []).map(mapTraceHit)
  const vectorHits = (perStrategy['vector']?.hits ?? []).map(mapTraceHit)
  const tocHits    = (perStrategy['toc_heading']?.hits ?? []).map(mapTraceHit)

  const fusedResults = sources.map((s: any, i: number) => ({
    rank: i + 1,
    chunk_id: s.source_id ?? '',
    score: s.confidence ?? null,
    snippet: s.snippet ?? '',
    page_number: s.page_number ?? null,
    book_title: s.book_title ?? '',
  }))

  const ftsQuery = perStrategy['fts5_bm25']?.query_used ?? req.question

  return {
    question: retr.question ?? req.question,
    top_k: retr.top_k ?? req.top_k ?? 5,
    filters: retr.filters ?? req.filters ?? null,
    active_book_title: null,
    routing: raw?.routing ?? null,
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
  const res = await request<any>(`${ENGINE}/engine/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: req.question,
      top_k: req.top_k ?? 5,
      filters: req.filters ?? {},
      model: req.model,
      provider: req.provider,
      reranker: req.reranker ?? null,
      custom_system_prompt: req.custom_system_prompt ?? null,
      retrieval_mode: req.retrieval_mode ?? null,
    }),
  })

  const sources = (res.sources ?? []).map(normaliseSource)

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

// ============================================================
// Query (streaming SSE)
// ============================================================

export async function queryTextbookStream(
  req: QueryRequest,
  callbacks: {
    onToken: (token: string) => void
    onRetrievalDone?: (data: { stats: Record<string, number>; sources: SourceInfo[] }) => void
    onDone: (result: QueryResponse) => void
    onError: (error: Error) => void
    signal?: AbortSignal
  },
): Promise<void> {
  try {
    const res = await fetch(`${ENGINE}/engine/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: req.question,
        top_k: req.top_k ?? 5,
        filters: req.filters ?? {},
        model: req.model,
        provider: req.provider,
        reranker: req.reranker ?? null,
        custom_system_prompt: req.custom_system_prompt ?? null,
        retrieval_mode: req.retrieval_mode ?? null,
      }),
      signal: callbacks.signal,
    })

    if (!res.ok) {
      const body = await res.text()
      throw new Error(`${res.status}: ${body}`)
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      let currentEvent = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6)
          try {
            const data = JSON.parse(jsonStr)

            if (currentEvent === 'token') {
              callbacks.onToken(data.t ?? '')
            } else if (currentEvent === 'retrieval_done') {
              const sources = (data.sources ?? []).map(normaliseSource)
              callbacks.onRetrievalDone?.({ stats: data.stats ?? {}, sources })
            } else if (currentEvent === 'done') {
              const sources = (data.sources ?? []).map(normaliseSource)

              callbacks.onDone({
                answer: data.answer ?? '',
                sources,
                retrieval_stats: {
                  fts_hits: data.stats?.fts5_bm25_hits ?? data.stats?.fts_hits ?? 0,
                  vector_hits: data.stats?.vector_hits ?? 0,
                  toc_hits: data.stats?.toc_heading_hits ?? 0,
                  fused_count: sources.length,
                },
                trace: normaliseTrace(data.trace, req, sources),
                telemetry: data.telemetry ?? undefined,
              })
            }
          } catch {
            // Skip malformed JSON
          }
          currentEvent = ''
        }
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    callbacks.onError(err instanceof Error ? err : new Error(String(err)))
  }
}

// ============================================================
// Demo
// ============================================================

export async function fetchDemo(): Promise<QueryResponse> {
  return queryTextbook({ question: 'What is BM25?', top_k: 3 })
}
