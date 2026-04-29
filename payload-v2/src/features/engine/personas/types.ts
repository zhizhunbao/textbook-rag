/**
 * personas types — Consulting persona domain types.
 *
 * Shared type definitions for the engine/personas admin module.
 */

// ============================================================
// Domain types
// ============================================================

/** Status of a persona's knowledge base. */
export type PersonaKbStatus = 'ready' | 'empty' | 'processing'

/** Persona as returned by the Engine /consulting/personas endpoint. */
export interface PersonaWithStats {
  name: string
  slug: string
  icon?: string
  description?: string
  chromaCollection: string
  chunkCount: number
  status: PersonaKbStatus
}

/** Payload for creating a consulting persona from the admin UI. */
export interface CreatePersonaInput {
  name: string
  slug: string
  icon?: string
  description?: string
  systemPrompt: string
  chromaCollection: string
  mineruCategory?: string
  isEnabled?: boolean
  sortOrder?: number
}

// ============================================================
// API types
// ============================================================

/** Response from GET /engine/consulting/personas. */
export interface PersonasListResponse {
  personas: PersonaWithStats[]
}

/** Response from POST /engine/consulting/ingest. */
export interface PersonaIngestResponse {
  status: 'accepted' | 'error'
  persona_slug?: string
  collection_name?: string
  book_dir_name?: string
  pdf_path?: string
  message?: string
}

/** Response from GET /engine/consulting/status/{slug}. */
export interface PersonaStatusResponse {
  slug: string
  collection_name: string
  chunk_count: number
  has_data: boolean
}
