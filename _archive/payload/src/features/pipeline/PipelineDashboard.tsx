'use client'

/**
 * Pipeline Dashboard — 流水线管理 (v5 — Tree sidebar + Stage panel)
 *
 * 左 sidebar：分类 → 子分类 → 书本（树形目录，和 Library sidebar 风格一致）
 * 右 sidebar：Pipeline 步骤导航 + 操作按钮
 * 主区域：总览或单步详情
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Zap,
  Loader2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  BookOpen,
  AlertCircle,
  Search,
  ArrowDown,
  Eye,
  FileText,
  Layers,
  HardDrive,
  Sparkles,
  List,
  LayoutDashboard,
  Building2,
  Home,
  ChevronRight,
  ChevronDown,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import ResizeHandle from '@/features/shared/ResizeHandle'
import { triggerPipeline, fetchPipelinePreview } from '@/features/pipeline/api'
import type { TaskType, PipelinePreview, StagePreview } from '@/features/pipeline/types'

// ═══════════════════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════════════════

type NavKey = 'overview' | string

const CATEGORY_CONFIG: Record<string, { labelZh: string; icon: React.ElementType; color: string }> = {
  textbook:    { labelZh: '教材',     icon: BookOpen,  color: 'text-blue-400' },
  ecdev:       { labelZh: '经济发展', icon: Building2, color: 'text-emerald-400' },
  real_estate: { labelZh: '房地产',   icon: Home,      color: 'text-amber-400' },
}

const STAGE_META: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  pdf_parse:   { icon: FileText,  color: 'text-blue-400',    bg: 'bg-blue-500/10' },
  chunk_build: { icon: Layers,    color: 'text-amber-400',   bg: 'bg-amber-500/10' },
  store:       { icon: HardDrive, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  vector:      { icon: Sparkles,  color: 'text-purple-400',  bg: 'bg-purple-500/10' },
  fts:         { icon: Search,    color: 'text-cyan-400',    bg: 'bg-cyan-500/10' },
  toc:         { icon: List,      color: 'text-pink-400',    bg: 'bg-pink-500/10' },
}

const STATUS_ICON: Record<string, { icon: React.ElementType; color: string }> = {
  done:    { icon: CheckCircle2, color: 'text-emerald-400' },
  pending: { icon: Clock,        color: 'text-muted-foreground' },
  missing: { icon: XCircle,      color: 'text-red-400' },
  error:   { icon: AlertCircle,  color: 'text-red-400' },
}

interface BookOption {
  id: number
  title: string
  engineBookId: string
  status: string
  category: string
  subcategory: string | null
}

const PIPELINE_ACTIONS: { type: TaskType; label: string; icon: React.ElementType; desc: string }[] = [
  { type: 'ingest',  label: '重新处理',     icon: Play,      desc: '重新解析 MinerU 输出并建索引' },
  { type: 'reindex', label: '重建索引',     icon: RefreshCw, desc: '重新构建 FTS + 向量索引' },
  { type: 'full',    label: '完整 Pipeline', icon: Zap,      desc: '执行完整处理流程' },
]

const CATEGORY_ORDER = ['textbook', 'ecdev', 'real_estate']

// ═══════════════════════════════════════════════════════════════════════════
// Tree data structure
// ═══════════════════════════════════════════════════════════════════════════

interface TreeCategory {
  key: string
  label: string
  icon: React.ElementType
  color: string
  subcategories: TreeSubcategory[]
  /** Books without subcategory */
  books: BookOption[]
}

interface TreeSubcategory {
  key: string
  label: string
  books: BookOption[]
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════════════════

export default function PipelineDashboard() {
  // ── Book state ──────────────────────────────────────────────────────────
  const [books, setBooks] = useState<BookOption[]>([])
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null)
  const [bookSearch, setBookSearch] = useState('')
  const [loading, setLoading] = useState(true)

  // ── Sidebar width state ──────────────────────────────────────────────────
  const [sb1Width, setSb1Width] = useState(240)
  const [sb2Width, setSb2Width] = useState(200)

