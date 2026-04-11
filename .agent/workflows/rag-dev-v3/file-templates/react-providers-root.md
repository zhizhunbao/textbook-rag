# 3.5 `features/providers/Providers.tsx` — 组合根

> 本文件已固定，不可新增。模板仅供参考。

```tsx
/**
 * Providers — 组合根，嵌套所有全局 Provider.
 *
 * Mounted once in app/(frontend)/layout.tsx.
 */

'use client'

import { type ReactNode } from 'react'

// ============================================================
// Component
// ============================================================
interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    // Nest providers inside-out (innermost = closest to children)
    <>{children}</>
  )
}
```
