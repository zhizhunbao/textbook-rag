/**
 * usePersonas — Fetch enabled consulting personas from Payload CMS.
 *
 * Returns { personas, loading, error } for the OnboardingPage.
 * Data source: GET /api/consulting-personas?where[isEnabled][equals]=true&sort=sortOrder
 */

'use client'

import { useState, useEffect, useCallback } from 'react'

// ── Types ──

export interface Persona {
  id: number
  name: string
  nameEn?: string
  slug: string
  icon?: string
  avatar?: string
  category?: string
  description?: string
}

interface UsePersonasReturn {
  personas: Persona[]
  loading: boolean
  error: string | null
  refetch: () => void
}

// ── Hook ──

export function usePersonas(): UsePersonasReturn {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchPersonas = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(
        '/api/consulting-personas?where[isEnabled][equals]=true&sort=sortOrder&limit=50',
        { credentials: 'include' },
      )
      if (!res.ok) throw new Error(`Failed to fetch personas: ${res.status}`)
      const json = await res.json()
      setPersonas(json.docs ?? [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchPersonas()
  }, [fetchPersonas])

  return { personas, loading, error, refetch: fetchPersonas }
}
