/**
 * useQueryState — Persist UI state in URL search params so that
 * page refreshes restore the same view.
 *
 * Usage:
 *   const [tab, setTab] = useQueryState('tab', 'import')
 *   // URL: ?tab=pipeline  →  tab === 'pipeline'
 *   // setTab('files')     →  updates URL to ?tab=files
 *
 * Supports string values only. Multiple useQueryState hooks on the
 * same page preserve each other's params.
 *
 * Requires a <Suspense> boundary above any component using this hook
 * (Next.js App Router requirement for useSearchParams).
 */

'use client'

import { useCallback, useMemo } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'

/**
 * Sync a single key in URL search params with React state.
 *
 * @param key         — search-param key (e.g. 'tab', 'filter')
 * @param defaultValue — fallback when the param is absent
 * @returns [value, setValue] — same API as useState<string>
 */
export function useQueryState(
  key: string,
  defaultValue: string,
): [string, (next: string) => void] {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()

  // Read current value from URL (or fall back to default)
  const value = useMemo(() => {
    return searchParams.get(key) ?? defaultValue
  }, [searchParams, key, defaultValue])

  // Update URL param while preserving other params
  const setValue = useCallback(
    (next: string) => {
      const params = new URLSearchParams(searchParams.toString())
      if (next === defaultValue) {
        params.delete(key) // keep URL clean when value equals default
      } else {
        params.set(key, next)
      }
      const qs = params.toString()
      router.replace(`${pathname}${qs ? `?${qs}` : ''}`, { scroll: false })
    },
    [searchParams, key, defaultValue, router, pathname],
  )

  return [value, setValue]
}
