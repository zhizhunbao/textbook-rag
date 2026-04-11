# 3.21 `features/engine/<engine-module>/types.ts` — Engine 模块类型

```typescript
/**
 * <engine-module> types — <一句话描述>.
 *
 * Shared type definitions for the <engine-module> module.
 */

// ============================================================
// Domain types
// ============================================================

/** Represents a single <entity>. */
export interface <Entity> {
  id: string
  // TODO: define fields
  createdAt: string
  updatedAt: string
}

// ============================================================
// API types
// ============================================================

/** API response shape for <entity> list. */
export interface <Entity>ListResponse {
  items: <Entity>[]
  total: number
}
```
