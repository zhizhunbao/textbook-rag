/**
 * MediaTab — Unified book browser with card/table dual-view.
 *
 * Merged from: AQ-04 MediaTab + LibraryPage.
 * Now the single place to browse, search, edit, delete, and select books.
 *
 * Features:
 *  - Card and Table views with sort/search
 *  - Multi-select → "New Chat" footer
 *  - Inline edit (BookEditDialog)
 *  - Per-row delete
 *  - Pipeline progress pills
 *  - PDF origin/layout links
 */

'use client'

import { useState, useMemo, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  HardDrive,
  FileText,
  Eye,
  Layers,
  ExternalLink,
  LayoutGrid,
  List,
  Search,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  Hash,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  FileDown,
  CheckSquare,
  Square,
  MessageSquarePlus,
  Pencil,
  Trash2,
  BookOpen,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import type { BookBase, BookStatus, PipelineInfo } from '@/features/shared/books'
import { PipelineProgress } from '@/features/engine/readers/components/StatusBadge'
import BookEditDialog from '@/features/engine/readers/components/BookEditDialog'
import type { LibraryBook } from '@/features/engine/readers/types'
import { deleteBook } from '@/features/engine/readers/api'

// ============================================================
// Constants
// ============================================================
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Props
// ============================================================
interface MediaTabProps {
  books: BookBase[]
  filter: string
  /** Called after a destructive action (delete/edit) to refresh book list. */
  onBooksRefresh?: () => void
}

// ============================================================
// Types
// ============================================================
type ViewMode = 'cards' | 'table'
type SortField = 'title' | 'status' | 'pages' | 'size' | 'authors' | 'chunks'
type SortDir = 'asc' | 'desc'

// ============================================================
// Helpers
// ============================================================

function titleToGradient(title: string): string {
  let hash = 0
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash)
  }
  const h1 = Math.abs(hash) % 360
  const h2 = (h1 + 40) % 360
  return `linear-gradient(135deg, hsl(${h1}, 45%, 25%), hsl(${h2}, 55%, 18%))`
}

function titleInitials(title: string): string {
  return title
    .split(/[\s_\-]+/)
    .filter((w) => w.length > 0)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
}

function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Status config — using "Ready" instead of "Indexed" for the Files context. */
const STATUS_CONFIG: Record<BookStatus, { icon: React.ElementType; color: string; label: string; labelFr: string }> = {
  indexed: { icon: CheckCircle2, color: 'text-emerald-400', label: 'Ready', labelFr: '已就绪' },
  processing: { icon: Loader2, color: 'text-amber-400', label: 'Processing', labelFr: '处理中' },
  pending: { icon: Clock, color: 'text-muted-foreground', label: 'Pending', labelFr: '待处理' },
  error: { icon: AlertTriangle, color: 'text-red-400', label: 'Error', labelFr: '错误' },
}

function compareBooks(a: BookBase, b: BookBase, field: SortField, dir: SortDir): number {
  let cmp = 0
  switch (field) {
    case 'title': cmp = a.title.localeCompare(b.title); break
    case 'authors': cmp = a.authors.localeCompare(b.authors); break
    case 'pages': cmp = a.pageCount - b.pageCount; break
    case 'size': cmp = a.fileSize - b.fileSize; break
    case 'chunks': cmp = (a.chunk_count ?? 0) - (b.chunk_count ?? 0); break
    case 'status': {
      const order = { indexed: 0, processing: 1, pending: 2, error: 3 }
      cmp = (order[a.status] ?? 9) - (order[b.status] ?? 9)
      break
    }
  }
  return dir === 'asc' ? cmp : -cmp
}

/** Full-field fuzzy search */
function fuzzyMatch(book: BookBase, query: string): boolean {
  if (!query) return true
  const q = query.toLowerCase()
  return (
    book.title.toLowerCase().includes(q) ||
    book.authors.toLowerCase().includes(q) ||
    book.book_id.toLowerCase().includes(q) ||
    (book.category ?? '').toLowerCase().includes(q) ||
    (book.subcategory ?? '').toLowerCase().includes(q) ||
    book.status.toLowerCase().includes(q)
  )
}

