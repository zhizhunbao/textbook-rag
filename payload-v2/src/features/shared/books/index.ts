/**
 * shared/books — barrel export.
 *
 * This is the ONLY public API surface for the books module.
 */

// ============================================================
// Exports
// ============================================================
export type { BookBase, BookCategory, BookStatus, CategoryConfig, PipelineStage, PipelineInfo } from './types'
export { CATEGORY_CONFIGS, getCategoryConfig } from './types'
export { getCategoryIcon, buildCategoryIcons } from './CategoryIcons'
export { fetchBooks, fetchIndexedBooks } from './api'
export type { FetchBooksOptions } from './api'
export { useBooks } from './useBooks'
export { useBookSidebar } from './useBookSidebar'
export type { UseBookSidebarOptions } from './useBookSidebar'
export { ChapterSidebar } from './ChapterSidebar'
export type { TocEntry } from './ChapterSidebar'
