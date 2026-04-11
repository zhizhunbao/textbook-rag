# 3.17 `features/layout/App<Part>.tsx` — App Shell 组件

```tsx
/**
 * App<Part> — <一句话描述>.
 *
 * Part of the App Shell (layout layer).
 */

'use client'

import { type ReactNode } from 'react'

// ============================================================
// Types
// ============================================================
interface App<Part>Props {
  children?: ReactNode
}

// ============================================================
// Component
// ============================================================
export function App<Part>({ children }: App<Part>Props) {
  return (
    <div className="app-<part>">
      {children}
    </div>
  )
}
```
