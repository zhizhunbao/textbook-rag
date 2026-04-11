import { useState, useEffect, useCallback, useRef } from 'react'

export interface PromptMode {
  id: number
  name: string
  slug: string
  description: string
  systemPrompt: string
  icon?: string
  isDefault: boolean
  updatedAt: string
}

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
      const res = await fetch('/api/prompt-modes?limit=50&sort=name', {
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
