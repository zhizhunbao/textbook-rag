/**
 * consulting/api — Client-side API for consulting endpoints.
 *
 * Wraps Engine FastAPI /engine/consulting/* endpoints.
 * Modeled after the textbook query_engine/api.ts but targeting persona collections.
 */

import type { SourceInfo } from '@/features/shared/types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ── Types ──

export interface ConsultingQueryRequest {
  persona_slug: string
  question: string
  top_k?: number
  model?: string | null
  provider?: string | null
  user_id?: number | null
}

export interface ConsultingQueryResponse {
  persona: { name: string; slug: string }
  answer: string
  sources: SourceInfo[]
  stats: { source_count: number }
}

export interface PersonaInfo {
  name: string
  slug: string
  icon?: string
  description?: string
  chromaCollection: string
  chunkCount: number
}

export interface PersonaStatus {
  slug: string
  collection_name: string
  chunk_count: number
  has_data: boolean
}

// ── Helpers ──

function normaliseSource(s: any): SourceInfo {
  return {
    source_id: s.chunk_id ?? String(s.page_number ?? ''),
    book_id: s.book_id ?? 0,
    book_id_string: s.book_id_string ?? '',
    citation_index: s.citation_index ?? undefined,
    book_title: s.book_title ?? '',
    chapter_title: s.chapter_title ?? null,
    page_number: s.page_number ?? 1,
    full_content: s.full_content ?? undefined,
    snippet: s.text ?? s.snippet ?? '',
    bbox: null,
    page_dim: null,
    confidence: s.score ?? 1,
    score: s.score ?? undefined,
    retrieval_source: s.retrieval_source ?? s.retrieval_origin ?? undefined,
  }
}

// ── API Functions ──

/** List enabled consulting personas with collection stats. */
export async function fetchConsultingPersonas(): Promise<PersonaInfo[]> {
  const res = await fetch(`${ENGINE}/engine/consulting/personas`)
  if (!res.ok) throw new Error(`Failed to fetch personas: ${res.status}`)
  const data = await res.json()
  return data.personas ?? []
}

/** Get collection status for a single persona. */
export async function fetchPersonaStatus(slug: string): Promise<PersonaStatus> {
  const res = await fetch(`${ENGINE}/engine/consulting/status/${slug}`)
  if (!res.ok) throw new Error(`Failed to fetch status: ${res.status}`)
  return res.json()
}

/** SSE streaming query against a consulting persona's knowledge base. */
export async function queryConsultingStream(
  req: ConsultingQueryRequest,
  callbacks: {
    onToken: (token: string) => void
    onRetrievalDone?: (data: { stats: Record<string, number>; sources: SourceInfo[] }) => void
    onDone: (result: ConsultingQueryResponse) => void
    onError: (error: Error) => void
    signal?: AbortSignal
  },
): Promise<void> {
  try {
    const res = await fetch(`${ENGINE}/engine/consulting/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        persona_slug: req.persona_slug,
        question: req.question,
        top_k: req.top_k ?? 5,
        model: req.model ?? null,
        provider: req.provider ?? null,
        user_id: req.user_id ?? null,
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
                persona: data.persona ?? { name: '', slug: req.persona_slug },
                answer: data.answer ?? '',
                sources,
                stats: data.stats ?? { source_count: sources.length },
              })
            } else if (currentEvent === 'error') {
              callbacks.onError(new Error(data.message ?? 'Unknown error'))
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
