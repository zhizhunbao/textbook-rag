# 3.4 `features/providers/<Name>Context.tsx` — 独立 Context

```tsx
/**
 * <Name>Context — <一句话描述>.
 *
 * Provides: <Name>Context (read-only context, separated from Provider)
 */

'use client'

import { createContext, useContext } from 'react'

// ============================================================
// Context
// ============================================================
export interface <Name>ContextValue {
  // TODO: define context shape
}

export const <Name>Context = createContext<<Name>ContextValue | null>(null)

// ============================================================
// Hook
// ============================================================
export function use<Name>(): <Name>ContextValue {
  const ctx = useContext(<Name>Context)
  if (!ctx) throw new Error('use<Name> must be used within <Name>Provider')
  return ctx
}
```
