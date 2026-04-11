# 3.9 `features/shared/hooks/use<Name>.ts` — 共享 Hook

```typescript
/**
 * use<Name> — <一句话描述>.
 *
 * Usage: const { <value> } = use<Name>(<params>)
 */

'use client'

import { useState, useEffect } from 'react'

// ============================================================
// Types
// ============================================================
interface Use<Name>Options {
  // TODO: define options
}

interface Use<Name>Return {
  data: unknown
  loading: boolean
  error: Error | null
}

// ============================================================
// Hook
// ============================================================
export function use<Name>(options?: Use<Name>Options): Use<Name>Return {

  // ==========================================================
  // State
  // ==========================================================
  const [data, setData] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // ==========================================================
  // Effects
  // ==========================================================
  useEffect(() => {
    // TODO: implement async logic
    setLoading(true)
    setError(null)
    Promise.resolve()
      .then(() => {
        // TODO: fetch / compute
      })
      .catch((err) => setError(err instanceof Error ? err : new Error(String(err))))
      .finally(() => setLoading(false))
  }, [])

  // ==========================================================
  // Return
  // ==========================================================
  return { data, loading, error }
}
```
