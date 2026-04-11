# 2.6 `seed/<data-source>.ts` — 预置数据源

```typescript
/**
 * <data-source> seed — <一句话描述>.
 *
 * Populates: <Collection> collection
 */

import type { Payload } from 'payload'
import type { SeedEntry } from './types'

// ============================================================
// Data
// ============================================================
export const <dataSource>Data: SeedEntry[] = [
  {
    // TODO: define seed entries
  },
]

// ============================================================
// Seeder
// ============================================================
export async function seed<DataSource>(payload: Payload): Promise<void> {
  for (const entry of <dataSource>Data) {
    await payload.create({
      collection: '<collection-slug>',
      data: entry,
    })
  }
}
```
