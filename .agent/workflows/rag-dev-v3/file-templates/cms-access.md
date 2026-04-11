# 2.5 `access/is<Role>.ts` — 访问控制策略

```typescript
/**
 * is<Role> — <一句话描述>.
 *
 * Returns true if the requesting user has the <Role> role.
 */

import type { Access } from 'payload'

// ============================================================
// Access control
// ============================================================
export const is<Role>: Access = ({ req: { user } }) => {
  return user?.role === '<role>'
}
```
