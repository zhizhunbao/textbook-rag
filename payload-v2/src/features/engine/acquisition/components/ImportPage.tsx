/**
 * ImportPage — Acquisition module main page with 5-tab layout + SidebarLayout.
 *
 * Layout: SidebarLayout (shared book sidebar) wraps a tab-bar + content area.
 * Tab order follows the data pipeline flow:
 *   ① Import   — File upload + URL import (no book selection needed)
 *   ② Files    — Payload Media files for the selected book
 *   ③ Parse    — MinerU parse output (content_list.json) with sub-tabs
 *   ④ Pipeline — Ingestion pipeline status + task queue
 *   ⑤ Vectors  — ChromaDB vector stats + sampling
 *
 * Uses SidebarLayout + useBookSidebar (same as readers/LibraryPage,
 * question_gen/QuestionsPage). No hand-written sidebar.
 *
 * Ref: AQ-10 — ImportPage 5-Tab upgrade
 */

'use client'

import { Suspense, useMemo, useState, useCallback, useEffect, useRef } from 'react'
import {
  Download,
  FileText,
  Activity,
  Upload,
  Link2,
  Layers,
  BookOpen,
  Trash2,
  RefreshCw,
  Globe,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import { useBooks, useBookSidebar, buildCategoryIcons } from '@/features/shared/books'
import { SidebarLayout } from '@/features/shared/components/SidebarLayout'
import { useQueryState } from '@/features/shared/hooks/useQueryState'
import type { ImportTab } from '../types'
import { deleteBookWithCleanup } from '../api'
import FileUploadCard from './FileUploadCard'
import UrlImportCard from './UrlImportCard'
import MediaTab from './MediaTab'
import PipelineTab from './PipelineTab'
import SourcesTab from './SourcesTab'


// ============================================================
// Tab config
// ============================================================
interface TabConfig {
  key: ImportTab
  label: string
  labelFr: string
  icon: React.ElementType
}

const TABS: TabConfig[] = [
  { key: 'sources',  label: 'Sources',  labelFr: '数据源',  icon: Globe },
  { key: 'import',   label: 'Import',   labelFr: '导入',   icon: Download },
  { key: 'files',    label: 'Files',    labelFr: '文件',   icon: FileText },
  { key: 'pipeline', label: 'Pipeline', labelFr: '管线',   icon: Activity },
]

// ============================================================
// Component
// ============================================================
export default function ImportPage() {
  return (
    <Suspense>
      <ImportPageInner />
    </Suspense>
  )
}

function ImportPageInner() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'
  const [activeTab, setActiveTab] = useQueryState('tab', 'files') as [ImportTab, (v: string) => void]
  const [filter, setFilter] = useQueryState('filter', 'all')
  const [deleting, setDeleting] = useState(false)

  // ── Book data (shared hooks) ──
  const { books, loading, error, refetch } = useBooks()

  // ── One-time metadata backfill from engine ──
  const syncedRef = useRef(false)
  useEffect(() => {
    if (syncedRef.current || books.length === 0) return
    // Only sync books missing pageCount or fileSize
    const missing = books.filter((b) => b.pageCount === 0 && b.fileSize === 0 && b.status === 'indexed')
    if (missing.length === 0) { syncedRef.current = true; return }
    syncedRef.current = true
    ;(async () => {
      try {
        const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'
        const res = await fetch(`${ENGINE_URL}/engine/books`)
        if (!res.ok) return
        const engineBooks: Array<{ book_id: string; page_count?: number; chunk_count?: number; pdf_size_bytes?: number }> = await res.json()
        const engineMap = new Map(engineBooks.map((eb) => [eb.book_id, eb]))
        let patched = 0
        for (const book of missing) {
          const eb = engineMap.get(book.book_id)
          if (!eb || (!eb.page_count && !eb.pdf_size_bytes)) continue
          try {
            await fetch(`/api/books/${book.id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({
                metadata: { pageCount: eb.page_count ?? 0, fileSize: eb.pdf_size_bytes ?? 0 },
                chunkCount: eb.chunk_count ?? 0,
              }),
            })
            patched++
          } catch { /* best-effort */ }
        }
        if (patched > 0) refetch()
      } catch (e) {
        console.warn('Metadata backfill failed:', e)
      }
    })()
  }, [books])

  const booksForSidebar = useMemo(() =>
    books.map((b) => ({
      ...b,
      category: b.category || 'textbooks',
      subcategory: b.subcategory || '',
    })),
    [books],
  )

  // ── Dynamic category icons from actual book data ──
  const categoryIcons = useMemo(() => {
    const cats = [...new Set(booksForSidebar.map((b) => b.category || 'textbooks'))]
    return buildCategoryIcons(cats)
  }, [booksForSidebar])

  const { sidebarItems: rawSidebarItems, filterBooks } = useBookSidebar(booksForSidebar, {
    mode: 'by-book',
    isFr,
    allLabel: isFr ? '全部' : 'All',
    allIcon: <Layers className="h-4 w-4 shrink-0" />,
    bookIcon: <BookOpen className="h-3.5 w-3.5 shrink-0" />,
    categoryIcons,
  })

  // ── Filter books by sidebar selection ──
  const filteredBooks = useMemo(() => filterBooks(filter), [filter, filterBooks])

  // ── Selected book (when sidebar filter is a specific book) ──
  const selectedBook = useMemo(() => {
    if (!filter.startsWith('book::')) return null
    const bookId = filter.slice(6) // "book::{book_id}" → book_id string
    return books.find((b) => b.book_id === bookId) ?? null
  }, [filter, books])

  // ── Delete handler (works for any book) ──
  const handleDeleteBook = useCallback(async (book: { id: number; book_id: string; title: string }) => {
    const confirmed = window.confirm(
      isFr
        ? `确定删除「${book.title}」？\n将同时清除 Engine 侧数据（向量、MinerU 输出）。此操作不可撤销。`
        : `Delete "${book.title}"?\nThis will also clean up Engine-side data (vectors, MinerU output). This cannot be undone.`,
    )
    if (!confirmed) return

    setDeleting(true)
    try {
      await deleteBookWithCleanup(book.id, book.book_id)
      // If the deleted book was selected, reset to "all"
      if (filter === `book::${book.book_id}`) {
        setFilter('all')
      }
      refetch()
    } catch (err) {
      console.error('Delete failed:', err)
      window.alert(
        isFr
          ? `删除失败: ${err instanceof Error ? err.message : String(err)}`
          : `Delete failed: ${err instanceof Error ? err.message : String(err)}`,
      )
    } finally {
      setDeleting(false)
    }
  }, [isFr, refetch, setFilter, filter])

  // ── Add delete action to book-level sidebar items ──
  const sidebarItems = useMemo(() =>
    rawSidebarItems.map((item) => {
      if (!item.key.startsWith('book::')) return item
      const bookId = item.key.slice(6)
      const book = books.find((b) => b.book_id === bookId)
      if (!book) return item
      return {
        ...item,
        onAction: () => handleDeleteBook(book),
      }
    }),
    [rawSidebarItems, books, handleDeleteBook],
  )


  return (
    <SidebarLayout
      title={isFr ? '数据源管理' : 'Data Sources'}
      icon={<Globe className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={setFilter}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {isFr ? `共 ${books.length} 本` : `${books.length} total`}
        </p>
      }
      loading={loading}
      loadingText={isFr ? '正在加载...' : 'Loading...'}
      error={error?.message ?? null}
      onRetry={refetch}
      subtitle={isFr
        ? '数据源 → 导入 → 文件 → 管线'
        : 'Sources → Import → Files → Pipeline'}
      toolbar={
        <div className="flex items-center gap-2">
          {/* Delete button — visible when a specific book is selected */}
          {selectedBook && (
            <button
              type="button"
              onClick={() => handleDeleteBook(selectedBook)}
              disabled={deleting}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors',
                'text-destructive hover:bg-destructive/10',
                'disabled:opacity-50 disabled:cursor-not-allowed',
              )}
              title={isFr ? '删除此书' : 'Delete this book'}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {isFr ? '删除' : 'Delete'}
            </button>
          )}
          {/* Refresh button */}
          <button
            type="button"
            onClick={refetch}
            className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            title={isFr ? '刷新' : 'Refresh'}
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      }
    >
      {/* ── Tab bar ── */}
      <div className="flex items-center gap-1 border-b border-border -mx-6 px-6 mb-4 -mt-2">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors relative',
                isActive
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {isFr ? tab.labelFr : tab.label}
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t" />
              )}
            </button>
          )
        })}
      </div>

      {/* ── Tab content ── */}
      {activeTab === 'sources' && <SourcesTab onBooksRefresh={refetch} />}
      {activeTab === 'import' && <ImportTabContent onBooksRefresh={refetch} />}
      {activeTab === 'files' && <MediaTab books={filteredBooks} filter={filter} onBooksRefresh={refetch} />}
      {activeTab === 'pipeline' && <PipelineTab books={filteredBooks} filter={filter} onBooksRefresh={refetch} />}
    </SidebarLayout>
  )
}

// ============================================================
// Import Tab — 2-column: File Upload + URL Import
// ============================================================
function ImportTabContent({ onBooksRefresh }: { onBooksRefresh: () => void }) {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  const handleComplete = () => {
    // Auto-refresh sidebar book list after upload/import
    onBooksRefresh()
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* File upload column */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <Upload className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {isFr ? '文件上传' : 'File Upload'}
            </span>
          </div>
          <FileUploadCard onUploadComplete={handleComplete} />
        </div>

        {/* URL import column */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <Link2 className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {isFr ? 'URL 导入' : 'URL Import'}
            </span>
          </div>
          <UrlImportCard onImportComplete={handleComplete} />
        </div>
      </div>
    </div>
  )
}
