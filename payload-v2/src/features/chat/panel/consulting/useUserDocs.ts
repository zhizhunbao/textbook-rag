/**
 * useUserDocs — Manage user's private documents for consulting.
 *
 * Usage: const { docs, loading, error, upload, remove, refetch } = useUserDocs()
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'

// ============================================================
// Types
// ============================================================

export type UserDocStatus = 'pending' | 'processing' | 'indexed' | 'error'

export interface UserDoc {
  id: number
  filename: string
  status: UserDocStatus
  chunkCount: number
  liveChunkCount: number
  chromaCollection: string
  persona: { id: number; name: string; slug: string } | null
  createdAt: string
  description?: string
}

// ============================================================
// Constants
// ============================================================

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Hook
// ============================================================

export function useUserDocs(personaSlug?: string) {

  // ==========================================================
  // State
  // ==========================================================
  const { user } = useAuth()
  const [docs, setDocs] = useState<UserDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // ==========================================================
  // Fetch docs from Engine (enriched with live ChromaDB stats)
  // ==========================================================
  const refetch = useCallback(async () => {
    if (!user?.id) return
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (personaSlug) {
        params.set('persona_slug', personaSlug)
      }

      const res = await fetch(
        `${ENGINE}/engine/consulting/user-doc/list?${params}`,
        { credentials: 'include' },
      )
      if (!res.ok) throw new Error(`Failed to fetch docs: ${res.status}`)
      const data = await res.json()
      setDocs(data.docs ?? [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [user?.id, personaSlug])

  // ==========================================================
  // Effects
  // ==========================================================
  useEffect(() => {
    void refetch()
  }, [refetch])

  // ==========================================================
  // Upload — triggers Engine ingest after Payload file upload
  // ==========================================================
  const upload = useCallback(
    async (params: {
      docId: number
      pdfFilename: string
      personaSlug: string
    }) => {
      if (!user?.id) return

      const res = await fetch(
        `${ENGINE}/engine/consulting/user-doc/ingest`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            persona_slug: params.personaSlug,
            doc_id: params.docId,
            pdf_filename: params.pdfFilename,
          }),
        },
      )

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Ingest failed: ${res.status} ${text}`)
      }

      const result = await res.json()
      // Refresh doc list after ingest trigger
      await refetch()
      return result
    },
    [user?.id, refetch],
  )

  // ==========================================================
  // Remove — delete doc + ChromaDB vectors
  // ==========================================================
  const remove = useCallback(
    async (docId: number) => {
      const res = await fetch(
        `${ENGINE}/engine/consulting/user-doc/${docId}?delete_vectors=true`,
        { method: 'DELETE', credentials: 'include' },
      )

      if (!res.ok) {
        throw new Error(`Delete failed: ${res.status}`)
      }

      // Optimistic removal
      setDocs((prev) => prev.filter((d) => d.id !== docId))
      return res.json()
    },
    [],
  )

  // ==========================================================
  // Return
  // ==========================================================
  return { docs, loading, error, upload, remove, refetch }
}