// ============================================================
// Default column widths (px)
// ============================================================
const DEFAULT_COLS = {
  title: 240,
  author: 130,
  category: 100,
  subcategory: 100,
  chunks: 70,
  status: 90,
  pages: 60,
  size: 80,
  pipeline: 120,
  actions: 90,
}

// ============================================================
// useColumnResize — lightweight drag-to-resize hook
// ============================================================
function useColumnResize(initial: Record<string, number>) {
  const [widths, setWidths] = useState(initial)
  const dragRef = useRef<{ col: string; startX: number; startW: number } | null>(null)

  const onMouseDown = useCallback((col: string) => (e: React.MouseEvent) => {
    e.preventDefault()
    dragRef.current = { col, startX: e.clientX, startW: widths[col] }

    const onMouseMove = (ev: MouseEvent) => {
      if (!dragRef.current) return
      const delta = ev.clientX - dragRef.current.startX
      const newW = Math.max(40, dragRef.current.startW + delta)
      setWidths((prev) => ({ ...prev, [dragRef.current!.col]: newW }))
    }

    const onMouseUp = () => {
      dragRef.current = null
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [widths])

  return { widths, onMouseDown }
}

// ============================================================
// Component
// ============================================================
export default function MediaTab({ books, filter, onBooksRefresh }: MediaTabProps) {
  const router = useRouter()
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [localSearch, setLocalSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('title')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const { widths, onMouseDown } = useColumnResize(DEFAULT_COLS)

  // ── Multi-select state ──
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [deleting, setDeleting] = useState<number | null>(null)
  const [editingBookId, setEditingBookId] = useState<number | null>(null)

  const toggleSelect = (book: BookBase) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(book.id)) next.delete(book.id)
      else next.add(book.id)
      return next
    })
  }

  // ── Delete handler ──
  const handleDeleteSingle = useCallback(async (book: BookBase) => {
    const confirmed = window.confirm(
      isFr
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
      onBooksRefresh?.()
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setDeleting(null)
    }
  }, [isFr, onBooksRefresh])

  // ── Batch delete ──
  const handleBatchDelete = useCallback(async () => {
    const confirmed = window.confirm(
      isFr
        ? `确定删除 ${selected.size} 本书？此操作不可撤销。`
        : `Delete ${selected.size} book(s)? This cannot be undone.`,
    )
    if (!confirmed) return
    try {
      await Promise.all([...selected].map((id) => deleteBook(id)))
      setSelected(new Set())
      onBooksRefresh?.()
    } catch {
      // Error handled by individual deleteBook calls
    }
  }, [selected, isFr, onBooksRefresh])

  // ── Start new chat with selected books ──
  const startNewChat = useCallback(() => {
    if (selected.size === 0) return
    // Pass selected Payload IDs via URL params — ChatPage will read and scope the session
    const bookParams = [...selected].join(',')
    router.push(`/chat?books=${bookParams}`)
  }, [selected, router])

  // ── Edit save handler ──
  const handleEditSave = useCallback(() => {
    setEditingBookId(null)
    onBooksRefresh?.()
  }, [onBooksRefresh])

  // Local search + sort
  const displayBooks = useMemo(() => {
    let filtered = books
    if (localSearch.trim()) {
      filtered = filtered.filter((b) => fuzzyMatch(b, localSearch.trim()))
    }
    return [...filtered].sort((a, b) => compareBooks(a, b, sortField, sortDir))
  }, [books, localSearch, sortField, sortDir])

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

  /** Resize handle at RIGHT edge of each column */
  const ResizeGrip = ({ col }: { col: string }) => (
    <div
      onMouseDown={onMouseDown(col)}
      className="absolute right-0 top-1 bottom-1 w-[3px] cursor-col-resize rounded-full
                 bg-border hover:bg-primary/60 active:bg-primary transition-colors z-10"
    />
  )

  // ==========================================================
  // Empty state
  // ==========================================================
  if (books.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
          <HardDrive className="h-7 w-7 text-muted-foreground" />
        </div>
        <h3 className="text-sm font-semibold text-foreground mb-1">
          {isFr ? '暂无书籍' : 'No books'}
        </h3>
        <p className="text-xs text-muted-foreground text-center max-w-xs">
          {isFr
            ? '在「导入」标签页上传 PDF 即可开始。'
            : 'Upload PDFs via the Import tab to get started.'}
        </p>
      </div>
    )
  }

  // ==========================================================
  // Main view
  // ==========================================================
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0 space-y-4">
        {/* ── Toolbar ── */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              placeholder={isFr ? '搜索书名、作者、分类...' : 'Search title, author, category...'}
              className="w-full h-8 pl-9 pr-3 rounded-md border border-input bg-background text-xs text-foreground
                         placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/30 transition-colors"
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

          {/* Selected count + batch actions */}
          {selected.size > 0 && (
            <>
              <button
                type="button"
                onClick={startNewChat}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <MessageSquarePlus className="h-3.5 w-3.5" />
                {isFr ? `开始对话 (${selected.size})` : `Chat (${selected.size})`}
              </button>
              <button
                type="button"
                onClick={handleBatchDelete}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                {isFr ? `删除 (${selected.size})` : `Delete (${selected.size})`}
              </button>
            </>
          )}

          <span className="text-[10px] tabular-nums text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {displayBooks.length}
          </span>

          <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5">
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              className={cn(
                'p-1.5 rounded transition-colors',
                viewMode === 'cards' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={cn(
                'p-1.5 rounded transition-colors',
                viewMode === 'table' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <List className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Empty search */}
        {displayBooks.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16">
            <h3 className="text-sm font-semibold text-foreground mb-1">
              {isFr ? '未找到匹配结果' : 'No matches found'}
            </h3>
            <p className="text-xs text-muted-foreground">
              {isFr ? '尝试不同的关键词' : 'Try different keywords'}
            </p>
          </div>
        )}

        {/* ── Card view ── */}
        {displayBooks.length > 0 && viewMode === 'cards' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {displayBooks.map((book) => (
              <PdfBookCard
                key={book.id}
                book={book}
                isFr={isFr}
                isSelected={selected.has(book.id)}
                onSelect={() => toggleSelect(book)}
                onEdit={() => setEditingBookId(book.id)}
                onDelete={() => handleDeleteSingle(book)}
                deleting={deleting === book.id}
              />
            ))}
          </div>
        )}

        {/* ── Table view ── */}
        {displayBooks.length > 0 && viewMode === 'table' && (
          <div className="rounded-lg border border-border overflow-hidden overflow-x-auto">
            {/* Header */}
            <div className="flex items-center min-w-max bg-muted/50 text-[11px] font-medium text-muted-foreground tracking-wider border-b border-border select-none">
              {/* Checkbox spacer */}
              <span className="w-8 shrink-0 px-2" />
              {/* Icon spacer */}
              <span className="w-8 shrink-0 px-1" />

              {/* Title */}
              <button
                onClick={() => toggleSort('title')}
                className="relative shrink-0 flex items-center gap-1 px-2 py-2 group/th hover:text-foreground transition-colors"
                style={{ width: widths.title }}
              >
                {isFr ? '书名' : 'Title'}
                <SortIcon field="title" />
                <ResizeGrip col="title" />
              </button>

              {/* Author */}
              <button
                onClick={() => toggleSort('authors')}
                className="relative shrink-0 flex items-center gap-1 px-2 py-2 group/th hover:text-foreground transition-colors"
                style={{ width: widths.author }}
              >
                {isFr ? '作者' : 'Author'}
                <SortIcon field="authors" />
                <ResizeGrip col="author" />
              </button>

              {/* Category */}
              <span className="relative shrink-0 flex items-center px-2 py-2" style={{ width: widths.category }}>
                {isFr ? '分类' : 'Category'}
                <ResizeGrip col="category" />
              </span>

              {/* Subcategory */}
              <span className="relative shrink-0 flex items-center px-2 py-2" style={{ width: widths.subcategory }}>
                {isFr ? '子分类' : 'Subcategory'}
                <ResizeGrip col="subcategory" />
              </span>

              {/* Chunks */}
              <button
                onClick={() => toggleSort('chunks')}
                className="relative shrink-0 flex items-center gap-1 justify-end px-2 py-2 group/th hover:text-foreground transition-colors"
                style={{ width: widths.chunks }}
              >
                Chunks
                <SortIcon field="chunks" />
                <ResizeGrip col="chunks" />
              </button>

              {/* Pages */}
              <button
                onClick={() => toggleSort('pages')}
                className="relative shrink-0 flex items-center gap-1 justify-end px-2 py-2 group/th hover:text-foreground transition-colors"
                style={{ width: widths.pages }}
              >
                {isFr ? '页数' : 'Pages'}
                <SortIcon field="pages" />
                <ResizeGrip col="pages" />
              </button>

              {/* Size */}
              <button
                onClick={() => toggleSort('size')}
                className="relative shrink-0 flex items-center gap-1 justify-end px-2 py-2 group/th hover:text-foreground transition-colors"
                style={{ width: widths.size }}
              >
                {isFr ? '大小' : 'Size'}
                <SortIcon field="size" />
                <ResizeGrip col="size" />
              </button>

              {/* Status */}
              <button
                onClick={() => toggleSort('status')}
                className="relative shrink-0 flex items-center gap-1 px-2 py-2 group/th hover:text-foreground transition-colors"
                style={{ width: widths.status }}
              >
                {isFr ? '状态' : 'Status'}
                <SortIcon field="status" />
                <ResizeGrip col="status" />
              </button>

              {/* Pipeline */}
              <span className="relative shrink-0 flex items-center justify-center px-2 py-2" style={{ width: widths.pipeline }}>
                Pipeline
                <ResizeGrip col="pipeline" />
              </span>

              {/* Actions */}
              <span className="relative shrink-0 flex items-center justify-center px-2 py-2" style={{ width: widths.actions }}>
                {isFr ? '操作' : 'Actions'}
              </span>
            </div>

            {/* Rows */}
            {displayBooks.map((book, idx) => {
              const pdfUrl = `${ENGINE_URL}/engine/books/${book.book_id}/pdf`
              const layoutUrl = `${pdfUrl}?variant=layout`
              const st = STATUS_CONFIG[book.status]
              const StatusIcon = st.icon
              const isChecked = selected.has(book.id)
              const pipeline = book.pipeline ?? { parse: 'pending' as const, ingest: 'pending' as const }

              // Inline edit mode
              if (editingBookId === book.id) {
                return (
                  <div key={book.id} className={cn('px-4 py-3', idx > 0 && 'border-t border-border')}>
                    <BookEditDialog
                      book={{
                        id: book.id,
                        engineBookId: book.book_id,
                        title: book.title,
                        authors: book.authors || null,
                        isbn: null,
                        coverImage: null,
                        category: book.category || 'textbooks',
                        subcategory: book.subcategory || null,
                        status: book.status,
                        chunkCount: book.chunk_count ?? null,
                        metadata: { pageCount: book.pageCount },
                        pipeline,
                        createdAt: book.createdAt || '',
                        updatedAt: '',
                      } as LibraryBook}
                      onSave={handleEditSave}
                      onCancel={() => setEditingBookId(null)}
                    />
                  </div>
                )
              }

              return (
                <div
                  key={book.id}
                  className={cn(
                    'flex items-center min-w-max transition-colors',
                    isChecked ? 'bg-primary/5 hover:bg-primary/10' : 'hover:bg-secondary/50',
                    idx > 0 && 'border-t border-border',
                  )}
                >
                  {/* Checkbox */}
                  <div className="w-8 shrink-0 flex items-center justify-center px-2">
                    <button
                      type="button"
                      onClick={() => toggleSelect(book)}
                      className={cn(
                        'flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors',
                        isChecked
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-muted-foreground/30 hover:border-muted-foreground/60',
                      )}
                    >
                      {isChecked && <CheckSquare className="h-3 w-3" />}
                    </button>
                  </div>

                  {/* Icon */}
                  <div className="w-8 shrink-0 flex items-center justify-center px-1 py-2.5">
                    <div className="w-6 h-6 rounded bg-red-500/10 flex items-center justify-center">
                      <FileText className="h-3 w-3 text-red-400" />
                    </div>
                  </div>

                  {/* Title */}
                  <div className="shrink-0 px-2 py-2.5 min-w-0 overflow-hidden" style={{ width: widths.title }}>
                    <span className="text-sm text-foreground truncate block">{book.title}</span>
                  </div>

                  {/* Author */}
                  <span className="shrink-0 px-2 py-2.5 text-xs text-muted-foreground truncate" style={{ width: widths.author }}>
                    {book.authors || '—'}
                  </span>

                  {/* Category */}
                  <span className="shrink-0 px-2 py-2.5 text-xs text-muted-foreground truncate" style={{ width: widths.category }}>
                    {book.category || '—'}
                  </span>

                  {/* Subcategory */}
                  <span className="shrink-0 px-2 py-2.5 text-xs text-muted-foreground truncate" style={{ width: widths.subcategory }}>
                    {book.subcategory || '—'}
                  </span>

                  {/* Chunks */}
                  <span className="shrink-0 px-2 py-2.5 text-xs text-muted-foreground text-right tabular-nums" style={{ width: widths.chunks }}>
                    {book.chunk_count || '—'}
                  </span>

                  {/* Pages */}
                  <span className="shrink-0 px-2 py-2.5 text-xs text-muted-foreground text-right tabular-nums" style={{ width: widths.pages }}>
                    {book.pageCount || '—'}
                  </span>

                  {/* Size */}
                  <span className="shrink-0 px-2 py-2.5 text-xs text-muted-foreground text-right tabular-nums" style={{ width: widths.size }}>
                    {formatFileSize(book.fileSize)}
                  </span>

                  {/* Status */}
                  <div className="shrink-0 px-2 py-2.5 flex items-center gap-1.5" style={{ width: widths.status }}>
                    <StatusIcon className={cn('h-3.5 w-3.5', st.color, book.status === 'processing' && 'animate-spin')} />
                    <span className={cn('text-[11px]', st.color)}>
                      {isFr ? st.labelFr : st.label}
                    </span>
                  </div>

                  {/* Pipeline */}
                  <div className="shrink-0 px-2 py-2.5 flex justify-center" style={{ width: widths.pipeline }}>
                    <PipelineProgress pipeline={pipeline} />
                  </div>

                  {/* Actions */}
                  <div
                    className="px-2 py-2.5 shrink-0 flex items-center justify-center gap-1"
                    style={{ width: widths.actions }}
                  >
                    {/* Origin PDF */}
                    <a
                      href={pdfUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                      title={isFr ? '原始 PDF' : 'Origin PDF'}
                    >
                      <Eye className="h-3 w-3" />
                    </a>
                    {/* Layout PDF */}
                    {book.status === 'indexed' && (
                      <a
                        href={layoutUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-blue-400 hover:bg-blue-400/10 transition-colors"
                        title={isFr ? '布局 PDF' : 'Layout PDF'}
                      >
                        <Layers className="h-3 w-3" />
                      </a>
                    )}
                    {/* Edit */}
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setEditingBookId(book.id) }}
                      className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                      title={isFr ? '编辑' : 'Edit'}
                    >
                      <Pencil className="h-3 w-3" />
                    </button>
                    {/* Delete */}
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleDeleteSingle(book) }}
                      disabled={deleting === book.id}
                      className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
                      title={isFr ? '删除' : 'Delete'}
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

    </div>
  )
}

// ============================================================
// CoverImage — engine cover with gradient fallback
// ============================================================
function CoverImage({
  bookId,
  title,
  status,
  className,
}: {
  bookId: string
  title: string
  status: BookStatus
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  const handleError = useCallback(() => setFailed(true), [])

  const coverUrl = status === 'indexed' && !failed
    ? `${ENGINE_URL}/engine/books/${bookId}/cover`
    : null

  if (coverUrl) {
    return (
      <img
        src={coverUrl}
        alt={title}
        onError={handleError}
        className={cn('w-full object-cover', className)}
      />
    )
  }

  return (
    <div
      className={cn('w-full flex items-center justify-center', className)}
      style={{ background: titleToGradient(title) }}
    >
      <span className="text-3xl font-bold text-white/25 select-none tracking-widest">
        {titleInitials(title)}
      </span>
    </div>
  )
}

// ============================================================
// PdfBookCard — card view item (enhanced with select/edit/delete)
// ============================================================
function PdfBookCard({
  book,
  isFr,
  isSelected,
  onSelect,
  onEdit,
  onDelete,
  deleting,
}: {
  book: BookBase
  isFr: boolean
  isSelected: boolean
  onSelect: () => void
  onEdit: () => void
  onDelete: () => void
  deleting: boolean
}) {
  const pdfUrl = `${ENGINE_URL}/engine/books/${book.book_id}/pdf`
  const layoutUrl = `${pdfUrl}?variant=layout`
  const st = STATUS_CONFIG[book.status]
  const StatusIcon = st.icon

  return (
    <div className={cn(
      'relative w-full text-left group rounded-xl border bg-card',
      'hover:bg-secondary/50 transition-all duration-200 hover:shadow-md overflow-hidden',
      isSelected ? 'border-primary/50 ring-1 ring-primary/20' : 'border-border hover:border-primary/20',
    )}>
      {/* Cover */}
      <div className="relative w-full h-28 overflow-hidden">
        <CoverImage bookId={book.book_id} title={book.title} status={book.status} className="h-28 group-hover:scale-105 transition-transform duration-300" />
        <div className="absolute inset-0 bg-gradient-to-t from-card/90 via-transparent to-transparent" />

        {/* Status badge */}
        <div className="absolute top-2 right-2 flex items-center gap-1 rounded-md bg-card/60 backdrop-blur-sm px-1.5 py-0.5">
          <StatusIcon className={cn('h-3 w-3', st.color, book.status === 'processing' && 'animate-spin')} />
          <span className={cn('text-[10px] font-medium', st.color)}>
            {isFr ? st.labelFr : st.label}
          </span>
        </div>

        {/* Checkbox */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onSelect() }}
          className={cn(
            'absolute top-2 left-2 z-10 flex h-6 w-6 items-center justify-center rounded-md border-2 transition-all shadow-sm',
            isSelected
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-muted-foreground/40 bg-card/80 text-transparent group-hover:text-muted-foreground',
          )}
        >
          {isSelected ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
        </button>
      </div>

      {/* Content */}
      <div className="p-3 pt-2">
        <h3 className="text-sm font-semibold text-foreground line-clamp-2 mb-0.5 group-hover:text-primary transition-colors">
          {book.title}
        </h3>
        {book.authors && (
          <p className="text-[11px] text-muted-foreground truncate mb-1">{book.authors}</p>
        )}

        {/* Stats */}
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground mb-2">
          {book.pageCount > 0 && (
            <span className="flex items-center gap-1">
              <Hash className="h-3 w-3" />
              {book.pageCount} {isFr ? '页' : 'pages'}
            </span>
          )}
          {book.fileSize > 0 && (
            <span className="flex items-center gap-1">
              <FileDown className="h-3 w-3" />
              {formatFileSize(book.fileSize)}
            </span>
          )}
          {(book.chunk_count ?? 0) > 0 && (
            <span className="flex items-center gap-1">
              <Layers className="h-3 w-3" />
              {book.chunk_count} chunks
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="pt-2 border-t border-border flex items-center gap-2">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            <Eye className="h-3.5 w-3.5" />
            PDF
          </a>
          {book.status === 'indexed' && (
            <a
              href={layoutUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground hover:underline"
            >
              <Layers className="h-3.5 w-3.5" />
              Layout
            </a>
          )}
          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onEdit() }}
              className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors opacity-0 group-hover:opacity-100"
              title={isFr ? '编辑' : 'Edit'}
            >
              <Pencil className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onDelete() }}
              disabled={deleting}
              className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50"
              title={isFr ? '删除' : 'Delete'}
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
