# 3.7 `features/shared/types.ts` — 全局类型定义

> 本文件已固定，不可新增。模板仅供参考。

```typescript
/**
 * types — 全局共享类型定义.
 *
 * Only domain-agnostic, cross-feature types belong here.
 */

// ============================================================
// Common types
// ============================================================

/** Generic loading state tuple. */
export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

/** Sidebar navigation item. */
export interface NavItem {
  label: string
  href: string
  icon?: string
}
```
