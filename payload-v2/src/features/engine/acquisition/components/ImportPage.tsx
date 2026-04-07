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

import { Suspense, useMemo } from 'react'
import {
  Download,
  FileText,
  Activity,
  Upload,
  Link2,
  Layers,
  BookOpen,
  Building2,
  Home,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import { useBooks, useBookSidebar } from '@/features/shared/books'
import { SidebarLayout } from '@/features/shared/components/SidebarLayout'
import { useQueryState } from '@/features/shared/hooks/useQueryState'
import type { ImportTab } from '../types'
import FileUploadCard from './FileUploadCard'
import UrlImportCard from './UrlImportCard'
import MediaTab from './MediaTab'
import PipelineTab from './PipelineTab'

// ============================================================
// Category icons (same as LibraryPage)
// ============================================================
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  textbook:    <BookOpen  className={cn('h-4 w-4 shrink-0', 'text-blue-400')} />,
  ecdev:       <Building2 className={cn('h-4 w-4 shrink-0', 'text-emerald-400')} />,
  real_estate: <Home      className={cn('h-4 w-4 shrink-0', 'text-amber-400')} />,
}

// ============================================================
// Tab config
// ============================================================
interface TabConfig {
  key: ImportTab
  label: string
  labelZh: string
  icon: React.ElementType
}

const TABS: TabConfig[] = [
  { key: 'import',   label: 'Import',   labelZh: '导入',   icon: Download },
  { key: 'files',    label: 'Files',    labelZh: '文件',   icon: FileText },
  { key: 'pipeline', label: 'Pipeline', labelZh: '管线',   icon: Activity },
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
  const isZh = locale === 'zh'
  const [activeTab, setActiveTab] = useQueryState('tab', 'import') as [ImportTab, (v: string) => void]
  const [filter, setFilter] = useQueryState('filter', 'all')

  // ── Book data (shared hooks — same as LibraryPage) ──
  const { books, loading, error, refetch } = useBooks()

  const booksForSidebar = useMemo(() =>
    books.map((b) => ({
      ...b,
      category: b.category || 'textbook',
      subcategory: b.subcategory || '',
    })),
    [books],
  )

  const { sidebarItems, filterBooks } = useBookSidebar(booksForSidebar, {
    mode: 'by-book',
    isZh,
    allLabel: isZh ? '全部' : 'All',
    allIcon: <Layers className="h-4 w-4 shrink-0" />,
    bookIcon: <BookOpen className="h-3.5 w-3.5 shrink-0" />,
    categoryIcons: CATEGORY_ICONS,
  })

  // ── Filter books by sidebar selection ──
  const filteredBooks = useMemo(() => filterBooks(filter), [filter, filterBooks])

  return (
    <SidebarLayout
      title={isZh ? '数据导入' : 'Data Import'}
      icon={<Download className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={setFilter}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {isZh ? `共 ${books.length} 本` : `${books.length} total`}
        </p>
      }
      loading={loading}
      loadingText={isZh ? '正在加载...' : 'Loading...'}
      error={error?.message ?? null}
      onRetry={refetch}
      subtitle={isZh
        ? '上传 → 文件 → 管线'
        : 'Upload → Files → Pipeline'}
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
              {isZh ? tab.labelZh : tab.label}
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t" />
              )}
            </button>
          )
        })}
      </div>

      {/* ── Tab content ── */}
      {activeTab === 'import' && <ImportTabContent />}
      {activeTab === 'files' && <MediaTab books={filteredBooks} filter={filter} />}
      {activeTab === 'pipeline' && <PipelineTab books={filteredBooks} filter={filter} onBooksRefresh={refetch} />}
    </SidebarLayout>
  )
}

// ============================================================
// Import Tab — 2-column: File Upload + URL Import
// ============================================================
function ImportTabContent() {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  const handleComplete = () => {
    // Future: trigger list reload / show notification
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* File upload column */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <Upload className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {isZh ? '文件上传' : 'File Upload'}
            </span>
          </div>
          <FileUploadCard onUploadComplete={handleComplete} />
        </div>

        {/* URL import column */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <Link2 className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {isZh ? 'URL 导入' : 'URL Import'}
            </span>
          </div>
          <UrlImportCard onImportComplete={handleComplete} />
        </div>
      </div>
    </div>
  )
}

