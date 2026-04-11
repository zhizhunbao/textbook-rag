# 3.1 `app/(frontend)/<page>/page.tsx` — 路由页面 (薄壳)

```tsx
/**
 * /<page> — <一句话描述>.
 *
 * Thin shell: only imports and renders the feature page component.
 */

import { <Feature>Page } from '@/features/<feature>/<Feature>Page'

// ============================================================
// Page
// ============================================================
export default function Page() {
  return <<Feature>Page />
}
```
