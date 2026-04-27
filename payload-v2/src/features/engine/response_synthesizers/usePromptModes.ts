/**
 * engine/response_synthesizers/usePromptModes.ts
 * Aligned with: llama_index.response_synthesizers → engine-v2/response_synthesizers/
 *
 * React hook to fetch and manage prompt modes from Payload CMS Prompts collection.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import type { PromptMode } from './types'

export interface UsePromptModesReturn {
  promptModes: PromptMode[]
  loading: boolean
  error: string | null
  getDefaultMode: () => PromptMode | null
}

export function usePromptModes(autoLoad = true): UsePromptModesReturn {
  const [promptModes, setPromptModes] = useState<PromptMode[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  const fetchModes = useCallback(async () => {
    if (!mountedRef.current) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/prompts?limit=50&sort=sortOrder&where[isEnabled][equals]=true&where[type][equals]=mode', {
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      if (mountedRef.current) {
        setPromptModes(json.docs || [])
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Fetch failed')
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    if (autoLoad) {
      fetchModes()
    }
    return () => {
      mountedRef.current = false
    }
  }, [autoLoad, fetchModes])

  const getDefaultMode = useCallback(() => {
    return promptModes.find((m) => m.isDefault) ?? promptModes[0] ?? null
  }, [promptModes])

  return { promptModes, loading, error, getDefaultMode }
}
