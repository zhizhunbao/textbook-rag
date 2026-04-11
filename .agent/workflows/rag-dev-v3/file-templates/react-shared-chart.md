# 3.14 `features/shared/components/charts/<chart-type>.tsx` — 图表组件

```tsx
/**
 * <chart-type> — <一句话描述>.
 *
 * Usage: <<ChartType> data={data} />
 */

'use client'

// ============================================================
// Types
// ============================================================
interface <ChartType>Props {
  data: unknown[]
  // TODO: define props
}

// ============================================================
// Component
// ============================================================
export function <ChartType>({ data }: <ChartType>Props) {
  return (
    <div className="chart-container">
      {/* TODO: implement chart rendering */}
    </div>
  )
}
```
