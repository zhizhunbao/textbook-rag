/**
 * engine/retrievers/api.ts — Retriever search API calls.
 *
 * Endpoints:
 *   POST /engine/retrievers/search — retrieve chunks without generation
 *
 * Ref: S2-FE-04 — retrievers types + api
 */

// ============================================================
// Constants
// ============================================================
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Types
// ============================================================

export interface RetrieveRequest {
  question: string
  top_k?: number
  book_id_strings?: string[]
  reranker?: string | null
}

export interface RetrieveResult {
  chunk_id: string
  score: number | null
  book_id: string
  book_title: string
  page_idx: number
  content_type: string
  chapter_key: string | null
  text: string
}

export interface RetrieveResponse {
  query: string
  results: RetrieveResult[]
  count: number
  reranked: boolean
}

// ============================================================
// API Functions
// ============================================================

/**
 * Execute a retrieve-only search (no LLM generation).
 * Returns raw BM25 + Vector → RRF fused chunks.
 */
export async function retrieveSearch(req: RetrieveRequest): Promise<RetrieveResponse> {
  const res = await fetch(`${ENGINE_URL}/engine/retrievers/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: req.question,
      top_k: req.top_k ?? 5,
      book_id_strings: req.book_id_strings ?? [],
      reranker: req.reranker ?? null,
    }),
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }

  return res.json()
}
