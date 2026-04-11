# 3.3 `features/providers/<Name>Provider.tsx` — 全局 Provider

```tsx
/**
 * <Name>Provider — <一句话描述>.
 *
 * Provides: <Name>Context
 */

'use client'

import { createContext, useContext, useState, type ReactNode } from 'react'

// ============================================================
// Context
// ============================================================
interface <Name>ContextValue {
  // TODO: define context shape
}

const <Name>Context = createContext<<Name>ContextValue | null>(null)

// ============================================================
// Hook
// ============================================================
export function use<Name>(): <Name>ContextValue {
  const ctx = useContext(<Name>Context)
  if (!ctx) throw new Error('use<Name> must be used within <Name>Provider')
  return ctx
}

// ============================================================
// Provider
// ============================================================
interface <Name>ProviderProps {
  children: ReactNode
}

export function <Name>Provider({ children }: <Name>ProviderProps) {
  // TODO: implement state

  return (
    <<Name>Context.Provider value={{}}>
      {children}
    </<Name>Context.Provider>
  )
}
```
