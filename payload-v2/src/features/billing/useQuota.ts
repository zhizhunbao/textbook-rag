/**
 * useQuota — Hook to fetch current user's quota usage from Engine billing API.
 *
 * Returns { data, loading, error, refetch } standard shape.
 * Polls every 60s when mounted to keep usage panel current.
 *
 * GO-MON-05: Data source for UsagePanel progress bars.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Types
// ============================================================

export interface QuotaBucket {
  used: number
  limit: number
  remaining: number
  period: 'day' | 'month'
}

export interface QuotaData {
  tier: 'free' | 'pro'
  query: QuotaBucket
  ingest: QuotaBucket
}

// ============================================================
// Hook
// ============================================================

const POLL_INTERVAL_MS = 60_000

export function useQuota() {
  const [data, setData] = useState<QuotaData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${ENGINE}/engine/billing/me`, {
        credentials: 'include',
      })
      if (!res.ok) {
        setError(`Failed to fetch quota: ${res.status}`)
        return
      }
      const json = await res.json()
      setData(json as QuotaData)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refetch()
    const interval = setInterval(refetch, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [refetch])

  return { data, loading, error, refetch }
}
