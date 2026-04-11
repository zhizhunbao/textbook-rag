/**
 * Library feature — 资料库模块
 *
 * 浏览、搜索、筛选已索引的教材
 *
 * 文件结构:
 *   types.ts          — 类型定义 (LibraryBook, BookCategory, BookStatus)
 *   api.ts            — Payload REST API 封装
 *   useLibraryBooks.ts — 带搜索/筛选/自动轮询的数据 hook
 *   StatusBadge.tsx   — 状态标签组件 (pending/processing/indexed/error)
 *   BookCard.tsx      — 单本书卡片组件
 *   LibraryPage.tsx   — 资料库主页面
 */

export { default as LibraryPage } from './LibraryPage'
export { default as BookCard } from './BookCard'
export { default as StatusBadge, PipelineProgress, StageDot } from './StatusBadge'
export { useLibraryBooks } from './useLibraryBooks'
export * from './types'
export * from './api'
