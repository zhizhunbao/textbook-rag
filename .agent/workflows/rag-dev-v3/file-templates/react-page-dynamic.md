# 3.2 `app/(frontend)/<page>/[<paramId>]/page.tsx` — 动态路由页面

```tsx
/**
 * /<page>/[<paramId>] — <一句话描述>.
 *
 * Thin shell: passes route params to the feature page component.
 */

import { <Feature>DetailPage } from '@/features/<feature>/<Feature>DetailPage'

// ============================================================
// Types
// ============================================================
interface PageProps {
  params: Promise<{ <paramId>: string }>
}

// ============================================================
// Page
// ============================================================
export default async function Page({ params }: PageProps) {
  const { <paramId> } = await params
  return <<Feature>DetailPage <paramId>={<paramId>} />
}
```
