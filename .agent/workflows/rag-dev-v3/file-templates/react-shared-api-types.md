# 3.16 `features/shared/api/types.ts` — API 层类型

> 本文件已固定，不可新增。模板仅供参考。

```typescript
/**
 * API types — 分页、错误响应等通用类型.
 */

// ============================================================
// Pagination
// ============================================================

/** Payload CMS 分页响应. */
export interface PaginatedResponse<T> {
  docs: T[]
  totalDocs: number
  totalPages: number
  page: number
  limit: number
  hasNextPage: boolean
  hasPrevPage: boolean
}

// ============================================================
// Error
// ============================================================

/** API 错误响应. */
export interface ApiError {
  status: number
  message: string
  errors?: Array<{ field: string; message: string }>
}
```
