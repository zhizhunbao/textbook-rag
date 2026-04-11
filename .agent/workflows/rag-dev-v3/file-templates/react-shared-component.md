# 3.12 `features/shared/components/<ComponentName>.tsx` — 通用组件

```tsx
/**
 * <ComponentName> — <一句话描述>.
 *
 * Usage: <<ComponentName> prop={value} />
 */

'use client'

import { type ReactNode } from 'react'

// ============================================================
// Types
// ============================================================
interface <ComponentName>Props {
  children?: ReactNode
  // TODO: define props
}

// ============================================================
// Component
// ============================================================
export function <ComponentName>({ children }: <ComponentName>Props) {
  return (
    <div>
      {children}
    </div>
  )
}
```
