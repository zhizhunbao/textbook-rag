'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import {
  Library,
  Search,
  RefreshCw,
  BookOpen,
  ChevronRight,
  Hash,
  Layers,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  MessageSquarePlus,
  CheckSquare,
  Square,
  Building2,
  Home,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { useLibraryBooks } from './useLibraryBooks'
import type { LibraryBook, BookCategory } from './types'
import { PIPELINE_STAGE_CONFIGS } from './types'
import BookCard from './BookCard'
import StatusBadge, { StageDot } from './StatusBadge'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type SidebarItem, type ViewMode } from '@/features/shared/components/SidebarLayout'
import { PipelineActions } from '@/features/pipeline'

// ── Category icon/color mapping (same as BookPicker) ─────────────────────────
const CATEGORY_CONFIG: Record<string, { label: string; labelZh: string; icon: React.ElementType; color: string }> = {
  textbook:    { label: 'Textbooks',      labelZh: '教材',     icon: BookOpen,  color: 'text-blue-400' },
  ecdev:       { label: 'EC Development', labelZh: '经济发展', icon: Building2, color: 'text-emerald-400' },
  real_estate: { label: 'Real Estate',    labelZh: '房地产',   icon: Home,      color: 'text-amber-400' },
}

type SortField = 'title' | 'authors' | 'pages' | 'chunks' | 'status' | 'updatedAt'
type SortDir = 'asc' | 'desc'

/** 全字段模糊匹配 */
function fuzzyMatch(book: LibraryBook, query: string): boolean {
  if (!query) return true
  const q = query.toLowerCase()
  return (
    book.title.toLowerCase().includes(q) ||
    (book.authors?.toLowerCase().includes(q) ?? false) ||
    book.engineBookId.toLowerCase().includes(q) ||
    (book.isbn?.toLowerCase().includes(q) ?? false) ||
    book.category.toLowerCase().includes(q) ||
    (book.subcategory?.toLowerCase().includes(q) ?? false) ||
    book.status.toLowerCase().includes(q)
  )
}

/** 排序比较 */
function compareBooks(a: LibraryBook, b: LibraryBook, field: SortField, dir: SortDir): number {
  let cmp = 0
  switch (field) {
    case 'title':
      cmp = a.title.localeCompare(b.title)
      break
    case 'authors':
      cmp = (a.authors ?? '').localeCompare(b.authors ?? '')
      break
    case 'pages':
      cmp = (a.metadata?.pageCount ?? 0) - (b.metadata?.pageCount ?? 0)
      break
    case 'chunks':
      cmp = (a.chunkCount ?? 0) - (b.chunkCount ?? 0)
      break
    case 'status': {
      const order = { indexed: 0, processing: 1, pending: 2, error: 3 }
      cmp = (order[a.status] ?? 9) - (order[b.status] ?? 9)
      break
    }
    case 'updatedAt':
      cmp = (a.updatedAt ?? '').localeCompare(b.updatedAt ?? '')
      break
  }
  return dir === 'asc' ? cmp : -cmp
}

/**
 * LibraryPage — uses SidebarLayout with category → subcategory hierarchy
 */