  // ── Collapse state for categories & subcategories ──────────────────────
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set(CATEGORY_ORDER))
  const [expandedSubs, setExpandedSubs] = useState<Set<string>>(new Set())

  // ── Pipeline preview state ──────────────────────────────────────────────
  const [preview, setPreview] = useState<PipelinePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [activeNav, setActiveNav] = useState<NavKey>('overview')

  // ── Feedback state ──────────────────────────────────────────────────────
  const [actionFeedback, setActionFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
  const [runningAction, setRunningAction] = useState<string | null>(null)

  // ── Fetch books ─────────────────────────────────────────────────────────
  const fetchBooks = useCallback(async () => {
    try {
      const resp = await fetch('/api/books?limit=500&sort=title', { credentials: 'include' })
      if (!resp.ok) return
      const data = await resp.json()
      setBooks(
        (data.docs || []).map((b: any) => ({
          id: b.id,
          title: b.title,
          engineBookId: b.engineBookId || '',
          status: b.status || 'pending',
          category: b.category || 'textbook',
          subcategory: b.subcategory || null,
        }))
      )
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    fetchBooks().finally(() => setLoading(false))
  }, [fetchBooks])

  const selectedBook = useMemo(
    () => books.find((b) => b.id === selectedBookId) ?? null,
    [books, selectedBookId],
  )

  // ── Build tree from books ─────────────────────────────────────────────
  const tree = useMemo(() => {
    const q = bookSearch.toLowerCase().trim()
    const filtered = q
      ? books.filter((b) =>
          b.title.toLowerCase().includes(q) ||
          b.engineBookId.toLowerCase().includes(q) ||
          (b.subcategory?.toLowerCase().includes(q) ?? false)
        )
      : books

    const catMap: Record<string, { books: BookOption[]; subMap: Record<string, BookOption[]> }> = {}

    for (const book of filtered) {
      const cat = book.category || 'textbook'
      if (!catMap[cat]) catMap[cat] = { books: [], subMap: {} }

      if (book.subcategory) {
        if (!catMap[cat].subMap[book.subcategory]) catMap[cat].subMap[book.subcategory] = []
        catMap[cat].subMap[book.subcategory].push(book)
      } else {
        catMap[cat].books.push(book)
      }
    }

    const result: TreeCategory[] = []
    for (const catKey of CATEGORY_ORDER) {
      const cfg = CATEGORY_CONFIG[catKey]
      const data = catMap[catKey]
      if (!cfg || !data) continue
      if (data.books.length === 0 && Object.keys(data.subMap).length === 0) continue

      const subcategories: TreeSubcategory[] = Object.entries(data.subMap)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([sub, subBooks]) => ({
          key: `${catKey}::${sub}`,
          label: sub,
          books: subBooks.sort((a, b) => a.title.localeCompare(b.title)),
        }))

      result.push({
        key: catKey,
        label: cfg.labelZh,
        icon: cfg.icon,
        color: cfg.color,
        subcategories,
        books: data.books.sort((a, b) => a.title.localeCompare(b.title)),
      })
    }

    // Handle unknown categories
    for (const [catKey, data] of Object.entries(catMap)) {
      if (CATEGORY_ORDER.includes(catKey)) continue
      if (data.books.length === 0 && Object.keys(data.subMap).length === 0) continue
      result.push({
        key: catKey,
        label: catKey,
        icon: BookOpen,
        color: 'text-muted-foreground',
        subcategories: [],
        books: [...data.books, ...Object.values(data.subMap).flat()].sort((a, b) => a.title.localeCompare(b.title)),
      })
    }

    return result
  }, [books, bookSearch])

  const totalFiltered = useMemo(
    () => tree.reduce((sum, cat) => sum + cat.books.length + cat.subcategories.reduce((s, sub) => s + sub.books.length, 0), 0),
    [tree],
  )

  // ── Toggle helpers ────────────────────────────────────────────────────
  const toggleCat = (key: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const toggleSub = (key: string) => {
    setExpandedSubs((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  // Auto-expand when searching
  useEffect(() => {
    if (bookSearch.trim()) {
      setExpandedCats(new Set(CATEGORY_ORDER))
      setExpandedSubs(new Set(tree.flatMap((c) => c.subcategories.map((s) => s.key))))
    }
  }, [bookSearch, tree])

  // Auto-expand the category/sub of the selected book
  useEffect(() => {
    if (selectedBook) {
      setExpandedCats((prev) => new Set([...prev, selectedBook.category]))
      if (selectedBook.subcategory) {
        setExpandedSubs((prev) => new Set([...prev, `${selectedBook.category}::${selectedBook.subcategory}`]))
      }
    }
  }, [selectedBook])

  // ── Fetch pipeline preview when book changes ──────────────────────────
  useEffect(() => {
    if (!selectedBook?.engineBookId) {
      setPreview(null)
      setActiveNav('overview')
      return
    }
    let cancelled = false
    setPreviewLoading(true)
    fetchPipelinePreview(selectedBook.engineBookId)
      .then((data) => { if (!cancelled) { setPreview(data); setActiveNav('overview') } })
      .catch(() => { if (!cancelled) setPreview(null) })
      .finally(() => { if (!cancelled) setPreviewLoading(false) })
    return () => { cancelled = true }
  }, [selectedBook?.engineBookId])

  // ── Action handlers ─────────────────────────────────────────────────────
  const handlePipelineAction = async (taskType: TaskType) => {
    if (!selectedBookId) return
    setRunningAction(taskType)
    setActionFeedback({ type: 'info', message: `正在启动 ${taskType}...` })
    try {
      const task = await triggerPipeline({ bookId: selectedBookId, taskType })
      setActionFeedback({ type: 'success', message: `✅ 任务已创建 (#${task.id})` })
      setTimeout(() => setActionFeedback(null), 4000)
    } catch (err) {
      setActionFeedback({ type: 'error', message: `❌ 启动失败: ${err}` })
      setTimeout(() => setActionFeedback(null), 5000)
    } finally {
      setRunningAction(null)
    }
  }

  const activeStage = useMemo(
    () => preview?.stages.find((s) => s.stage === activeNav) ?? null,
    [preview, activeNav],
  )

  // ═══════════════════════════════════════════════════════════════════════
  //   Render
  // ═══════════════════════════════════════════════════════════════════════
  return (
    <div className="flex h-full">
      {/* ═══ SIDEBAR 1: Category → Subcategory → Books ═══ */}
      <aside
        className="shrink-0 border-r border-border bg-card/50 flex flex-col"
        style={{ width: sb1Width }}
      >
        {/* Header */}
        <div className="shrink-0 px-3 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-amber-400" />
            <span className="text-xs font-semibold text-foreground">Pipeline</span>
          </div>
        </div>

        {/* Search */}
        <div className="shrink-0 px-2 py-2 border-b border-border/50">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <input
              type="text"
              value={bookSearch}
              onChange={(e) => setBookSearch(e.target.value)}
              placeholder="搜索书名..."
              className="w-full h-7 pl-7 pr-2 rounded-md border border-input bg-background text-xs
                         focus:outline-none focus:ring-1 focus:ring-ring/30 placeholder:text-muted-foreground"
            />
          </div>
        </div>

        {/* Tree navigation */}
        <nav className="flex-1 overflow-y-auto py-1 px-1.5">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : tree.length === 0 ? (
            <div className="py-6 text-center text-xs text-muted-foreground">
              {bookSearch ? '无匹配结果' : '暂无书本'}
            </div>
          ) : (
            tree.map((cat) => {
              const CatIcon = cat.icon
              const isExpanded = expandedCats.has(cat.key)
              const catBookCount = cat.books.length + cat.subcategories.reduce((s, sub) => s + sub.books.length, 0)

              return (
                <div key={cat.key} className="mb-1">
                  {/* Category header */}
                  <button
                    type="button"
                    onClick={() => toggleCat(cat.key)}
                    className="flex items-center gap-2 w-full rounded-md px-2.5 py-2 text-left transition-colors hover:bg-secondary"
                  >
                    {isExpanded
                      ? <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
                      : <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />}
                    <CatIcon className={cn('h-3.5 w-3.5 shrink-0', cat.color)} />
                    <span className="text-xs font-semibold text-foreground flex-1 truncate">{cat.label}</span>
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                      {catBookCount}
                    </span>
                  </button>

                  {/* Expanded children */}
                  {isExpanded && (
                    <div className="ml-3">
                      {/* Direct books (no subcategory) */}
                      {cat.books.map((book) => (
                        <BookItem
                          key={book.id}
                          book={book}
                          isActive={selectedBookId === book.id}
                          onClick={() => setSelectedBookId(book.id)}
                        />
                      ))}

                      {/* Subcategories */}
                      {cat.subcategories.map((sub) => {
                        const isSubExpanded = expandedSubs.has(sub.key)
                        return (
                          <div key={sub.key} className="mb-0.5">
                            <button
                              type="button"
                              onClick={() => toggleSub(sub.key)}
                              className="flex items-center gap-1.5 w-full rounded-md px-2 py-1.5 text-left transition-colors hover:bg-secondary"
                            >
                              {isSubExpanded
                                ? <ChevronDown className="h-2.5 w-2.5 shrink-0 text-muted-foreground" />
                                : <ChevronRight className="h-2.5 w-2.5 shrink-0 text-muted-foreground" />}
                              <span className="text-[11px] font-medium text-muted-foreground flex-1 truncate">{sub.label}</span>
                              <span className="text-[9px] text-muted-foreground">{sub.books.length}</span>
                            </button>
                            {isSubExpanded && (
                              <div className="ml-3">
                                {sub.books.map((book) => (
                                  <BookItem
                                    key={book.id}
                                    book={book}
                                    isActive={selectedBookId === book.id}
                                    onClick={() => setSelectedBookId(book.id)}
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </nav>

        {/* Footer */}
        {!loading && (
          <div className="shrink-0 px-3 py-2 border-t border-border text-[10px] text-muted-foreground">
            共 {totalFiltered} 本{bookSearch && ` (筛选自 ${books.length})`}
          </div>
        )}
      </aside>

      <ResizeHandle width={sb1Width} onResize={setSb1Width} min={180} max={400} />

      {/* ═══ SIDEBAR 2: Pipeline Stages + Actions ═══ */}
      <aside
        className="shrink-0 border-r border-border bg-card flex flex-col"
        style={{ width: sb2Width }}
      >
        {/* Header */}
        <div className="shrink-0 px-3 py-3 border-b border-border">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground truncate">
            {selectedBook ? selectedBook.title : '步骤'}
          </p>
        </div>

        {/* Stage Nav */}
        <div className="flex-1 overflow-y-auto py-1 px-1.5">
          {/* Overview */}
          <button
            type="button"
            onClick={() => setActiveNav('overview')}
            className={cn(
              'flex items-center gap-2 w-full h-8 px-2.5 rounded-md text-xs font-medium transition-colors mb-0.5',
              activeNav === 'overview'
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
            )}
          >
            <LayoutDashboard className="h-3.5 w-3.5 shrink-0" />
            总览
          </button>

          {preview ? (
            <>
              <div className="my-1.5 mx-2 border-t border-border" />
              {preview.stages.map((stage, idx) => {
                const meta = STAGE_META[stage.stage] || { icon: Zap, color: 'text-muted-foreground', bg: 'bg-muted' }
                const Icon = meta.icon
                const statusCfg = STATUS_ICON[stage.status] || STATUS_ICON.pending
                const StatusIcon = statusCfg.icon
                const isActive = activeNav === stage.stage

                return (
                  <button
                    key={stage.stage}
                    type="button"
                    onClick={() => setActiveNav(stage.stage)}
                    className={cn(
                      'flex items-center gap-1.5 w-full h-8 px-2.5 rounded-md text-xs transition-colors mb-0.5',
                      isActive
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-foreground hover:bg-secondary',
                    )}
                  >
                    <span className="text-[9px] text-muted-foreground font-mono w-3.5 shrink-0">#{idx + 1}</span>
                    <Icon className={cn('h-3 w-3 shrink-0', isActive ? 'text-primary' : meta.color)} />
                    <span className="truncate flex-1">{stage.label}</span>
                    <StatusIcon className={cn('h-3 w-3 shrink-0', statusCfg.color)} />
                  </button>
                )
              })}
            </>
          ) : !selectedBook ? (
            <p className="px-2.5 py-4 text-xs text-muted-foreground">← 选择书本</p>
          ) : previewLoading ? (
            <div className="flex items-center gap-2 px-2.5 py-4 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> 加载中...
            </div>
          ) : null}
        </div>

        {/* Actions */}
        <div className="shrink-0 border-t border-border p-1.5 space-y-0.5">
          {PIPELINE_ACTIONS.map((action) => {
            const Icon = action.icon
            const isThis = runningAction === action.type
            return (
              <button
                key={action.type}
                onClick={() => handlePipelineAction(action.type)}
                disabled={!selectedBookId || !!runningAction}
                title={action.desc}
                className={cn(
                  'flex items-center gap-2 w-full h-7 px-2.5 rounded-md text-[11px] font-medium transition-colors',
                  'hover:bg-secondary',
                  (!selectedBookId || !!runningAction) && 'opacity-40 cursor-not-allowed',
                  isThis && 'bg-primary/10 text-primary',
                )}
              >
                {isThis ? <Loader2 className="h-3 w-3 animate-spin" /> : <Icon className="h-3 w-3 shrink-0" />}
                {action.label}
              </button>
            )
          })}
        </div>
      </aside>

      <ResizeHandle width={sb2Width} onResize={setSb2Width} min={160} max={300} />

      {/* ═══ MAIN CONTENT ═══ */}
      <main className="flex-1 min-w-0 overflow-y-auto p-6">
        {/* Feedback toast */}
        {actionFeedback && (
          <div className={cn(
            'mb-4 px-4 py-3 rounded-lg text-xs border animate-in fade-in duration-200',
            actionFeedback.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
            : actionFeedback.type === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400'
            : 'bg-blue-500/10 border-blue-500/20 text-blue-400',
          )}>
            {actionFeedback.message}
          </div>
        )}

        {/* No book selected */}
        {!selectedBook && !loading && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
              <Zap className="h-7 w-7 text-muted-foreground" />
            </div>
            <h2 className="text-sm font-semibold text-foreground mb-1">Pipeline 管理</h2>
            <p className="text-xs text-muted-foreground text-center max-w-xs">
              从左侧目录选择一本书，查看其处理流水线的每一步输入与输出
            </p>
          </div>
        )}

        {/* Loading */}
        {previewLoading && !preview && selectedBook && (
          <div className="flex items-center justify-center h-64 gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            加载 Pipeline 数据...
          </div>
        )}

        {/* Overview */}
        {preview && activeNav === 'overview' && (
          <OverviewPage preview={preview} onSelectStage={setActiveNav} />
        )}

        {/* Stage detail */}
        {preview && activeStage && (
          <StageDetailPage stage={activeStage} stageIndex={preview.stages.indexOf(activeStage)} />
        )}
      </main>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// BookItem — single book in tree
// ═══════════════════════════════════════════════════════════════════════════

function BookItem({ book, isActive, onClick }: { book: BookOption; isActive: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 w-full rounded-md px-2 py-1.5 text-left transition-colors mb-0.5',
        isActive
          ? 'bg-primary/10 text-primary font-medium'
          : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
      )}
    >
      <BookOpen className={cn('h-3 w-3 shrink-0', isActive ? 'text-primary' : 'text-muted-foreground')} />
      <span className="text-[11px] flex-1 truncate">{book.title}</span>
      {book.status === 'indexed' && (
        <CheckCircle2 className="h-2.5 w-2.5 shrink-0 text-emerald-400" />
      )}
    </button>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Overview Page
// ═══════════════════════════════════════════════════════════════════════════

function OverviewPage({ preview, onSelectStage }: { preview: PipelinePreview; onSelectStage: (s: string) => void }) {
  const doneCount = preview.stages.filter((s) => s.status === 'done').length
  const totalCount = preview.stages.length

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-lg font-bold text-foreground mb-1">{preview.title}</h1>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <code className="font-mono">{preview.bookId}</code>
          <span>·</span>
          <span className={preview.status === 'indexed' ? 'text-emerald-400 font-medium' : ''}>
            {preview.status}
          </span>
          <span>·</span>
          <span>{doneCount}/{totalCount} 步骤完成</span>
        </div>
        <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500"
            style={{ width: `${(doneCount / totalCount) * 100}%` }}
          />
        </div>
      </div>

      <div className="space-y-0">
        {preview.stages.map((stage, idx) => {
          const meta = STAGE_META[stage.stage] || { icon: Zap, color: 'text-muted-foreground', bg: 'bg-muted' }
          const Icon = meta.icon
          const isDone = stage.status === 'done'
          const statusCfg = STATUS_ICON[stage.status] || STATUS_ICON.pending
          const StatusIcon = statusCfg.icon

          return (
            <div key={stage.stage}>
              <button
                type="button"
                onClick={() => onSelectStage(stage.stage)}
                className={cn(
                  'w-full flex items-center gap-4 px-5 py-4 rounded-xl border transition-all text-left group',
                  'hover:border-primary/30 hover:shadow-sm hover:bg-card',
                  isDone ? 'border-border bg-card' : 'border-dashed border-border/50 bg-card/30',
                )}
              >
                <div className={cn('flex items-center justify-center w-10 h-10 rounded-xl shrink-0', isDone ? 'bg-emerald-500/10' : meta.bg)}>
                  <Icon className={cn('h-5 w-5', isDone ? 'text-emerald-400' : meta.color)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-mono text-muted-foreground">#{idx + 1}</span>
                    <span className="text-sm font-semibold text-foreground">{stage.label}</span>
                    <StatusIcon className={cn('h-3.5 w-3.5', statusCfg.color)} />
                  </div>
                  <div className="text-[11px] text-muted-foreground truncate">
                    {stage.input.description} → {stage.output.description}
                  </div>
                </div>
                <div className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Eye className="h-4 w-4 text-muted-foreground" />
                </div>
              </button>
              {idx < preview.stages.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowDown className="h-4 w-4 text-border" />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Stage Detail Page
// ═══════════════════════════════════════════════════════════════════════════

function StageDetailPage({ stage, stageIndex }: { stage: StagePreview; stageIndex: number }) {
  const meta = STAGE_META[stage.stage] || { icon: Zap, color: 'text-muted-foreground', bg: 'bg-muted' }
  const Icon = meta.icon
  const isDone = stage.status === 'done'
  const statusCfg = STATUS_ICON[stage.status] || STATUS_ICON.pending
  const StatusIcon = statusCfg.icon

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-4 mb-6">
        <div className={cn('flex items-center justify-center w-12 h-12 rounded-xl shrink-0', isDone ? 'bg-emerald-500/10' : meta.bg)}>
          <Icon className={cn('h-6 w-6', isDone ? 'text-emerald-400' : meta.color)} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-muted-foreground">#{stageIndex + 1}</span>
            <h1 className="text-lg font-bold text-foreground">{stage.label}</h1>
            <span className={cn('inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full', statusCfg.color, isDone ? 'bg-emerald-500/10' : 'bg-muted')}>
              <StatusIcon className="h-3 w-3" />
              {stage.status}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{stage.labelEn}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DataPanel title="输入 (Input)" type={stage.input.type} description={stage.input.description} preview={stage.input.preview} direction="in" />
        <DataPanel title="输出 (Output)" type={stage.output.type} description={stage.output.description} preview={stage.output.preview} direction="out" />
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// DataPanel
// ═══════════════════════════════════════════════════════════════════════════

function DataPanel({ title, type, description, preview, direction }: {
  title: string; type: string; description: string; preview?: Record<string, unknown>[]; direction: 'in' | 'out'
}) {
  const isIn = direction === 'in'
  return (
    <div className={cn('rounded-xl border bg-card overflow-hidden', isIn ? 'border-blue-500/20' : 'border-emerald-500/20')}>
      <div className={cn('px-4 py-3 border-b flex items-center gap-2', isIn ? 'bg-blue-500/5 border-blue-500/10' : 'bg-emerald-500/5 border-emerald-500/10')}>
        <span className={cn('text-xs font-semibold uppercase tracking-wider', isIn ? 'text-blue-400' : 'text-emerald-400')}>{title}</span>
        <span className="ml-auto text-[10px] font-mono text-muted-foreground">{type}</span>
      </div>
      <div className="px-4 py-3 border-b border-border/50">
        <p className="text-sm text-foreground">{description}</p>
      </div>
      {preview && preview.length > 0 ? (
        <div className="p-4 space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">样本数据 ({preview.length} 条)</p>
          {preview.map((item, i) => (
            <PreviewCard key={i} data={item} />
          ))}
        </div>
      ) : (
        <div className="px-4 py-6 text-center text-xs text-muted-foreground">暂无预览数据</div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// PreviewCard
// ═══════════════════════════════════════════════════════════════════════════

function PreviewCard({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v != null && v !== '')
  if (entries.length === 0) return null
  return (
    <div className="rounded-lg border border-border/50 bg-background/50 overflow-hidden">
      {entries.map(([key, value]) => (
        <div key={key} className="flex px-3 py-1.5 border-b border-border/30 last:border-0">
          <span className="text-[10px] text-muted-foreground font-medium w-24 shrink-0 py-0.5">{key}</span>
          <span className="text-[11px] text-foreground flex-1 break-all whitespace-pre-wrap py-0.5">
            {typeof value === 'string' && value.length > 200 ? `${value.slice(0, 200)}...` : String(value)}
          </span>
        </div>
      ))}
    </div>
  )
}
