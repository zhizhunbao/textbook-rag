/**
 * personas API — Engine API calls for persona knowledge base management.
 *
 * All API calls for the engine/personas admin module.
 * Persona listing uses Engine API (real-time collection stats).
 * Ingest triggers Engine background processing.
 */

import type {
  PersonaIngestResponse,
  PersonaStatusResponse,
  PersonaWithStats,
} from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Engine FastAPI (cross-origin) — admin operations
// ============================================================

/** Fetch all enabled personas with live ChromaDB stats. */
export async function fetchPersonasWithStats(): Promise<PersonaWithStats[]> {
  const res = await fetch(`${ENGINE}/engine/consulting/personas`)
  if (!res.ok) throw new Error(`Failed to fetch personas: ${res.status}`)
  const data = await res.json()
  const personas: PersonaWithStats[] = (data.personas ?? []).map(
    (p: PersonaWithStats) => ({
      ...p,
      status: p.chunkCount > 0 ? 'ready' : 'empty',
    }),
  )
  return personas
}

/** Get collection status for a single persona. */
export async function fetchPersonaStatus(
  slug: string,
): Promise<PersonaStatusResponse> {
  const res = await fetch(`${ENGINE}/engine/consulting/status/${slug}`)
  if (!res.ok) throw new Error(`Failed to fetch status: ${res.status}`)
  return res.json()
}

/** Trigger PDF ingest into a persona's knowledge base. */
export async function ingestPersonaPdf(params: {
  personaSlug: string
  pdfFilename: string
  forceParse?: boolean
}): Promise<PersonaIngestResponse> {
  const res = await fetch(`${ENGINE}/engine/consulting/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      persona_slug: params.personaSlug,
      pdf_filename: params.pdfFilename,
      force_parse: params.forceParse ?? false,
    }),
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Ingest failed: ${res.status} ${body}`)
  }
  return res.json()
}

/** Initialize (ensure) a persona's ChromaDB collection via Engine. */
export async function initPersonaCollection(
  slug: string,
): Promise<{ status: string; collection_name: string }> {
  const res = await fetch(
    `${ENGINE}/engine/consulting/status/${slug}`,
  )
  if (!res.ok) throw new Error(`Init check failed: ${res.status}`)
  return res.json()
}
