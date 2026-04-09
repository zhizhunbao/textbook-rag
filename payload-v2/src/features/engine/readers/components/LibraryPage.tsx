/**
 * LibraryPage — Book library grid/table with upload, edit, delete, and search.
 *
 * Main view for engine/readers. Composes BookCard, UploadZone,
 * BookEditDialog, and PipelineActions.
 */

'use client'

import { useState, useMemo, Suspense } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Library,
  Search,
  RefreshCw,
  BookOpen,
  Layers,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  MessageSquarePlus,
  CheckSquare,
  Square,
  Download,
  Trash2,
  Pencil,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { useBookSidebar, buildCategoryIcons } from '@/features/shared/books'
import { useLibraryBooks } from '../useLibraryBooks'
import { deleteBook } from '../api'
import type { LibraryBook, BookCategory } from '../types'
import BookCard from './BookCard'
import BookEditDialog from './BookEditDialog'
import { PipelineProgress } from './StatusBadge'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type ViewMode } from '@/features/shared/components/SidebarLayout'
import { useQueryState } from '@/features/shared/hooks/useQueryState'



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
  return (
    <Suspense>
      <LibraryPageInner />
    </Suspense>
  )
}

function LibraryPageInner() {
  const router = useRouter()
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  const {
    books,
    total,
    loading,
    error,
    refresh,
  } = useLibraryBooks()

  const [viewMode, setViewMode] = useQueryState('view', 'table') as [ViewMode, (v: string) => void]
  const [sortField, setSortField] = useState<SortField>('title')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [localSearch, setLocalSearch] = useState('')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [deleting, setDeleting] = useState<number | null>(null)
  const [editingBookId, setEditingBookId] = useState<number | null>(null)

  // Client-side filter key (category / subcategory / all)
  const [filter, setFilter] = useQueryState('filter', 'all')

  const toggleSelect = (book: LibraryBook) => {
    if (book.status !== 'indexed') return
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(book.id)) next.delete(book.id)
      else next.add(book.id)
      return next
    })
  }

  const handleDeleteSingle = async (book: LibraryBook) => {
    const confirmed = window.confirm(
      isZh
        ? `确定删除「${book.title}」？此操作不可撤销。`
        : `Delete "${book.title}"? This cannot be undone.`,
    )
    if (!confirmed) return
    setDeleting(book.id)
    try {
      await deleteBook(book.id)
      setSelected((prev) => {
        const next = new Set(prev)
        next.delete(book.id)
        return next
      })
      refresh()
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setDeleting(null)
    }
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

  // ── Book sidebar (via shared hook) ──────────────────────────────────────────
  const booksForSidebar = useMemo(() =>
    books.map((b) => ({
      id: b.id,
      book_id: b.engineBookId,
      title: b.title,
      authors: b.authors ?? '',
      category: b.category ?? 'textbook',
      subcategory: b.subcategory ?? '',
      chunk_count: b.chunkCount ?? 0,
      status: b.status as 'pending' | 'processing' | 'indexed' | 'error',
      pageCount: (b.metadata as any)?.pageCount ?? 0,
      fileSize: (b.metadata as any)?.fileSize ?? 0,
      createdAt: b.createdAt ?? '',
    })),
    [books],
  )

  // ── Dynamic category icons from actual book data ──────────────────────────
  const categoryIcons = useMemo(() => {
    const cats = [...new Set(booksForSidebar.map((b) => b.category || 'textbook'))]
    return buildCategoryIcons(cats)
  }, [booksForSidebar])

  const { sidebarItems, filterBooks: _filterBooks } = useBookSidebar(booksForSidebar, {
    mode: 'by-category',
    isZh,
    allLabel: isZh ? '全部教材' : 'All Books',
    allIcon: <Layers className="h-4 w-4 shrink-0" />,
    categoryIcons,
  })

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
      onFilterChange={setFilter}
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
          <Link
            href="/engine/acquisition"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            title={isZh ? '导入 PDF' : 'Import PDF'}
          >
            <Download className="h-3.5 w-3.5" />
            {isZh ? '导入' : 'Import'}
          </Link>
          {selected.size > 0 && (
            <button
              onClick={async () => {
                const confirmed = window.confirm(
                  isZh
                    ? `确定删除 ${selected.size} 本书？此操作不可撤销。`
                    : `Delete ${selected.size} book(s)? This cannot be undone.`,
                )
                if (!confirmed) return
                setDeleting(selected.size)
                try {
                  await Promise.all([...selected].map((id) => deleteBook(id)))
                  setSelected(new Set())
                  refresh()
                } catch {
                  // Error handled by individual deleteBook calls
                } finally {
                  setDeleting(null)
                }
              }}
              disabled={deleting !== null}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
              title={isZh ? '删除选中' : 'Delete selected'}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {isZh ? '删除' : 'Delete'}
            </button>
          )}
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
              {editingBookId === book.id ? (
                <BookEditDialog
                  book={book}
                  onSave={() => { setEditingBookId(null); refresh() }}
                  onCancel={() => setEditingBookId(null)}
                />
              ) : (
                <>
                  <BookCard book={book} onSelect={toggleSelect} />
                  {/* Edit button */}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setEditingBookId(book.id) }}
                    className="absolute top-2 right-[4.5rem] z-10 flex h-6 w-6 items-center justify-center rounded-md border-2 border-muted-foreground/40 bg-card/80 text-transparent group-hover/card:text-muted-foreground transition-all shadow-sm hover:border-primary hover:text-primary"
                    title={isZh ? '编辑' : 'Edit'}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {/* Delete button */}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); handleDeleteSingle(book) }}
                    disabled={deleting === book.id}
                    className="absolute top-2 right-10 z-10 flex h-6 w-6 items-center justify-center rounded-md border-2 border-muted-foreground/40 bg-card/80 text-transparent group-hover/card:text-destructive/70 transition-all shadow-sm hover:border-destructive hover:text-destructive disabled:opacity-50"
                    title={isZh ? '删除' : 'Delete'}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                  {/* Checkbox */}
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
                </>
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
            <span className="w-8 shrink-0" /> {/* cover thumbnail column */}
            <button
              onClick={() => toggleSort('title')}
              className="flex items-center gap-1 flex-1 group/th hover:text-foreground transition-colors"
            >
              {isZh ? '书名' : 'Title'}
              <SortIcon field="title" />
            </button>
            <button
              onClick={() => toggleSort('authors')}
              className="w-32 hidden sm:block text-right group/th hover:text-foreground transition-colors"
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
            {/* Pipeline column */}
            <span className="w-36 hidden xl:block text-center">
              Pipeline
            </span>
            {/* Actions column */}
            <span className="w-16 shrink-0 text-center">
              {isZh ? '操作' : 'Actions'}
            </span>
          </div>

          {/* Table rows */}
          {displayBooks.map((book, idx) => {
            const isChecked = selected.has(book.id)
            return (
            <div
              key={book.id}
              role="button"
              tabIndex={0}
              onClick={() => toggleSelect(book)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleSelect(book) }}
              className={cn(
                'flex items-center gap-4 w-full px-4 py-2.5 text-left transition-colors cursor-pointer',
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

              {/* Cover thumbnail */}
              <div className="w-8 h-10 shrink-0 rounded overflow-hidden bg-muted">
                {book.coverImage?.sizes?.thumbnail?.url ? (
                  <img
                    src={book.coverImage.sizes.thumbnail.url}
                    alt={book.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <BookOpen className="h-3.5 w-3.5 text-muted-foreground/40" />
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <div className="min-w-0">
                  <span className="text-sm text-foreground truncate block">
                    {book.title}
                  </span>
                </div>
              </div>

              <span className="w-32 hidden sm:block text-xs text-muted-foreground truncate text-right">
                {book.authors || '—'}
              </span>

              <span className="w-16 hidden md:block text-xs text-muted-foreground text-right tabular-nums">
                {book.metadata?.pageCount || '—'}
              </span>

              <span className="w-16 hidden lg:block text-xs text-muted-foreground text-right tabular-nums">
                {book.chunkCount || '—'}
              </span>

              {/* Pipeline progress pills */}
              <div className="w-36 hidden xl:flex justify-center shrink-0">
                <PipelineProgress pipeline={book.pipeline} />
              </div>

              {/* Actions */}
              <div className="w-16 shrink-0 flex items-center justify-center gap-1">
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setEditingBookId(book.id) }}
                  className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                  title={isZh ? '编辑' : 'Edit'}
                >
                  <Pencil className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleDeleteSingle(book) }}
                  disabled={deleting === book.id}
                  className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                  title={isZh ? '删除' : 'Delete'}
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            </div>
          )})}
        </div>
      )}
    </SidebarLayout>
  )
}
