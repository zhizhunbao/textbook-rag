# 3.6 `features/providers/messages.ts` — i18n 翻译字典

> 本文件已固定，不可新增。模板仅供参考。

```typescript
/**
 * messages — i18n 翻译字典.
 *
 * Centralises all UI strings for future localisation.
 */

// ============================================================
// Messages
// ============================================================
export const messages = {
  common: {
    loading: '加载中…',
    error: '出错了',
    retry: '重试',
    save: '保存',
    cancel: '取消',
    confirm: '确认',
  },
  // TODO: add feature-specific message groups
} as const

export type Messages = typeof messages
```
