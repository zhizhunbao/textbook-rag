/**
 * useBooks — shared book data hook.
 *
 * Usage: const { books, loading, error, refetch } = useBooks({ status: 'indexed' })
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { fetchBooks, type FetchBooksOptions } from './api'
import type { BookBase } from './types'

// ============================================================
// Hook
// ============================================================

export function useBooks(opts?: FetchBooksOptions) {

  // ==========================================================
  // State
  // ==========================================================
  const [books, setBooks] = useState<BookBase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // ==========================================================
  // Stable options key (re-fetch on filter change)
  // ==========================================================
  const optKey = JSON.stringify(opts ?? {})

  // ==========================================================
  // Data loading — initial load shows spinner
  // ==========================================================
  const load = useCallback(async () => {
    try {
      setLoading(true)
      const data = await fetchBooks(opts)
      setBooks(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [optKey])

  // ==========================================================
  // Background refetch — silently updates without loading spinner.
  // Prevents the full-page loading overlay from flashing during
  // incremental imports, which would destroy child component state.
  // ==========================================================
  const refetch = useCallback(async () => {
    try {
      const data = await fetchBooks(opts)
      setBooks(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [optKey])

  // ==========================================================
  // Effects
  // ==========================================================
  useEffect(() => { load() }, [load])

  // ==========================================================
  // Return
  // ==========================================================
  return { books, loading, error, refetch }
}
