# 2.2 `collections/endpoints/<endpoint-name>.ts` — 自定义端点

```typescript
/**
 * <endpoint-name> — <一句话描述>.
 *
 * Route: GET /api/<collection>/<endpoint-name>
 */

import type { PayloadHandler } from 'payload'

// ============================================================
// Handler
// ============================================================
export const <endpointName>Handler: PayloadHandler = async (req, res) => {
  try {
    const { payload } = req

    // TODO: implement
    const result = {}

    return res.json(result)
  } catch (error) {
    return res.status(500).json({ error: 'Internal Server Error' })
  }
}
```
