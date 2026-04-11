# 3.10 `features/shared/config/<name>.ts` — 前端配置

```typescript
/**
 * <name> — <一句话描述>.
 *
 * Runtime configuration constants for <concern>.
 */

// ============================================================
// Config
// ============================================================
export const <name>Config = {
  // TODO: define config values
} as const

export type <Name>Config = typeof <name>Config
```
