/**
 * QuestionsPage — unified question bank: browse + generate + evaluate.
 *
 * Route: /engine/question_gen
 *
 * Three-column layout (matching EvaluationPage):
 *   [Books sidebar]  |  [PDF preview + Questions list (center)]  |  [Evaluation panel (right)]
 *   Chapters appear as checkable items under the selected book in the sidebar.
 *   Toolbar integrates: count input, generate button, clear, refresh, view toggle.
 *   Evaluation panel shows question depth + self-assessment scores synced with Q list.
 */

'use client'

import { useState, useEffect, useCallback, useMemo, useRef, Suspense } from 'react'
import ResizeHandle from '@/features/shared/ResizeHandle'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/esm/Page/TextLayer.css'
import {
  MessageSquare, BookOpen, ThumbsUp,
  RefreshCw, Layers, Trash2, Sparkles,
  Loader2, AlertCircle, Hash, Zap, FileText, X,
  BarChart3, RotateCcw, ChevronRight, GripVertical, Clock,
  PanelLeftClose, PanelLeftOpen,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type SidebarItem, type ViewMode } from '@/features/shared/components/SidebarLayout'
import { useBooks, useBookSidebar, buildCategoryIcons } from '@/features/shared/books'
import { useQueryState } from '@/features/shared/hooks/useQueryState'
import type { TocEntry } from '@/features/shared/books'
import type { Question } from '../types'
import { fetchQuestions, likeQuestion, deleteQuestion, deleteAllQuestions, generateQuestions, saveQuestionToPayload, updateQuestionEval } from '../api'
import { assessQuestionQuality } from '@/features/engine/evaluation/api'

