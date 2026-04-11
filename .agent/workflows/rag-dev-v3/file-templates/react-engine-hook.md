# 3.23 `features/engine/<engine-module>/use<Name>.ts` — Engine 自定义 hook

```typescript
/**
 * use<Name> — <一句话描述>.
 *
 * Usage: const { items, loading, error } = use<Name>()
 */

'use client'

import { useState, useEffect } from 'react'
import { fetch<Entities> } from './api'
import type { <Entity> } from './types'

// ============================================================
// Hook
// ============================================================
export function use<Name>() {

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
  // Return
  // ==========================================================
  return { items, loading, error }
}
```
