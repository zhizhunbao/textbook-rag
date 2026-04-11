# 2.4 `hooks/<collection>/<lifecycle>.ts` — 生命周期钩子

```typescript
/**
 * <lifecycle> hook for <Collection> — <一句话描述>.
 *
 * Trigger: <afterChange | beforeValidate | ...>
 */

import type { CollectionAfterChangeHook } from 'payload'

// ============================================================
// Hook
// ============================================================
export const <lifecycle>: CollectionAfterChangeHook = async ({
  doc,
  req,
  operation,
}) => {
  if (operation === 'create') {
    // TODO: implement
  }

  return doc
}
```
