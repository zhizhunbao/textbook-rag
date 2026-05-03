/**
 * ParsePreviewTab — MinerU parse product viewer with content-type sub-tabs.
 *
 * Data source: Engine GET /engine/books/{book_id}/parse-stats
 *
 * Layout: 2-column
 *   Left:  Book selector grouped by category folders (uses shared useBookSidebar)
 *   Right: Sub-tab bar (Text/Image/Table/Equation/Discarded) + paginated content
 *
 * Each sub-tab shows items filtered by content_type with count badges.
 * Supports "Load More" pagination.
 *
 * Ref: AQ-03 + AQ-07 — Parse Preview Tab + Sub-tabs
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  FileSearch,
  BookOpen,
  Layers,
  FileText,
  Image,
  Table2,
  Heading,
  ChevronRight,
  Folder,
  FolderOpen,
  Trash2,
  Calculator,
  Ban,
  ChevronDown,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { useBooks, useBookSidebar } from '@/features/shared/books'
import { cn } from '@/features/shared/utils'
import { fetchParseStats, deleteBookWithCleanup } from '../api'
import type { ParseStats, ParseSample, ContentFilterType } from '../types'

// ============================================================
// Sub-tab definitions (AQ-07)
// ============================================================
interface SubTabDef {
  key: ContentFilterType
  label: string
  icon: React.ElementType
  color: string  // badge/icon color
}

const SUB_TABS: SubTabDef[] = [
  { key: 'text',      label: 'Text',      icon: FileText,   color: 'blue' },
  { key: 'image',     label: 'Image',     icon: Image,      color: 'emerald' },
  { key: 'table',     label: 'Table',     icon: Table2,     color: 'amber' },
  { key: 'equation',  label: 'Equation',  icon: Calculator, color: 'purple' },
  { key: 'discarded', label: 'Discarded', icon: Ban,         color: 'red' },
]

const TYPE_ICONS: Record<string, React.ElementType> = {
  text: FileText,
  image: Image,
  table: Table2,
  title: Heading,
  equation: Calculator,
  discarded: Ban,
}

const PAGE_SIZE = 50

// ============================================================
// Component
// ============================================================
export default function ParsePreviewTab() {
  const { locale } = useI18n()
  const isZh = locale === 'zh'
  const { books, loading: booksLoading, refetch } = useBooks()

  // Build sidebar items with category folders
  const { sidebarItems } = useBookSidebar(books, {
    mode: 'by-book',
    isZh,
    bookIcon: <BookOpen className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />,
    categoryIcons: {},
  })

  const [selectedBookId, setSelectedBookId] = useState<string | null>(null)
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>({})
  const [totalItems, setTotalItems] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  // Sub-tab state (AQ-07)
  const [activeSubTab, setActiveSubTab] = useState<ContentFilterType>('text')
  const [samples, setSamples] = useState<ParseSample[]>([])
  const [filteredCount, setFilteredCount] = useState(0)
  const [loadingStats, setLoadingStats] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [deletingBookId, setDeletingBookId] = useState<string | null>(null)

  // ==========================================================
  // Fetch overview stats (type counts) when book changes
  // ==========================================================
  const loadOverview = useCallback(async (bookId: string) => {
    try {
      const data = await fetchParseStats(bookId, { limit: 0 })
      setTypeCounts(data.typeCounts)
      setTotalItems(data.totalItems)
      setTotalPages(data.totalPages)
    } catch {
      setTypeCounts({})
      setTotalItems(0)
      setTotalPages(0)
    }
  }, [])

  // ==========================================================
  // Fetch filtered samples when sub-tab or book changes
  // ==========================================================
  const loadSubTab = useCallback(async (bookId: string, contentType: ContentFilterType, offset = 0, append = false) => {
    setLoadingStats(true)
    setError(null)
    try {
      const data = await fetchParseStats(bookId, {
        contentType,
        limit: PAGE_SIZE,
        offset,
      })
      setFilteredCount(data.filteredCount ?? 0)
      if (append) {
        setSamples(prev => [...prev, ...data.samples])
      } else {
        setSamples(data.samples)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load'
      setError(msg)
      if (!append) {
        setSamples([])
        setFilteredCount(0)
      }
    } finally {
      setLoadingStats(false)
    }
  }, [])

  // On book selection change → load overview + first sub-tab
  useEffect(() => {
    if (selectedBookId) {
      loadOverview(selectedBookId)
      loadSubTab(selectedBookId, activeSubTab)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBookId])

  // On sub-tab change → reload samples
  useEffect(() => {
    if (selectedBookId) {
      loadSubTab(selectedBookId, activeSubTab)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSubTab])

  // ==========================================================
  // Load more handler
  // ==========================================================
  const handleLoadMore = useCallback(() => {
    if (selectedBookId) {
      loadSubTab(selectedBookId, activeSubTab, samples.length, true)
    }
  }, [selectedBookId, activeSubTab, samples.length, loadSubTab])

  // ==========================================================
  // Collapse toggle
  // ==========================================================
  const toggleExpand = useCallback((key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  // ==========================================================
  // Delete book
  // ==========================================================
  const handleDeleteBook = useCallback(async (bookId: string) => {
    const book = books.find((b) => b.book_id === bookId)
    const title = book?.title ?? bookId
    const confirmed = window.confirm(
      isZh
        ? `确定删除「${title}」？将同时清理向量库和解析文件。`
        : `Delete "${title}"? This will also clean up vectors and parsed files.`,
    )
    if (!confirmed) return

    setDeletingBookId(bookId)
    try {
      await deleteBookWithCleanup(book?.id ?? 0, bookId)
      if (selectedBookId === bookId) {
        setSelectedBookId(null)
        setSamples([])
      }
      refetch()
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setDeletingBookId(null)
    }
  }, [books, isZh, selectedBookId, refetch])

  // ==========================================================
  // Determine visible sidebar items (respecting collapsed state)
  // ==========================================================
  const visibleItems = sidebarItems.filter((item, idx) => {
    if (item.key === 'all') return true
    const indentLevel = (item as { indentLevel?: number }).indentLevel ?? 0
    if (indentLevel === 0) return true

    for (let i = idx - 1; i >= 0; i--) {
      const parent = sidebarItems[i]
      const parentIndent = (parent as { indentLevel?: number }).indentLevel ?? 0
      if (parentIndent < indentLevel) {
        if (!expanded.has(parent.key)) return false
        if (parentIndent > 0) {
          for (let j = i - 1; j >= 0; j--) {
            const gp = sidebarItems[j]
            const gpIndent = (gp as { indentLevel?: number }).indentLevel ?? 0
            if (gpIndent < parentIndent) {
              if (!expanded.has(gp.key)) return false
              break
            }
          }
        }
        break
      }
    }
    return true
  })

  const hasMore = samples.length < filteredCount

  return (
    <div className="flex gap-4 h-full min-h-[400px]">
      {/* ── Left: Book selector with category folders ── */}
      <div className="w-56 shrink-0 rounded-lg border border-border bg-card overflow-y-auto">
        <div className="px-3 py-2.5 border-b border-border">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            {isZh ? '选择书本' : 'Select Book'}
          </span>
        </div>

        {booksLoading ? (
          <div className="flex items-center justify-center py-10">
            <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          </div>
        ) : books.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <Layers className="h-5 w-5 text-muted-foreground mx-auto mb-1.5" />
            <p className="text-xs text-muted-foreground">
              {isZh ? '暂无书本' : 'No books available'}
            </p>
          </div>
        ) : (
          <div className="p-1">
            {visibleItems.map((item) => {
              const indentLevel = (item as { indentLevel?: number }).indentLevel ?? 0
              const isBookItem = item.key.startsWith('book::')
              const isCollapsible = (item as { collapsible?: boolean }).collapsible
              const isExpanded = expanded.has(item.key)
              const bookId = isBookItem ? item.key.slice(6) : null

              if (item.key === 'all') return null

              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => {
                    if (isBookItem && bookId) {
                      setSelectedBookId(bookId)
                    } else if (isCollapsible) {
                      toggleExpand(item.key)
                    }
                  }}
                  className={cn(
                    'w-full flex items-center gap-2 py-2 rounded-md text-left transition-colors text-xs group/item',
                    isBookItem && selectedBookId === bookId
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
                  )}
                  style={{ paddingLeft: `${10 + indentLevel * 14}px`, paddingRight: '8px' }}
                >
                  {isCollapsible && (
                    <ChevronRight className={cn(
                      'h-3 w-3 shrink-0 transition-transform duration-200',
                      isExpanded && 'rotate-90',
                    )} />
                  )}

                  {isBookItem ? (
                    <BookOpen className="h-4 w-4 shrink-0" />
                  ) : (
                    isExpanded
                      ? <FolderOpen className="h-4 w-4 shrink-0" />
                      : <Folder className="h-4 w-4 shrink-0" />
                  )}

                  <span className="truncate flex-1">{item.label}</span>

                  {isBookItem && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleDeleteBook(bookId!) }}
                      disabled={deletingBookId === bookId}
                      className="opacity-0 group-hover/item:opacity-100 flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all disabled:opacity-50"
                      title={isZh ? '删除' : 'Delete'}
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}

                  {item.count !== undefined && item.count > 0 && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground shrink-0">
                      {item.count}
                    </span>
                  )}

                  {isBookItem && selectedBookId === bookId && (
                    <ChevronRight className="h-3 w-3 shrink-0 text-primary" />
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Right: Sub-tab bar + Content ── */}
      <div className="flex-1 min-w-0 flex flex-col overflow-y-auto">
        {!selectedBookId && (
          <EmptyState
            title={isZh ? '选择一本书查看解析数据' : 'Select a book to view parse data'}
            subtitle={isZh
              ? '左侧选择已解析的书本，按内容类型浏览 MinerU 解析产物。'
              : 'Choose a parsed book from the left panel to browse MinerU parse products by content type.'}
            icon={FileSearch}
          />
        )}

        {selectedBookId && (
          <>
            {/* ── Sub-tab bar (AQ-07) ── */}
            <div className="flex items-center gap-1 border-b border-border pb-2 mb-3 flex-wrap">
              {SUB_TABS.map(tab => {
                const count = typeCounts[tab.key] ?? 0
                const isActive = activeSubTab === tab.key
                const Icon = tab.icon
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveSubTab(tab.key)}
                    className={cn(
                      'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150',
                      isActive
                        ? 'bg-primary/10 text-primary border border-primary/30'
                        : 'text-muted-foreground hover:bg-secondary hover:text-foreground border border-transparent',
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{tab.label}</span>
                    <span className={cn(
                      'text-[10px] font-bold px-1.5 py-0.5 rounded-full tabular-nums',
                      isActive
                        ? `bg-${tab.color}-500/15 text-${tab.color}-400`
                        : 'bg-muted text-muted-foreground',
                    )}>
                      {count}
                    </span>
                  </button>
                )
              })}

              {/* Totals summary */}
              <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">
                {totalItems.toLocaleString()} items · {totalPages} pages
              </span>
            </div>

            {/* ── Loading ── */}
            {loadingStats && samples.length === 0 && (
              <div className="flex items-center justify-center py-20">
                <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
              </div>
            )}

            {/* ── Error ── */}
            {error && (
              <EmptyState
                title={isZh ? '未找到解析数据' : 'No parse data found'}
                subtitle={error.includes('404')
                  ? (isZh ? '该书尚未被 MinerU 解析，请先在导入 Tab 上传并触发解析。' : 'This book has not been parsed by MinerU yet. Upload and trigger parsing in the Import tab.')
                  : error}
                icon={FileSearch}
              />
            )}

            {/* ── Content table ── */}
            {!error && (samples.length > 0 || !loadingStats) && (
              <div className="rounded-lg border border-border overflow-hidden flex-1">
                <div className="px-4 py-2.5 bg-muted/50 border-b border-border flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    {activeSubTab} ({filteredCount.toLocaleString()})
                  </span>
                  {samples.length > 0 && (
                    <span className="text-[10px] text-muted-foreground tabular-nums">
                      {isZh ? `显示 ${samples.length} / ${filteredCount}` : `Showing ${samples.length} / ${filteredCount}`}
                    </span>
                  )}
                </div>

                {samples.length === 0 && !loadingStats ? (
                  <div className="px-4 py-8 text-center text-xs text-muted-foreground">
                    {isZh
                      ? `无 ${activeSubTab} 类型内容`
                      : `No ${activeSubTab} content found`}
                  </div>
                ) : (
                  <div className="divide-y divide-border">
                    {/* Table header */}
                    <div className="flex items-center gap-3 px-4 py-2 bg-muted/30 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                      <span className="w-8 shrink-0 text-center">#</span>
                      <span className="w-16 shrink-0">Type</span>
                      <span className="w-12 shrink-0 text-right">Page</span>
                      <span className="flex-1">Content</span>
                    </div>

                    {/* Table rows */}
                    {samples.map((sample, idx) => {
                      const Icon = TYPE_ICONS[sample.contentType] ?? FileText
                      return (
                        <div
                          key={`${sample.pageIdx}-${idx}`}
                          className="flex items-start gap-3 px-4 py-2.5 hover:bg-secondary/30 transition-colors"
                        >
                          <span className="w-8 shrink-0 text-center text-[10px] text-muted-foreground tabular-nums pt-0.5">
                            {idx + 1}
                          </span>
                          <span className="w-16 shrink-0">
                            <span className={cn(
                              'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium',
                              sample.contentType === 'title' && 'bg-purple-500/10 text-purple-400',
                              sample.contentType === 'text' && 'bg-blue-500/10 text-blue-400',
                              sample.contentType === 'table' && 'bg-amber-500/10 text-amber-400',
                              sample.contentType === 'image' && 'bg-emerald-500/10 text-emerald-400',
                              sample.contentType === 'equation' && 'bg-purple-500/10 text-purple-400',
                              sample.contentType === 'discarded' && 'bg-red-500/10 text-red-400',
                              !['title', 'text', 'table', 'image', 'equation', 'discarded'].includes(sample.contentType) && 'bg-muted text-muted-foreground',
                            )}>
                              <Icon className="h-2.5 w-2.5" />
                              {sample.contentType}
                            </span>
                          </span>
                          <span className="w-12 shrink-0 text-right text-xs text-muted-foreground tabular-nums pt-0.5">
                            {sample.pageIdx + 1}
                          </span>
                          <p className="flex-1 text-xs text-foreground leading-relaxed line-clamp-3">
                            {sample.text || (
                              <span className="italic text-muted-foreground">(empty)</span>
                            )}
                          </p>
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Load More button */}
                {hasMore && (
                  <div className="px-4 py-3 border-t border-border flex justify-center">
                    <button
                      type="button"
                      onClick={handleLoadMore}
                      disabled={loadingStats}
                      className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg border border-border bg-card text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors disabled:opacity-50"
                    >
                      {loadingStats ? (
                        <div className="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      )}
                      <span>{isZh ? '加载更多' : 'Load More'}</span>
                      <span className="text-[10px] tabular-nums text-muted-foreground">
                        ({samples.length}/{filteredCount})
                      </span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ============================================================
// Sub-components
// ============================================================

function EmptyState({
  title,
  subtitle,
  icon: Icon,
}: {
  title: string
  subtitle: string
  icon: React.ElementType
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
        <Icon className="h-7 w-7 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground text-center max-w-xs">{subtitle}</p>
    </div>
  )
}