// ============================================================
// Constants
// ============================================================

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`

/** Badge config: maps question type to icon + gradient colours */
const TYPE_CONFIG: Record<string, { icon: typeof Zap; gradient: string; text: string }> = {
  analytical: { icon: Zap, gradient: 'from-violet-500/20 to-purple-500/10', text: 'text-violet-400' },
  conceptual: { icon: Hash, gradient: 'from-cyan-500/20 to-blue-500/10', text: 'text-cyan-400' },
  factual: { icon: BookOpen, gradient: 'from-emerald-500/20 to-green-500/10', text: 'text-emerald-400' },
  applied: { icon: Sparkles, gradient: 'from-amber-500/20 to-orange-500/10', text: 'text-amber-400' },
}

// ============================================================
// Evaluation types + constants
// ============================================================

/** Depth label → display info. */
const DEPTH_META: Record<string, { label: string; labelFr: string; color: string }> = {
  surface: { label: 'Surface', labelFr: 'Superficiel', color: 'text-amber-400' },
  understanding: { label: 'Understanding', labelFr: 'Compréhension', color: 'text-blue-400' },
  synthesis: { label: 'Synthesis', labelFr: 'Synthèse', color: 'text-emerald-400' },
}

type Grade = 'excellent' | 'good' | 'fair' | 'poor' | 'none'

function getGrade(score: number | null | undefined): Grade {
  if (score == null) return 'none'
  if (score >= 0.85) return 'excellent'
  if (score >= 0.7) return 'good'
  if (score >= 0.5) return 'fair'
  return 'poor'
}

const GRADE_STYLES: Record<Grade, { label: string; labelFr: string; text: string; bg: string; border: string }> = {
  excellent: { label: 'Excellent', labelFr: 'Excellent', text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  good: { label: 'Good', labelFr: 'Bon', text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  fair: { label: 'Fair', labelFr: 'Moyen', text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  poor: { label: 'Poor', labelFr: 'Faible', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  none: { label: '—', labelFr: '—', text: 'text-zinc-500', bg: 'bg-zinc-500/10', border: 'border-zinc-500/30' },
}

/** Per-question evaluation state. */
interface QuestionEvalState {
  status: 'idle' | 'loading' | 'done' | 'error'
  depth?: string | null       // surface / understanding / synthesis
  depthScore?: number | null   // 1-5 raw
  depthNormalized?: number | null // 0-1
  reasoning?: string | null
  error?: string
}

// ============================================================
// Component
// ============================================================

export default function QuestionsPage() {
  return (
    <Suspense>
      <QuestionsPageInner />
    </Suspense>
  )
}

function QuestionsPageInner() {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // ==========================================================
  // State
  // ==========================================================
  const [questions, setQuestions] = useState<Question[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useQueryState('filter', 'all')
  const [viewMode, setViewMode] = useQueryState('view', 'cards') as [ViewMode, (v: string) => void]
  const [likingIds, setLikingIds] = useState<Set<number>>(new Set())
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set())
  const [clearingAll, setClearingAll] = useState(false)

  // Generation state
  const [genCount, setGenCount] = useState(5)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)

  // Chapter state (merged into sidebar)
  const [selectedChapterKeys, setSelectedChapterKeys] = useState<Set<string>>(new Set())
  const [chapters, setChapters] = useState<TocEntry[]>([])
  const [chaptersLoading, setChaptersLoading] = useState(false)

  // PDF preview state
  const [previewPage, setPreviewPage] = useState<number | null>(null)
  const [showPreview, setShowPreview] = useState(true)
  const [pdfWidth, setPdfWidth] = useState(480)
  const [numPdfPages, setNumPdfPages] = useState(0)

  // Evaluation state
  const [evalStates, setEvalStates] = useState<Record<number, QuestionEvalState>>({})
  const [autoEvalRunning, setAutoEvalRunning] = useState(false)
  const [evalProgress, setEvalProgress] = useState({ done: 0, total: 0 })
  const abortEvalRef = useRef(false)
  const [evalPanelWidth, setEvalPanelWidth] = useState(360)

  // Scroll sync refs
  const leftPanelRef = useRef<HTMLDivElement>(null)
  const rightPanelRef = useRef<HTMLDivElement>(null)
  const isSyncingRef = useRef(false)

  // ==========================================================
  // Hooks
  // ==========================================================
  const { books, loading: booksLoading } = useBooks({ status: 'indexed' })

  // Build sidebar with question counts per book
  const countMap = useMemo(() => {
    const map = new Map<string, number>()
    for (const q of questions) {
      map.set(q.bookId, (map.get(q.bookId) || 0) + 1)
    }
    return map
  }, [questions])

  // Dynamic category icons from actual book data
  const categoryIcons = useMemo(() => {
    const cats = [...new Set(books.map((b) => b.category || 'textbooks'))]
    return buildCategoryIcons(cats, 'h-3.5 w-3.5')
  }, [books])

  const { sidebarItems: baseSidebarItems } = useBookSidebar(books, {
    mode: 'by-book',
    countMap,
    isZh,
    allLabel: isZh ? 'Toutes les questions' : 'All Questions',
    allIcon: <Layers className="h-4 w-4 text-cyan-400" />,
    bookIcon: <BookOpen className="h-3.5 w-3.5" />,
    categoryIcons,
  })

  // ==========================================================
  // Derived state
  // ==========================================================
  const selectedBookId = filter.startsWith('book::') ? filter.slice(6) : null
  const isSingleBook = selectedBookId !== null

  // Target books for generation
  const targetBookIds = useMemo(() => {
    if (filter === 'all') return books.map((b) => b.book_id)
    if (isSingleBook) return [selectedBookId]
    if (filter.includes('::')) {
      const [cat, sub] = filter.split('::')
      return books
        .filter((b) => (b.category || 'textbooks') === cat && b.subcategory === sub)
        .map((b) => b.book_id)
    }
    return books
      .filter((b) => (b.category || 'textbooks') === filter)
      .map((b) => b.book_id)
  }, [filter, books, isSingleBook, selectedBookId])

  // ==========================================================
  // Merge chapters into sidebar items
  // ==========================================================

  // Fetch chapters when a single book is selected
  useEffect(() => {
    setSelectedChapterKeys(new Set())
    setChapters([])

    if (!isSingleBook || !selectedBookId) return

    setChaptersLoading(true)
    fetch(`${ENGINE}/engine/books/${selectedBookId}/toc`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data: TocEntry[]) => setChapters(data))
      .catch(() => setChapters([]))
      .finally(() => setChaptersLoading(false))
  }, [isSingleBook, selectedBookId])

  // Show PDF when book is selected; jump to chapter page when checked
  useEffect(() => {
    if (!isSingleBook || !selectedBookId) {
      setPreviewPage(null)
      return
    }

    setShowPreview(true)

    if (selectedChapterKeys.size > 0) {
      const tocId = Array.from(selectedChapterKeys)[0]
      const chapter = chapters.find((ch) => String(ch.id) === tocId)
      if (chapter?.pdf_page) {
        setPreviewPage(chapter.pdf_page)
      }
    } else {
      setPreviewPage(1)
    }
  }, [isSingleBook, selectedBookId, selectedChapterKeys, chapters])

  // Build final sidebar items
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    if (!isSingleBook || chapters.length === 0) return baseSidebarItems

    const bookKey = `book::${selectedBookId}`
    const bookIdx = baseSidebarItems.findIndex((item) => item.key === bookKey)
    if (bookIdx === -1) return baseSidebarItems

    const bookLevel = baseSidebarItems[bookIdx].indentLevel ?? 1
    const chapterLevel = (bookLevel + 1) as number

    const chapterItems: SidebarItem[] = chapters.map((ch) => ({
      key: `chapter::${ch.id}`,
      label: ch.number ? `${ch.number} ${ch.title}` : ch.title,
      indentLevel: chapterLevel,
      checkable: true,
      checked: selectedChapterKeys.has(String(ch.id)),
      icon: <Hash className="h-3 w-3 text-muted-foreground/50" />,
    }))

    const result = [...baseSidebarItems]
    result.splice(bookIdx + 1, 0, ...chapterItems)
    return result
  }, [baseSidebarItems, isSingleBook, selectedBookId, chapters, selectedChapterKeys])

  // ==========================================================
  // Data loading
  // ==========================================================
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchQuestions(200)
      setQuestions(data)

      // Hydrate evalStates from persisted evaluation data
      const hydrated: Record<number, QuestionEvalState> = {}
      for (const q of data) {
        if (q.evalDepth) {
          hydrated[q.id] = {
            status: 'done',
            depth: q.evalDepth,
            depthScore: q.evalScore ? q.evalScore * 5 : null,
            depthNormalized: q.evalScore,
            reasoning: q.evalReasoning,
          }
        }
      }
      if (Object.keys(hydrated).length > 0) {
        setEvalStates(prev => ({ ...prev, ...hydrated }))
      }
    } catch {
      setError(isZh ? 'Échec du chargement des questions' : 'Failed to load questions')
    } finally {
      setLoading(false)
    }
  }, [isZh])

  useEffect(() => { load() }, [load])

  // ==========================================================
  // Filtered questions
  // ==========================================================
  const displayQuestions = useMemo(() => {
    let filtered = questions
    if (filter === 'all') {
      // no book filter
    } else if (filter.startsWith('book::')) {
      const bookId = filter.slice(6)
      filtered = filtered.filter((q) => q.bookId === bookId)
    } else {
      const catBooks = books.filter((b) => {
        if (filter.includes('::')) {
          const [cat, sub] = filter.split('::')
          return (b.category || 'textbooks') === cat && b.subcategory === sub
        }
        return (b.category || 'textbooks') === filter
      })
      const catBookIds = new Set(catBooks.map((b) => b.book_id))
      if (catBookIds.size > 0) {
        filtered = filtered.filter((q) => catBookIds.has(q.bookId))
      }
    }

    // Further filter by selected chapter (page range)
    if (selectedChapterKeys.size > 0 && chapters.length > 0) {
      const tocId = Array.from(selectedChapterKeys)[0]
      const chIdx = chapters.findIndex((ch) => String(ch.id) === tocId)
      if (chIdx !== -1) {
        const ch = chapters[chIdx]
        const pStart = (ch.pdf_page ?? 1) - 1
        let pEnd = Infinity
        for (let j = chIdx + 1; j < chapters.length; j++) {
          const nxt = chapters[j]
          if (nxt.pdf_page && nxt.pdf_page > (ch.pdf_page ?? 1)) {
            pEnd = nxt.pdf_page - 1
            break
          }
        }
        filtered = filtered.filter((q) =>
          q.sourcePage != null && q.sourcePage >= pStart && q.sourcePage < pEnd
        )
      }
    }

    return filtered
  }, [questions, filter, books, selectedChapterKeys, chapters])

  // ==========================================================
  // Scroll synchronization
  // ==========================================================
  const handleLeftScroll = useCallback(() => {
    if (isSyncingRef.current || !rightPanelRef.current || !leftPanelRef.current) return
    isSyncingRef.current = true
    const left = leftPanelRef.current
    const right = rightPanelRef.current
    const ratio = left.scrollTop / (left.scrollHeight - left.clientHeight || 1)
    right.scrollTop = ratio * (right.scrollHeight - right.clientHeight || 1)
    requestAnimationFrame(() => { isSyncingRef.current = false })
  }, [])

  const handleRightScroll = useCallback(() => {
    if (isSyncingRef.current || !leftPanelRef.current || !rightPanelRef.current) return
    isSyncingRef.current = true
    const right = rightPanelRef.current
    const left = leftPanelRef.current
    const ratio = right.scrollTop / (right.scrollHeight - right.clientHeight || 1)
    left.scrollTop = ratio * (left.scrollHeight - left.clientHeight || 1)
    requestAnimationFrame(() => { isSyncingRef.current = false })
  }, [])

  // ==========================================================
  // Evaluation logic
  // ==========================================================

  /** Evaluate a single question's depth via engine API. */
  const evaluateQuestion = useCallback(async (questionId: number, questionText: string) => {
    setEvalStates(prev => ({ ...prev, [questionId]: { status: 'loading' } }))
    try {
      const result = await assessQuestionQuality(questionText)
      const normScore = result.score ? result.score / 5.0 : null
      setEvalStates(prev => ({
        ...prev,
        [questionId]: {
          status: 'done',
          depth: result.depth,
          depthScore: result.score,
          depthNormalized: normScore,
          reasoning: result.reasoning,
        },
      }))

      // Persist to Payload CMS
      if (result.depth && normScore != null) {
        updateQuestionEval(questionId, {
          evalDepth: result.depth,
          evalScore: normScore,
          evalReasoning: result.reasoning || '',
        }).catch(() => { })
      }
    } catch (err) {
      setEvalStates(prev => ({
        ...prev,
        [questionId]: {
          status: 'error',
          error: err instanceof Error ? err.message : String(err),
        },
      }))
    }
  }, [])

  /** Auto-evaluate all displayed questions sequentially. */
  const autoEvaluateAll = useCallback(async (qs: Question[]) => {
    abortEvalRef.current = false
    setAutoEvalRunning(true)
    setEvalProgress({ done: 0, total: qs.length })

    let doneCount = 0
    for (const q of qs) {
      if (abortEvalRef.current) break

      // Skip already evaluated
      const existing = evalStates[q.id]
      if (existing?.status === 'done') {
        doneCount++
        setEvalProgress({ done: doneCount, total: qs.length })
        continue
      }

      setEvalStates(prev => ({ ...prev, [q.id]: { status: 'loading' } }))
      try {
        const result = await assessQuestionQuality(q.question)
        const normScore = result.score ? result.score / 5.0 : null
        setEvalStates(prev => ({
          ...prev,
          [q.id]: {
            status: 'done',
            depth: result.depth,
            depthScore: result.score,
            depthNormalized: normScore,
            reasoning: result.reasoning,
          },
        }))
      } catch (err) {
        setEvalStates(prev => ({
          ...prev,
          [q.id]: {
            status: 'error',
            error: err instanceof Error ? err.message : String(err),
          },
        }))
      }

      doneCount++
      setEvalProgress({ done: doneCount, total: qs.length })
    }

    setAutoEvalRunning(false)
  }, [evalStates])

  // ==========================================================
  // Handlers
  // ==========================================================

  const handleFilterChange = useCallback((key: string) => {
    if (key.startsWith('chapter::')) {
      const chapterId = key.slice(9)
      setSelectedChapterKeys((prev) => {
        if (prev.has(chapterId)) return new Set()
        return new Set([chapterId])
      })
      return
    }
    setFilter(key)
  }, [])

  const handleLike = useCallback(async (id: number) => {
    const q = questions.find((q) => q.id === id)
    if (!q) return
    setLikingIds((p) => new Set(p).add(id))
    try {
      await likeQuestion(id, q.likes)
      setQuestions((qs) => qs.map((q) => (q.id === id ? { ...q, likes: q.likes + 1 } : q)))
    } finally {
      setLikingIds((p) => { const n = new Set(p); n.delete(id); return n })
    }
  }, [questions])

  const handleDelete = useCallback(async (id: number) => {
    setDeletingIds((p) => new Set(p).add(id))
    try {
      await deleteQuestion(id)
      setQuestions((qs) => qs.filter((q) => q.id !== id))
    } finally {
      setDeletingIds((p) => { const n = new Set(p); n.delete(id); return n })
    }
  }, [])

  const handleClearAll = useCallback(async () => {
    const idsToDelete = displayQuestions.map((q) => q.id)
    if (idsToDelete.length === 0) return
    setClearingAll(true)
    try {
      await deleteAllQuestions(idsToDelete)
      if (selectedBookId) {
        setQuestions((qs) => qs.filter((q) => q.bookId !== selectedBookId))
      } else {
        setQuestions([])
      }
    } finally {
      setClearingAll(false)
    }
  }, [selectedBookId, displayQuestions])

  const handleGenerate = useCallback(async () => {
    if (targetBookIds.length === 0) return
    setGenerating(true)
    setGenError(null)

    try {
      const category = !filter.startsWith('book::') && filter !== 'all' && !filter.includes('::')
        ? filter : undefined

      let pageStart: number | undefined
      let pageEnd: number | undefined
      let chapterLabel: string | undefined
      if (selectedChapterKeys.size === 1) {
        const tocId = Array.from(selectedChapterKeys)[0]
        const chIdx = chapters.findIndex((c) => String(c.id) === tocId)
        if (chIdx !== -1) {
          const ch = chapters[chIdx]
          chapterLabel = ch.number ? `${ch.number} ${ch.title}` : ch.title
          pageStart = (ch.pdf_page ?? 1) - 1
          for (let j = chIdx + 1; j < chapters.length; j++) {
            const nxt = chapters[j]
            if (nxt.pdf_page && nxt.pdf_page > (ch.pdf_page ?? 1)) {
              pageEnd = nxt.pdf_page - 1
              break
            }
          }
        }
      }

      const qs = await generateQuestions(targetBookIds, genCount, {
        category,
        pageStart,
        pageEnd,
      })

      if (qs.length === 0) {
        setGenError(isZh ? 'Aucune question générée, vérifiez l\'index' : 'No questions generated')
      } else {
        await Promise.all(
          qs.map((q: Record<string, any>) =>
            saveQuestionToPayload({
              question: q.question,
              bookId: q.book_id || targetBookIds[0] || '',
              bookTitle: q.book_title || '',
              topicHint: q.type || q.difficulty || '',
              source: 'ai',
              likes: 0,
              questionCategory: q.question_category || '',
              sourcePage: q.source_page ?? pageStart ?? undefined,
              scoreRelevance: q.score_relevance || undefined,
              scoreClarity: q.score_clarity || undefined,
              scoreDifficulty: q.score_difficulty || undefined,
              scoreOverall: q.score_overall || undefined,
            }).catch(() => { })
          )
        )
      }
      load()
    } catch {
      setGenError(isZh ? 'Échec de la génération' : 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }, [targetBookIds, selectedChapterKeys, chapters, filter, genCount, isZh, load])

  // ==========================================================
  // Helpers
  // ==========================================================
  const formatDate = (d: string) => {
    if (!d) return ''
    return new Date(d).toLocaleDateString(isZh ? 'fr-CA' : 'en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  }

  const getBookTitle = (q: Question) => {
    if (q.bookTitle) return q.bookTitle
    const book = books.find((b) => b.book_id === q.bookId)
    return book?.title || q.bookId
  }

  const getTypeConfig = (q: Question) => {
    const hint = (q.topicHint || '').toLowerCase()
    return TYPE_CONFIG[hint] || { icon: MessageSquare, gradient: 'from-slate-500/20 to-slate-500/10', text: 'text-slate-400' }
  }

  // ==========================================================
  // Chapter selection summary (for toolbar)
  // ==========================================================
  const chapterHint = useMemo(() => {
    if (!isSingleBook) return null
    if (selectedChapterKeys.size === 0) return isZh ? 'Livre entier' : 'Whole book'
    if (selectedChapterKeys.size === 1) {
      const ch = chapters.find((c) => String(c.id) === Array.from(selectedChapterKeys)[0])
      return ch ? (ch.number ? `Ch ${ch.number}` : ch.title.slice(0, 20)) : null
    }
    return isZh ? `${selectedChapterKeys.size} chapitres` : `${selectedChapterKeys.size} chapters`
  }, [isSingleBook, selectedChapterKeys, chapters, isZh])

  // ==========================================================
  // Resizable eval panel drag handler
  // ==========================================================
  const createDragHandler = useCallback(
    (setter: React.Dispatch<React.SetStateAction<number>>, min: number, max: number, invert = false) => {
      return (e: React.MouseEvent) => {
        e.preventDefault()
        const startX = e.clientX
        let startWidth = 0
        setter(w => { startWidth = w; return w })

        const onMove = (ev: MouseEvent) => {
          const rawDelta = ev.clientX - startX
          const delta = invert ? -rawDelta : rawDelta
          setter(Math.min(max, Math.max(min, startWidth + delta)))
        }
        const onUp = () => {
          document.removeEventListener('mousemove', onMove)
          document.removeEventListener('mouseup', onUp)
          document.body.style.cursor = ''
          document.body.style.userSelect = ''
        }
        document.addEventListener('mousemove', onMove)
        document.addEventListener('mouseup', onUp)
        document.body.style.cursor = 'col-resize'
        document.body.style.userSelect = 'none'
      }
    },
    [],
  )

  // ==========================================================
  // Render: Evaluation card for a single question
  // ==========================================================
  const renderEvalCard = (q: Question) => {
    const state = evalStates[q.id]

    // Not evaluated yet
    if (!state || state.status === 'idle') {
      return (
        <div className="flex items-center justify-center h-full min-h-[80px]">
          <div className="flex items-center gap-2 text-muted-foreground/40">
            <Clock className="h-4 w-4" />
            <span className="text-xs">{isZh ? 'En attente…' : 'Pending…'}</span>
          </div>
        </div>
      )
    }

    // Loading
    if (state.status === 'loading') {
      return (
        <div className="flex items-center justify-center h-full min-h-[80px]">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-[10px] text-muted-foreground animate-pulse">
              {isZh ? 'Évaluation en cours…' : 'Evaluating…'}
            </span>
          </div>
        </div>
      )
    }

    // Error
    if (state.status === 'error') {
      return (
        <div className="p-3">
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
            <AlertCircle className="h-3.5 w-3.5 text-destructive mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-medium text-destructive">{isZh ? 'Échec' : 'Failed'}</p>
              <p className="text-[9px] text-destructive/60 mt-0.5 line-clamp-2">{state.error}</p>
            </div>
            <button
              type="button"
              onClick={() => evaluateQuestion(q.id, q.question)}
              className="p-1 rounded hover:bg-destructive/10 shrink-0"
            >
              <RotateCcw className="h-3 w-3 text-destructive" />
            </button>
          </div>
        </div>
      )
    }

    // Done — show evaluation results
    const depthLabel = state.depth
    const depthMeta = depthLabel ? DEPTH_META[depthLabel] : null
    const normScore = state.depthNormalized
    const grade = getGrade(normScore)
    const gradeStyle = GRADE_STYLES[grade]

    // Self-assessment scores from the question record
    const hasScores = q.scoreOverall != null

    return (
      <div className="p-2.5 space-y-2">
        {/* Re-evaluate button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => evaluateQuestion(q.id, q.question)}
            className="p-1 rounded hover:bg-secondary transition-colors"
            title={isZh ? 'Ré-évaluer' : 'Re-evaluate'}
          >
            <RotateCcw className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>

        {/* Top box: Scores (depth + generation) */}
        <div className={cn(
          'rounded-lg border p-2.5 space-y-2',
          'border-violet-500/30 bg-gradient-to-br from-violet-500/20 to-purple-500/10',
        )}>
          <div className="flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5 text-violet-400" />
            <span className="text-[10px] font-semibold text-foreground flex-1">
              {isZh ? 'Profondeur de la question' : 'Question Depth'}
            </span>
            {normScore != null && (
              <div className="flex items-center gap-1">
                <span className={cn('text-sm font-bold tabular-nums', gradeStyle.text)}>
                  {normScore.toFixed(2)}
                </span>
                <span className={cn(
                  'inline-flex px-1 py-0.5 rounded text-[8px] font-semibold',
                  gradeStyle.text, gradeStyle.bg,
                )}>
                  {isZh ? gradeStyle.labelFr : gradeStyle.label}
                </span>
              </div>
            )}
          </div>
          {depthLabel && depthMeta ? (
            <div className="flex items-center gap-2">
              <span className={cn(
                'inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold border',
                depthMeta.color,
                'bg-violet-500/10 border-violet-500/30',
              )}>
                {isZh ? depthMeta.labelFr : depthMeta.label}
              </span>
              {state.depthScore != null && (
                <span className="text-[9px] text-muted-foreground">
                  {isZh ? 'Brut' : 'Raw'}: {state.depthScore.toFixed(1)}/5.0
                </span>
              )}
            </div>
          ) : (
            <span className="text-[9px] text-muted-foreground italic">
              {isZh ? 'En attente d\'évaluation…' : 'Awaiting assessment…'}
            </span>
          )}
        </div>

        {/* Bottom box: Reasoning (collapsible) */}
        {state.reasoning && (
          <details className={cn(
            'rounded-lg border group/details',
            'border-border/50 bg-card/50',
          )}>
            <summary className="cursor-pointer list-none px-2.5 py-2 flex items-center gap-1.5">
              <ChevronRight className="h-3 w-3 text-muted-foreground transition-transform group-open/details:rotate-90" />
              <span className="text-[10px] font-semibold text-foreground">
                {isZh ? 'Raisonnement' : 'Reasoning'}
              </span>
            </summary>
            <div className="px-2.5 pb-2.5 pt-0">
              <p className="text-[9px] text-muted-foreground leading-relaxed whitespace-pre-wrap">
                {state.reasoning}
              </p>
            </div>
          </details>
        )}

        {/* Self-assessment scores card (from generation) */}
        {hasScores && (
          <div className={cn(
            'rounded-lg border p-2.5 space-y-2',
            'border-blue-500/30 bg-gradient-to-br from-blue-500/20 to-cyan-500/10',
          )}>
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-blue-400" />
              <span className="text-[10px] font-semibold text-foreground flex-1">
                {isZh ? 'Scores de génération' : 'Generation Scores'}
              </span>
              {q.scoreOverall != null && (
                <span className="text-sm font-bold tabular-nums text-amber-400">
                  ★ {q.scoreOverall}
                </span>
              )}
            </div>
            <div className="space-y-1.5">
              {q.scoreRelevance != null && renderScoreBar(
                isZh ? '相关性' : 'Relevance',
                q.scoreRelevance / 5,
                'bg-blue-500',
              )}
              {q.scoreClarity != null && renderScoreBar(
                isZh ? '清晰度' : 'Clarity',
                q.scoreClarity / 5,
                'bg-cyan-500',
              )}
              {q.scoreDifficulty != null && renderScoreBar(
                isZh ? '难度' : 'Difficulty',
                q.scoreDifficulty / 5,
                'bg-amber-500',
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  /** Render a single score bar row. */
  const renderScoreBar = (label: string, score: number | null | undefined, barColor: string) => {
    const grade = getGrade(score)
    const style = GRADE_STYLES[grade]
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground w-16 shrink-0">
          {label}
        </span>
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-500', barColor)}
            style={{ width: `${(score ?? 0) * 100}%` }}
          />
        </div>
        <span className={cn('text-xs font-bold tabular-nums w-9 text-right', style.text)}>
          {score != null ? score.toFixed(2) : '—'}
        </span>
      </div>
    )
  }

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <SidebarLayout
      title={isZh ? '书籍' : 'Books'}
      icon={<BookOpen className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={handleFilterChange}
      showViewToggle
      viewMode={viewMode}
      onViewModeChange={setViewMode}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {booksLoading
            ? (isZh ? '正在加载书籍…' : 'Loading books…')
            : (isZh ? `${books.length} 本书 · ${questions.length} 个问题` : `${books.length} books · ${questions.length} questions`)
          }
        </p>
      }
      loading={loading}
      loadingText={isZh ? '正在加载...' : 'Loading...'}
      error={error}
      onRetry={load}
      toolbar={
        <div className="flex items-center gap-2">
          {/* Chapter hint badge */}
          {chapterHint && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
              {chapterHint}
            </span>
          )}

          {/* ── Generate controls ────────────────────── */}
          <div className="flex items-center gap-1.5">
            <input
              type="number"
              min={1}
              max={20}
              value={genCount}
              onChange={(e) => setGenCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              className="w-10 h-7 rounded-md border border-border bg-card text-xs text-center text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              disabled={generating}
              title={isZh ? '生成数量' : 'Count'}
            />
            <button
              onClick={handleGenerate}
              disabled={generating || targetBookIds.length === 0}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all',
                generating
                  ? 'bg-primary/20 text-primary cursor-wait'
                  : 'bg-gradient-to-r from-primary to-primary/80 text-primary-foreground hover:shadow-lg hover:shadow-primary/25 hover:scale-[1.02] active:scale-[0.98] shadow-sm'
              )}
              title={isZh ? '生成问题' : 'Generate questions'}
            >
              {generating
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <Sparkles className="h-3.5 w-3.5" />
              }
              {isZh ? '生成' : 'Generate'}
            </button>
          </div>

          {/* ── Evaluate all button (after Generate) ── */}
          {displayQuestions.length > 0 && !autoEvalRunning && (
            <button
              onClick={() => autoEvaluateAll(displayQuestions)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-violet-400 hover:bg-violet-500/10 transition-colors border border-violet-500/20"
              title={isZh ? '评估所有问题' : 'Evaluate all'}
            >
              <BarChart3 className="h-3.5 w-3.5" />
              {isZh ? '评估' : 'Evaluate'}
            </button>
          )}

          {/* Auto-eval progress */}
          {autoEvalRunning && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-500/5 border border-violet-500/20">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
              <span className="text-xs text-foreground font-medium">
                {evalProgress.done}/{evalProgress.total}
              </span>
              <div className="w-12 h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-violet-500 transition-all duration-300"
                  style={{ width: `${evalProgress.total > 0 ? (evalProgress.done / evalProgress.total) * 100 : 0}%` }}
                />
              </div>
            </div>
          )}

          {/* ── Divider ──────────────────────────────── */}
          <div className="w-px h-5 bg-border" />

          {/* ── List controls ────────────────────────── */}
          {displayQuestions.length > 0 && (
            <button
              onClick={handleClearAll}
              disabled={clearingAll}
              className="flex items-center gap-1 px-2 py-1.5 rounded-md text-[11px] font-medium text-destructive/70 hover:bg-destructive/10 hover:text-destructive transition-colors disabled:opacity-50"
              title={isZh ? '清空当前列表' : 'Clear all'}
            >
              <Trash2 className={`h-3 w-3 ${clearingAll ? 'animate-spin' : ''}`} />
              {isZh ? '清空' : 'Clear'}
            </button>
          )}
          <button
            onClick={load}
            className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            title={isZh ? '刷新' : 'Refresh'}
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      }
    >

      {/* ── Generation error feedback ──────────────────────── */}
      {genError && !generating && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-destructive/10 text-destructive text-xs mb-4">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {genError}
          <button onClick={() => setGenError(null)} className="ml-auto text-[10px] underline hover:no-underline">
            {isZh ? '关闭' : 'Dismiss'}
          </button>
        </div>
      )}

      {/* ── Generating indicator ──────────────────────────── */}
      {generating && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-primary/5 border border-primary/10 mb-4">
          <div className="relative">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <div className="absolute inset-0 h-5 w-5 animate-ping rounded-full bg-primary/20" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              {isZh ? `正在生成 ${genCount} 个问题…` : `Generating ${genCount} questions…`}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {isZh ? '大约需要 10-30 秒' : 'This may take 10-30 seconds'}
            </p>
          </div>
        </div>
      )}

      {/* ── Three-column split: PDF (left) + Questions (center) + Eval (right) ── */}
      <div className="flex flex-1 min-h-0">

        {/* ── PDF Preview toggle button (when hidden) ─────── */}
        {selectedBookId && !showPreview && previewPage && (
          <button
            onClick={() => setShowPreview(true)}
            className="shrink-0 self-start flex flex-col items-center justify-center w-8 py-3 rounded-lg border border-border bg-card/50 hover:bg-secondary transition-colors gap-1"
            title={isZh ? '展开预览' : 'Show PDF preview'}
          >
            <PanelLeftOpen className="h-4 w-4 text-muted-foreground" />
            <span className="text-[8px] text-muted-foreground writing-mode-vertical" style={{ writingMode: 'vertical-rl' }}>PDF</span>
          </button>
        )}

        {/* ── PDF Preview Panel (LEFT) ──────────────────── */}
        {previewPage && showPreview && selectedBookId && (
          <>
            <div
              className="shrink-0 self-start flex flex-col rounded-xl border border-border bg-card/50 overflow-hidden"
              style={{ width: pdfWidth }}
            >
              {/* Preview header */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                  <span className="text-xs font-semibold text-foreground">
                    {isZh ? '原文预览' : 'PDF Preview'}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                    p.{previewPage}
                  </span>
                </div>
                <button
                  onClick={() => setShowPreview(false)}
                  className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                  title={isZh ? '收起预览' : 'Collapse preview'}
                >
                  <PanelLeftClose className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* PDF rendered via react-pdf — single page with nav */}
              <div className="flex-1 min-h-0 overflow-auto bg-muted/20 p-4 flex flex-col items-center" id="pdf-scroll-container">
                <Document
                  file={`${ENGINE}/engine/books/${selectedBookId}/pdf`}
                  loading={
                    <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      {isZh ? '加载 PDF...' : 'Loading PDF...'}
                    </div>
                  }
                  onLoadSuccess={({ numPages: n }) => setNumPdfPages(n)}
                >
                  <Page
                    pageNumber={previewPage}
                    width={pdfWidth - 48}
                    renderTextLayer
                    renderAnnotationLayer={false}
                  />
                </Document>
              </div>

              {/* Page navigation */}
              <div className="flex items-center justify-center gap-3 px-3 py-1.5 border-t border-border bg-muted/30">
                <button
                  className="px-2 py-0.5 rounded text-xs hover:bg-accent disabled:opacity-30 transition-colors"
                  disabled={previewPage <= 1}
                  onClick={() => setPreviewPage((p) => Math.max(1, (p ?? 1) - 1))}
                >◀</button>
                <span className="text-[11px] text-muted-foreground tabular-nums">
                  {previewPage} / {numPdfPages || '…'}
                </span>
                <button
                  className="px-2 py-0.5 rounded text-xs hover:bg-accent disabled:opacity-30 transition-colors"
                  disabled={numPdfPages > 0 && previewPage >= numPdfPages}
                  onClick={() => setPreviewPage((p) => Math.min(numPdfPages || 9999, (p ?? 1) + 1))}
                >▶</button>
              </div>
            </div>

            {/* Resize handle */}
            <ResizeHandle
              width={pdfWidth}
              onResize={setPdfWidth}
              min={280}
              max={800}
            />
          </>
        )}

        {/* ── Questions column (CENTER) ────────────────────── */}
        <div className="flex-1 min-w-0 overflow-y-auto" ref={leftPanelRef} onScroll={handleLeftScroll}>
          <div className="p-4">
            {/* Empty state */}
            {!loading && displayQuestions.length === 0 && (
              <div className="flex flex-col items-center justify-center py-24">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center mb-5 shadow-lg shadow-primary/5">
                  {selectedBookId
                    ? <BookOpen className="h-8 w-8 text-primary/60" />
                    : <MessageSquare className="h-8 w-8 text-primary/60" />
                  }
                </div>
                <h3 className="text-base font-semibold text-foreground mb-1.5">
                  {selectedBookId
                    ? (isZh ? '此书暂无问题' : 'No questions for this book')
                    : (isZh ? '暂无问题' : 'No questions yet')
                  }
                </h3>
                <p className="text-sm text-muted-foreground text-center max-w-xs leading-relaxed">
                  {selectedBookId
                    ? (isZh ? '点击工具栏「生成」按钮来创建问题' : 'Click "Generate" in the toolbar to create questions')
                    : (isZh ? '从左侧选择一本书，然后点击「生成」' : 'Select a book, then click "Generate"')
                  }
                </p>
              </div>
            )}

            {/* ── Question cards ──────────────────────── */}
            {displayQuestions.length > 0 && (
              <div className="space-y-3">
                {/* Header */}
                <div className="text-[10px] text-muted-foreground bg-muted/50 rounded-lg px-3 py-1.5 flex items-center justify-between sticky top-0 z-10 backdrop-blur-sm">
                  <span className="font-medium text-foreground text-[11px]">
                    {isZh ? '问题列表' : 'Questions'}
                  </span>
                  <span>
                    {displayQuestions.length} {isZh ? '个问题' : 'items'}
                  </span>
                </div>

                {displayQuestions.map((q, idx) => {
                  const typeConf = getTypeConfig(q)
                  const TypeIcon = typeConf.icon
                  return (
                    <div key={q.id} data-question-id={q.id}>
                      {/* Turn separator */}
                      {idx > 0 && (
                        <div className="flex items-center gap-2 text-[9px] text-muted-foreground/50 px-1 mb-2">
                          <div className="h-px flex-1 bg-border/50" />
                          <span>#{idx + 1}</span>
                          <div className="h-px flex-1 bg-border/50" />
                        </div>
                      )}

                      {/* Question card */}
                      <div className={cn(
                        'group relative rounded-xl border border-border bg-card overflow-hidden',
                        'hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5',
                        'transition-all duration-300 ease-out',
                      )}>
                        {/* Gradient top accent */}
                        <div className={cn(
                          'h-0.5 w-full bg-gradient-to-r',
                          typeConf.gradient.replace('/20', '/60').replace('/10', '/30'),
                        )} />

                        <div className="p-4">
                          {/* Header: category + type badge + source */}
                          <div className="flex items-center gap-2 mb-3 flex-wrap">
                            {q.questionCategory && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold rounded-full px-2 py-0.5 bg-gradient-to-r from-teal-500/20 to-cyan-500/10 text-teal-400">
                                🏷️ {q.questionCategory}
                              </span>
                            )}
                            {q.topicHint && (
                              <span className={cn(
                                'inline-flex items-center gap-1 text-[10px] font-semibold rounded-full px-2 py-0.5',
                                'bg-gradient-to-r', typeConf.gradient, typeConf.text,
                              )}>
                                <TypeIcon className="h-2.5 w-2.5" />
                                {q.topicHint}
                              </span>
                            )}
                            <span className="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-purple-500/10 text-purple-400">
                              AI
                            </span>
                            {q.model && (
                              <span className="text-[10px] rounded-full px-1.5 py-0.5 bg-muted text-muted-foreground ml-auto">
                                {q.model}
                              </span>
                            )}
                          </div>

                          {/* Question text */}
                          <div className="text-sm text-foreground leading-relaxed mb-4 [&_p]:m-0">
                            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                              {q.question}
                            </ReactMarkdown>
                          </div>

                          {/* Footer: book info + actions */}
                          <div className="flex items-center justify-between pt-3 border-t border-border/50">
                            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground min-w-0 max-w-[70%]">
                              <BookOpen className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                              <span className="truncate">{getBookTitle(q)}</span>
                              {q.sourcePage != null && (
                                <span className="shrink-0 text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                                  p.{q.sourcePage + 1}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => handleLike(q.id)}
                                disabled={likingIds.has(q.id)}
                                className={cn(
                                  'flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-all',
                                  q.likes > 0
                                    ? 'bg-primary/10 text-primary hover:bg-primary/20'
                                    : 'text-muted-foreground hover:bg-primary/10 hover:text-primary'
                                )}
                              >
                                <ThumbsUp className={cn('h-3 w-3', likingIds.has(q.id) && 'animate-bounce')} />
                                {q.likes}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(q.id)}
                                disabled={deletingIds.has(q.id)}
                                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-full text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
                                title={isZh ? '删除' : 'Delete'}
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>

                          {/* Date */}
                          {q.createdAt && (
                            <p className="text-[9px] text-muted-foreground/50 mt-2">
                              {formatDate(q.createdAt)}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>{/* end questions column */}

        {/* ── Evaluation column (RIGHT) ──────────────────── */}
        {displayQuestions.length > 0 && (
          <>
          <ResizeHandle
            width={evalPanelWidth}
            onResize={setEvalPanelWidth}
            min={240}
            max={520}
            invert
          />
          <div
            className="shrink-0 border-l border-border overflow-y-auto"
            style={{ width: evalPanelWidth }}
            ref={rightPanelRef}
            onScroll={handleRightScroll}
          >
            {/* Eval header */}
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm px-3 py-2 border-b border-border">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-3.5 w-3.5 text-violet-400" />
                <span className="text-[11px] font-medium text-foreground flex-1">
                  {isZh ? '质量评估' : 'Quality Evaluation'}
                </span>
                {evalProgress.total > 0 && (
                  <span className="text-[9px] text-muted-foreground">
                    {evalProgress.done}/{evalProgress.total}
                  </span>
                )}
              </div>
            </div>

            {/* Eval cards */}
            <div className="p-3 space-y-3">
              {displayQuestions.map((q, idx) => (
                <div key={q.id} data-eval-id={q.id}>
                  {idx > 0 && (
                    <div className="flex items-center gap-2 text-[9px] text-muted-foreground/50 px-1 mb-2">
                      <div className="h-px flex-1 bg-border/50" />
                      <span>#{idx + 1}</span>
                      <div className="h-px flex-1 bg-border/50" />
                    </div>
                  )}
                  <div className="rounded-xl border border-border bg-card/80">
                    {renderEvalCard(q)}
                  </div>
                </div>
              ))}
            </div>
          </div>
          </>
        )}

      </div>{/* end split layout */}
    </SidebarLayout>
  )
}