export default function LibraryPage() {
  const router = useRouter()
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  const {
    books,
    total,
    loading,
    error,
    category,
    setCategory,
    refresh,
  } = useLibraryBooks()

  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [sortField, setSortField] = useState<SortField>('title')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [localSearch, setLocalSearch] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())

  // We extend the filter to support subcategory: "category::subcategory"
  const [filter, setFilter] = useState<string>('all')

  // When SidebarLayout filter changes, also update the useLibraryBooks category
  const handleFilterChange = (key: string) => {
    setFilter(key)
    if (key === 'all') {
      setCategory('all')
    } else if (key.includes('::')) {
      // Subcategory filter — set parent category in hook, client-side sub-filter
      const cat = key.split('::')[0] as BookCategory
      setCategory(cat)
    } else {
      setCategory(key as BookCategory | 'all')
    }
  }

  const toggleSelect = (book: LibraryBook) => {
    if (book.status !== 'indexed') return
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(book.id)) next.delete(book.id)
      else next.add(book.id)
      return next
    })
  }

  const startNewChat = () => {
    if (selected.size === 0) return
    const state = {
      currentBookId: [...selected][0],
      sessionBookIds: [...selected],
      sessionStarted: true,
      currentPage: 1,
    }
    sessionStorage.setItem('textbook-rag-state', JSON.stringify(state))
    router.push('/chat')
  }

  // ── Compute category → subcategory tree ────────────────────────────────────
  const { categoryCounts, subcategoryMap } = useMemo(() => {
    const counts: Record<string, number> = { all: books.length }
    const subMap: Record<string, Set<string>> = {}

    for (const b of books) {
      const cat = b.category || 'textbook'
      counts[cat] = (counts[cat] || 0) + 1
      if (b.subcategory) {
        const subKey = `${cat}::${b.subcategory}`
        counts[subKey] = (counts[subKey] || 0) + 1
        if (!subMap[cat]) subMap[cat] = new Set()
        subMap[cat].add(b.subcategory)
      }
    }
    return { categoryCounts: counts, subcategoryMap: subMap }
  }, [books])

  // ── Sidebar items (same hierarchy as BookPicker) ───────────────────────────
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    const items: SidebarItem[] = [
      { key: 'all', label: isZh ? '全部教材' : 'All Books', count: categoryCounts.all || 0, icon: <Layers className="h-4 w-4 shrink-0" /> },
    ]
    for (const [catKey, cfg] of Object.entries(CATEGORY_CONFIG)) {
      const count = categoryCounts[catKey] || 0
      if (count === 0) continue
      const Icon = cfg.icon
      items.push({
        key: catKey,
        label: isZh ? cfg.labelZh : cfg.label,
        count,
        icon: <Icon className={cn('h-4 w-4 shrink-0', cfg.color)} />,
      })
      const subs = subcategoryMap[catKey]
      if (subs) {
        for (const sub of [...subs].sort()) {
          items.push({
            key: `${catKey}::${sub}`,
            label: sub,
            count: categoryCounts[`${catKey}::${sub}`] || 0,
            indent: true,
          })
        }
      }
    }
    return items
  }, [categoryCounts, subcategoryMap, isZh])

  // ── Filter + sort books ────────────────────────────────────────────────────
  const displayBooks = useMemo(() => {
    let filtered = books

    // Subcategory client-side filter
    if (filter.includes('::')) {
      const sub = filter.split('::')[1]
      filtered = filtered.filter((b) => b.subcategory === sub)
    }

    // Local fuzzy search
    if (localSearch.trim()) {
      filtered = filtered.filter((b) => fuzzyMatch(b, localSearch.trim()))
    }

    return [...filtered].sort((a, b) => compareBooks(a, b, sortField, sortDir))
  }, [books, filter, localSearch, sortField, sortDir])

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('asc') }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowUpDown className="h-3 w-3 opacity-0 group-hover/th:opacity-50" />
    return sortDir === 'asc'
      ? <ArrowUp className="h-3 w-3 text-primary" />
      : <ArrowDown className="h-3 w-3 text-primary" />
  }

  return (
    <SidebarLayout
      title={isZh ? '资料库' : 'Library'}
      icon={<Library className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={handleFilterChange}
      showViewToggle
      viewMode={viewMode}
      onViewModeChange={setViewMode}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {isZh ? `共 ${total} 本` : `${total} total`}
        </p>
      }
      loading={loading}
      loadingText={isZh ? '正在加载...' : 'Loading...'}
      error={error}
      onRetry={refresh}
      toolbar={
        <div className="flex items-center gap-2">
          <PipelineActions
            selectedBookIds={selected}
            onComplete={refresh}
          />
          <button
            onClick={refresh}
            className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            title={isZh ? '刷新' : 'Refresh'}
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      }
      footer={
        selected.size > 0 ? (
          <div className="shrink-0 flex items-center gap-3 px-4 py-2.5 bg-card border-t border-border animate-in slide-in-from-bottom-1 duration-200">
            <CheckSquare className="h-4 w-4 shrink-0 text-primary" />
            <span className="text-sm font-medium flex-1 text-foreground">
              {isZh
                ? `已选 ${selected.size} 本书`
                : `${selected.size} book${selected.size > 1 ? 's' : ''} selected`}
            </span>
            <button
              type="button"
              onClick={() => setSelected(new Set())}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded"
            >
              {isZh ? '清除' : 'Clear'}
            </button>
            <button
              type="button"
              onClick={startNewChat}
              className="flex items-center gap-2 bg-primary text-primary-foreground rounded-lg px-4 py-1.5 text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              <MessageSquarePlus className="h-4 w-4" />
              {isZh ? '开始对话' : 'New Chat'}
            </button>
          </div>
        ) : undefined
      }
    >
      {/* Search bar */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          type="text"
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          placeholder={isZh
            ? '搜索书名、作者、ISBN、分类...'
            : 'Search title, author, ISBN, category...'}
          className="w-full h-8 pl-9 pr-3 rounded-md border border-input bg-background text-xs text-foreground
                     placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/30
                     transition-colors"
        />
        {localSearch && (
          <button
            onClick={() => setLocalSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs px-1"
          >
            ✕
          </button>
        )}
      </div>

      {/* Empty state */}
      {displayBooks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
            <BookOpen className="h-7 w-7 text-muted-foreground" />
          </div>
          <h3 className="text-sm font-semibold text-foreground mb-1">
            {localSearch
              ? (isZh ? '未找到匹配结果' : 'No matches found')
              : (isZh ? '此分类暂无教材' : 'No books in this category')}
          </h3>
          <p className="text-xs text-muted-foreground text-center max-w-xs">
            {localSearch
              ? (isZh ? '尝试不同的关键词' : 'Try different keywords')
              : (isZh ? '运行 sync 同步或通过 Admin 上传 PDF' : 'Run sync or upload via Admin')}
          </p>
        </div>
      )}

      {/* ── Card/Grid view ── */}
      {displayBooks.length > 0 && viewMode === 'cards' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {displayBooks.map((book) => (
            <div key={book.id} className="relative group/card">
              <BookCard book={book} onSelect={toggleSelect} />
              {book.status === 'indexed' && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); toggleSelect(book) }}
                  className={cn(
                    'absolute top-2 right-2 z-10 flex h-6 w-6 items-center justify-center rounded-md border-2 transition-all shadow-sm',
                    selected.has(book.id)
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-muted-foreground/40 bg-card/80 text-transparent group-hover/card:text-muted-foreground'
                  )}
                >
                  {selected.has(book.id)
                    ? <CheckSquare className="h-4 w-4" />
                    : <Square className="h-4 w-4" />}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Table/List view ── */}
      {displayBooks.length > 0 && viewMode === 'table' && (
        <div className="rounded-lg border border-border overflow-hidden">
          {/* Sortable table header */}
          <div className="flex items-center gap-4 px-4 py-2 bg-muted/50 text-[11px] font-medium text-muted-foreground uppercase tracking-wider border-b border-border select-none">
            <span className="w-5 shrink-0" />
            <button
              onClick={() => toggleSort('title')}
              className="flex items-center gap-1 flex-1 group/th hover:text-foreground transition-colors"
            >
              {isZh ? '书名' : 'Title'}
              <SortIcon field="title" />
            </button>
            <button
              onClick={() => toggleSort('authors')}
              className="w-28 hidden sm:block text-right group/th hover:text-foreground transition-colors"
            >
              {isZh ? '作者' : 'Author'}
            </button>
            <button
              onClick={() => toggleSort('pages')}
              className="w-16 hidden md:block text-right group/th hover:text-foreground transition-colors"
            >
              {isZh ? '页数' : 'Pages'}
            </button>
            <button
              onClick={() => toggleSort('chunks')}
              className="w-16 hidden lg:block text-right group/th hover:text-foreground transition-colors"
            >
              Chunks
            </button>
            {/* 5 pipeline stage columns */}
            {PIPELINE_STAGE_CONFIGS.map((cfg) => (
              <span key={cfg.key} className="w-10 hidden xl:block text-center" title={cfg.label}>
                {cfg.label}
              </span>
            ))}
            <button
              onClick={() => toggleSort('status')}
              className="flex items-center justify-center gap-1 w-20 group/th hover:text-foreground transition-colors"
            >
              {isZh ? '状态' : 'Status'}
              <SortIcon field="status" />
            </button>
          </div>

          {/* Table rows */}
          {displayBooks.map((book, idx) => {
            const isChecked = selected.has(book.id)
            return (
            <button
              key={book.id}
              type="button"
              onClick={() => toggleSelect(book)}
              className={cn(
                'flex items-center gap-4 w-full px-4 py-2.5 text-left transition-colors',
                isChecked ? 'bg-primary/5 hover:bg-primary/10' : 'hover:bg-secondary/50',
                idx > 0 && 'border-t border-border',
                book.status !== 'indexed' && 'opacity-60'
              )}
            >
              {/* Checkbox */}
              <div className={cn(
                'flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-colors',
                isChecked
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-muted-foreground/30'
              )}>
                {isChecked && <CheckSquare className="h-3.5 w-3.5" />}
              </div>

              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="text-sm text-foreground truncate">
                  {book.title}
                  <span className="text-muted-foreground">.pdf</span>
                </span>
              </div>

              <span className="w-28 hidden sm:block text-xs text-muted-foreground truncate text-right">
                {book.authors || '—'}
              </span>

              <span className="w-16 hidden md:block text-xs text-muted-foreground text-right tabular-nums">
                {book.metadata?.pageCount || '—'}
              </span>

              <span className="w-16 hidden lg:block text-xs text-muted-foreground text-right tabular-nums">
                {book.chunkCount || '—'}
              </span>

              {/* 5 pipeline stage dots */}
              {PIPELINE_STAGE_CONFIGS.map((cfg) => (
                <div key={cfg.key} className="w-10 hidden xl:flex justify-center shrink-0">
                  <StageDot value={book.pipeline[cfg.key]} label={cfg.label} />
                </div>
              ))}

              <div className="w-20 flex justify-center shrink-0">
                <StatusBadge status={book.status} />
              </div>
            </button>
          )})}
        </div>
      )}
    </SidebarLayout>
  )
}
