# 3.25 `features/engine/<engine-module>/components/<Feature>Page.tsx` — Engine 页面

```tsx
/**
 * <Feature>Page — <一句话描述>.
 *
 * Route: /engine/<module>
 */

'use client'

import { useState, useEffect } from 'react'
import { fetch<Entities> } from '../api'
import type { <Entity> } from '../types'

// ============================================================
// Component
// ============================================================
export function <Feature>Page() {

  // ==========================================================
  // State
  // ==========================================================
  const [items, setItems] = useState<<Entity>[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // ==========================================================
  // Effects
  // ==========================================================
  useEffect(() => {
    fetch<Entities>()
      .then((res) => setItems(res.items))
      .catch((err) => setError(err instanceof Error ? err : new Error(String(err))))
      .finally(() => setLoading(false))
  }, [])

  // ==========================================================
  // Render
  // ==========================================================
  if (loading) return <div>Loading...</div>
  if (error) throw error

  return (
    <div>
      <h1><Feature></h1>
      {/* TODO: render items */}
    </div>
  )
}
```
