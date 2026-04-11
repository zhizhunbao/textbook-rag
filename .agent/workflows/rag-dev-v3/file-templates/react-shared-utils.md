# 3.8 `features/shared/utils.ts` — 纯工具函数

> 本文件已固定，不可新增。模板仅供参考。

```typescript
/**
 * utils — 纯工具函数 (无业务逻辑).
 *
 * Only stateless, side-effect-free helpers belong here.
 */

// ============================================================
// Class names
// ============================================================

/** Merge class names (falsy values are filtered out). */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

// ============================================================
// Formatting
// ============================================================

/** Format a date string to locale display. */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN')
}
```
