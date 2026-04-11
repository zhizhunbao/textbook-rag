# 3.13 `features/shared/components/ui/<component-name>.tsx` — 原子 UI 组件

```tsx
/**
 * <component-name> — <一句话描述>.
 *
 * Atomic UI component (shadcn/ui style).
 */

'use client'

import { forwardRef, type ComponentPropsWithoutRef } from 'react'
import { cn } from '@/features/shared/utils'

// ============================================================
// Types
// ============================================================
interface <ComponentName>Props extends ComponentPropsWithoutRef<'div'> {
  // TODO: define custom props
}

// ============================================================
// Component
// ============================================================
export const <ComponentName> = forwardRef<<HTMLDivElement>, <ComponentName>Props>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('<base-classes>', className)}
        {...props}
      />
    )
  }
)
<ComponentName>.displayName = '<ComponentName>'
```
