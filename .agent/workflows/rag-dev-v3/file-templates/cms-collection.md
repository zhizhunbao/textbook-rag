# 2.1 `collections/<CollectionName>.ts` — Collection 定义

```typescript
/**
 * <CollectionName> Collection — <一句话描述>.
 *
 * Slug: <collection-slug>
 */

import type { CollectionConfig } from 'payload'

// ============================================================
// Config
// ============================================================
export const <CollectionName>: CollectionConfig = {
  slug: '<collection-slug>',
  labels: {
    singular: '<显示名 (单数)>',
    plural: '<显示名 (复数)>',
  },
  admin: {
    useAsTitle: '<title-field>',
    defaultColumns: ['<field1>', '<field2>', 'updatedAt'],
  },

  // ============================================================
  // Fields
  // ============================================================
  fields: [
    {
      name: '<field1>',
      type: 'text',
      required: true,
    },
    {
      name: '<field2>',
      type: 'text',
    },
  ],
}
```
