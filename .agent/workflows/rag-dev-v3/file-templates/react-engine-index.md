# 3.20 `features/engine/<engine-module>/index.ts` — Engine 模块入口

```typescript
/**
 * <engine-module> — barrel export.
 *
 * This is the ONLY public API surface for this module.
 */

// ============================================================
// Exports
// ============================================================
export { <Feature>Page } from './components/<Feature>Page'
export type { <Type> } from './types'
```
