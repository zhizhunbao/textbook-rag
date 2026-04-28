/**
 * usePersonaAdmin — Fetch personas with live KB stats for admin management.
 *
 * Usage: const { personas, loading, error, refetch } = usePersonaAdmin()
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { fetchPersonasWithStats } from './api'
import type { PersonaWithStats } from './types'

// ============================================================
// Hook
// ============================================================
export function usePersonaAdmin() {

  // ==========================================================
  // State
  // ==========================================================
  const [personas, setPersonas] = useState<PersonaWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // ==========================================================
  // Fetch
  // ==========================================================
  const refetch = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await fetchPersonasWithStats()
      setPersonas(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  // ==========================================================
  // Effects
  // ==========================================================
  useEffect(() => {
    void refetch()
  }, [refetch])

  // ==========================================================
  // Return
  // ==========================================================
  return { personas, loading, error, refetch }
}
