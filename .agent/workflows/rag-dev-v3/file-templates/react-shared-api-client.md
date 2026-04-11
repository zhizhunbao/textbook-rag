# 3.15 `features/shared/api/client.ts` — 统一 fetch 封装

> 本文件已固定，不可新增。模板仅供参考。

```typescript
/**
 * client — 统一 fetch 封装 (base URL / 错误处理 / 拦截).
 *
 * Usage:
 *   import { engineClient, payloadClient } from '@/features/shared/api/client'
 *   const data = await engineClient.get<BookList>('/books')
 */

import type { ApiError } from './types'

// ============================================================
// Base URLs
// ============================================================
const ENGINE_BASE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000'
const PAYLOAD_BASE = '' // same-origin, proxied by Next.js

// ============================================================
// Core request function
// ============================================================
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ============================================================
// Client factory
// ============================================================
function createClient(base: string) {
  return {
    get: <T>(path: string) => request<T>(`${base}${path}`),
    post: <T>(path: string, data: unknown) =>
      request<T>(`${base}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    put: <T>(path: string, data: unknown) =>
      request<T>(`${base}${path}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    del: <T>(path: string) =>
      request<T>(`${base}${path}`, { method: 'DELETE' }),
  }
}

// ============================================================
// Exports
// ============================================================

/** Engine FastAPI 客户端 (Python 后端). */
export const engineClient = createClient(ENGINE_BASE)

/** Payload CMS 客户端 (same-origin). */
export const payloadClient = createClient(PAYLOAD_BASE)
```
