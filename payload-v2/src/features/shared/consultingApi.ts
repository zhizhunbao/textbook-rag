/**
 * shared/consultingApi — Client-side API for consulting query streams.
 *
 * Exposes Engine consulting endpoints for feature modules that need live LLM inference.
 */

import type { SourceInfo } from '@/features/shared/types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// GO-MON-06: Typed error for quota exceeded — triggers UpgradeModal
export class QuotaExceededError extends Error {
  action: string
  tier: string
  limit: number
  constructor(body: { detail: string; action: string; tier: string; limit: number }) {
    super(body.detail)
    this.name = 'QuotaExceededError'
    this.action = body.action
    this.tier = body.tier
    this.limit = body.limit
  }
}

export interface ConsultingQueryRequest {
  persona_slug: string
  question: string
  top_k?: number
  model?: string | null
  provider?: string | null
  country?: string         // G1-05: ISO 3166-1 alpha-2
  response_language?: string | null  // G1-07: language override
  // GO-MU-06: user_id removed — now extracted from JWT auth server-side
}

export interface ConsultingQueryResponse {
  persona: { name: string; slug: string }
  answer: string
  sources: SourceInfo[]
  stats: { source_count: number }
}

export interface PersonaInfo {
  name: string
  nameEn?: string
  slug: string
  icon?: string
  avatar?: string
  description?: string
  chromaCollection: string
  chunkCount: number
  country?: string   // G1-01
  category?: string  // G1-02
}

export interface PersonaStatus {
  slug: string
  collection_name: string
  chunk_count: number
  has_data: boolean
}

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
    source_type: s.source_type ?? undefined,
  }
}

export async function fetchConsultingPersonas(): Promise<PersonaInfo[]> {
  const res = await fetch('/api/consulting-personas?where[isEnabled][equals]=true&sort=sortOrder&limit=100&depth=0', {
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`Failed to fetch personas: ${res.status}`)
  const data = await res.json()
  const docs = data.docs ?? []
  return docs.map((d: any) => ({
    name: d.nameEn || d.name,
    nameEn: d.nameEn ?? undefined,
    slug: d.slug,
    icon: d.icon ?? undefined,
    avatar: d.avatar ?? undefined,
    description: d.description ?? undefined,
    chromaCollection: d.chromaCollection ?? `persona_${d.slug}`,
    chunkCount: 0,
    country: d.country ?? undefined,
    category: d.category ?? undefined,
  }))
}

export async function fetchPersonaStatus(slug: string): Promise<PersonaStatus> {
  const res = await fetch(`${ENGINE}/engine/consulting/status/${slug}`, {
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`Failed to fetch status: ${res.status}`)
  return res.json()
}

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
      credentials: 'include',
      body: JSON.stringify({
        persona_slug: req.persona_slug,
        question: req.question,
        top_k: req.top_k ?? 5,
        model: req.model ?? null,
        provider: req.provider ?? null,
        country: req.country ?? 'ca',
        response_language: req.response_language ?? null,
      }),
      signal: callbacks.signal,
    })

    // GO-MON-06: Detect quota exceeded (403 with upgrade_url)
    if (res.status === 403) {
      const body = await res.json().catch(() => ({ detail: 'Quota exceeded' }))
      if (body.upgrade_url) {
        throw new QuotaExceededError(body)
      }
    }

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
            // Skip malformed JSON.
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
