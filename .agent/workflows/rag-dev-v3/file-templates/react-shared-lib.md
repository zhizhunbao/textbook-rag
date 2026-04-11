# 3.11 `features/shared/lib/<library>.ts` — 第三方库封装

```typescript
/**
 * <library> — <Library> wrapper / adapter.
 *
 * Isolates external dependency for easy replacement.
 */

import { <something> } from '<library-package>'

// ============================================================
// Wrapper
// ============================================================
// Re-export with project-specific defaults
export const <wrappedName> = <something>({
  // project-specific config
})

// ============================================================
// Re-exports
// ============================================================
export type { <RelevantType> } from '<library-package>'
```
