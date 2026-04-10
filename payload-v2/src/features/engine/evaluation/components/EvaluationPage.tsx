/**
 * EvaluationPage — Data-driven RAG evaluation hub.
 *
 * Route: /engine/evaluation
 *
 * Two-column synced-scroll layout:
 *   Left sidebar: session list
 *   Main area: conversation replay (left) + evaluation cards (right)
 *   Selecting a session auto-evaluates all queries and renders results
 *   aligned with each Q&A pair, with synchronized scrolling.
 */

'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  LineChart, Loader2, AlertCircle, RotateCcw,
  Search, Info, GripVertical,
  Clock, MessageSquare, BarChart3,
  Users, User, Zap, ChevronRight,
  FileText, Sparkles, BookOpen,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import {
  evaluateFromHistory,
  fetchQueriesBySession,
  fetchSessionsForEval,
  fetchEvaluations,
  fetchEvalProviders,
} from '../api'
import type {
  HistoryEvalSingleResult,
  QueryListItem,
  SessionListItem,
  EvaluationResult,
} from '../types'
import type { EvalProvider } from '../api'
import { useAuth } from '@/features/shared/AuthProvider'
import AnswerBlockRenderer from '@/features/chat/panel/AnswerBlockRenderer'

// ============================================================
// Evaluation group definitions
// ============================================================

/** Depth label → display info. */
const DEPTH_META: Record<string, { label: string; labelFr: string; color: string }> = {
  surface: { label: 'Surface', labelFr: '浅层', color: 'text-amber-400' },
  understanding: { label: 'Understanding', labelFr: '理解', color: 'text-blue-400' },
  synthesis: { label: 'Synthesis', labelFr: '综合', color: 'text-emerald-400' },
}

/** Group metadata for the 3 evaluation categories. */
const EVAL_GROUPS = {
  question: {
    label: 'Question Quality',
    labelFr: '问题质量',
    Icon: FileText,
    gradient: 'from-violet-500/20 to-purple-500/10',
    border: 'border-violet-500/30',
    accentText: 'text-violet-400',
    accentBg: 'bg-violet-500/10',
    dimensions: [] as { key: string; label: string; labelFr: string; color: string }[],
  },
  answer: {
    label: 'Answer Quality',
    labelFr: '回答质量',
    Icon: Sparkles,
    gradient: 'from-blue-500/20 to-cyan-500/10',
    border: 'border-blue-500/30',
    accentText: 'text-blue-400',
    accentBg: 'bg-blue-500/10',
    dimensions: [
      { key: 'faithfulness', label: 'Faithfulness', labelFr: '忠实度', color: 'bg-blue-500' },
      { key: 'answer_relevancy', label: 'Answer Relevancy', labelFr: '答案相关性', color: 'bg-cyan-500' },
    ],
  },
  citation: {
    label: 'Citation Quality',
    labelFr: '引用质量',
    Icon: BookOpen,
    gradient: 'from-amber-500/20 to-orange-500/10',
    border: 'border-amber-500/30',
    accentText: 'text-amber-400',
    accentBg: 'bg-amber-500/10',
    dimensions: [
      { key: 'context_relevancy', label: 'Context Relevancy', labelFr: '上下文相关性', color: 'bg-amber-500' },
      { key: 'relevancy', label: 'Source Relevancy', labelFr: '来源相关性', color: 'bg-orange-500' },
    ],
  },
} as const

type Grade = 'excellent' | 'good' | 'fair' | 'poor' | 'none'

function getGrade(score: number | null | undefined): Grade {
  if (score == null) return 'none'
  if (score >= 0.85) return 'excellent'
  if (score >= 0.7) return 'good'
  if (score >= 0.5) return 'fair'
  return 'poor'
}

const GRADE_STYLES: Record<Grade, { label: string; labelFr: string; text: string; bg: string; border: string }> = {
  excellent: { label: 'Excellent', labelFr: '优秀', text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  good: { label: 'Good', labelFr: '良好', text: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  fair: { label: 'Fair', labelFr: '一般', text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  poor: { label: 'Poor', labelFr: '较差', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  none: { label: '—', labelFr: '—', text: 'text-zinc-500', bg: 'bg-zinc-500/10', border: 'border-zinc-500/30' },
}

/** Extract a short summary from verbose LLM evaluator feedback. */
function extractFeedbackSummary(text: string): string {
  if (!text) return ''
  const t = cleanFeedbackText(text)

  // Simple YES/NO answers — return as-is
  if (/^(YES|NO)$/i.test(t)) return t

  // Look for "Final feedback:" section
  const finalMatch = t.match(/Final feedback:\s*(.+)/is)
  if (finalMatch) return finalMatch[1].trim().slice(0, 120) + (finalMatch[1].trim().length > 120 ? '…' : '')

  // Default: first sentence up to 120 chars
  const firstSentence = t.split(/[.!?]\s/)[0] || t
  return firstSentence.slice(0, 120) + (firstSentence.length > 120 ? '…' : '')
}

/** Strip internal LlamaIndex evaluator artifacts from feedback text. */
function cleanFeedbackText(text: string): string {
  return text
    .replace(/\s*\[RESULT\]\s*[\d.]+\s*/g, '')  // Remove [RESULT] 3.5 etc.
    .replace(/\s*\[RESULT\]\s*/g, '')             // Remove standalone [RESULT]
    .trim()
}

type UserScope = 'mine' | 'all'

/** Track per-query eval state. */
interface QueryEvalState {
  status: 'idle' | 'loading' | 'done' | 'error'
  result?: HistoryEvalSingleResult | null
  existing?: EvaluationResult | null
  error?: string
}

// ============================================================
// Component
// ============================================================
export default function EvaluationPage() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'
  const { user } = useAuth()

  // — Sessions
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [selectedSession, setSelectedSession] = useState<SessionListItem | null>(null)

  // — Queries within session
  const [sessionQueries, setSessionQueries] = useState<QueryListItem[]>([])
  const [queriesLoading, setQueriesLoading] = useState(false)

  // — Per-query evaluation state
  const [evalStates, setEvalStates] = useState<Record<number, QueryEvalState>>({})

  // — Overall auto-eval progress
  const [autoEvalRunning, setAutoEvalRunning] = useState(false)
  const [evalProgress, setEvalProgress] = useState({ done: 0, total: 0 })
  const abortAutoEvalRef = useRef(false)

  // — Filters
  const [timeFilter, setTimeFilter] = useState<'all' | 'today' | '7d' | '30d'>('all')
  const [userScope, setUserScope] = useState<UserScope>('mine')
  const isAdmin = user?.role === 'admin'

  // — Model selection
  const [providers, setProviders] = useState<EvalProvider[]>([])
  const [selectedModel, setSelectedModel] = useState<string | undefined>(undefined)

  // — Methodology panel
  const [showMethodology, setShowMethodology] = useState(false)

  // — Resizable panel widths
  const [sidebarWidth, setSidebarWidth] = useState(256)
  const [evalPanelWidth, setEvalPanelWidth] = useState(400)

  // — Scroll sync refs
  const leftPanelRef = useRef<HTMLDivElement>(null)
  const rightPanelRef = useRef<HTMLDivElement>(null)
  const isSyncingRef = useRef(false)
  // Refs for per-query row alignment
  const leftRowRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const rightRowRefs = useRef<Map<number, HTMLDivElement>>(new Map())

  // Auto-load sessions
  useEffect(() => {
    if (user === undefined) return
    loadSessions()
  }, [user?.id, userScope]) // eslint-disable-line react-hooks/exhaustive-deps

  // Load available LLM providers
  useEffect(() => {
    fetchEvalProviders()
      .then(setProviders)
      .catch(() => { /* engine unavailable */ })
  }, [])

  /** Create a drag handler for resizable panels. */
  const createDragHandler = useCallback(
    (setter: React.Dispatch<React.SetStateAction<number>>, min: number, max: number, invert = false) => {
      return (e: React.MouseEvent) => {
        e.preventDefault()
        const startX = e.clientX
        let startWidth = 0
        // Read current width from the setter's initial value
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

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const scopedUserId = (isAdmin && userScope === 'all') ? undefined : user?.id
      const list = await fetchSessionsForEval(100, scopedUserId)
      setSessions(list)
    } catch {
      // Payload unavailable
    } finally {
      setSessionsLoading(false)
    }
  }, [user?.id, isAdmin, userScope])

  // Client-side time filtering
  const filteredSessions = sessions.filter((s) => {
    if (timeFilter === 'all') return true
    if (!s.createdAt) return false
    const created = new Date(s.createdAt).getTime()
    const now = Date.now()
    const DAY = 86400000
    if (timeFilter === 'today') return now - created < DAY
    if (timeFilter === '7d') return now - created < 7 * DAY
    if (timeFilter === '30d') return now - created < 30 * DAY
    return true
  })

  // Scroll synchronization
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

  /** Auto-evaluate all queries in a session sequentially. */
  const autoEvaluateSession = useCallback(async (queries: QueryListItem[]) => {
    abortAutoEvalRef.current = false
    setAutoEvalRunning(true)
    setEvalProgress({ done: 0, total: queries.length })

    const newStates: Record<number, QueryEvalState> = {}

    // First pass: check for existing evals (with question depth data)
    for (const q of queries) {
      try {
        const { evaluations } = await fetchEvaluations({ queryRef: q.id, limit: 1 })
        if (evaluations.length > 0 && evaluations[0].questionDepth) {
          // Has complete grouped eval data
          newStates[q.id] = { status: 'done', existing: evaluations[0] }
        } else {
          // Missing question depth — needs re-evaluation
          newStates[q.id] = { status: 'idle' }
        }
      } catch {
        newStates[q.id] = { status: 'idle' }
      }
    }
    setEvalStates({ ...newStates })
    const alreadyDone = Object.values(newStates).filter(s => s.status === 'done').length
    setEvalProgress({ done: alreadyDone, total: queries.length })

    // Second pass: evaluate queries that don't have existing evals
    let doneCount = alreadyDone
    for (const q of queries) {
      if (abortAutoEvalRef.current) break
      if (newStates[q.id]?.status === 'done') continue

      // Mark as loading
      setEvalStates(prev => ({ ...prev, [q.id]: { status: 'loading' } }))

      try {
        const result = await evaluateFromHistory(q.id, selectedModel)
        // Fetch the newly persisted eval from Payload
        const { evaluations } = await fetchEvaluations({ queryRef: q.id, limit: 1 })
        const evalDoc = evaluations.length > 0 ? evaluations[0] : null

        newStates[q.id] = { status: 'done', result, existing: evalDoc }
        setEvalStates(prev => ({ ...prev, [q.id]: newStates[q.id] }))
      } catch (err) {
        newStates[q.id] = {
          status: 'error',
          error: err instanceof Error ? err.message : String(err),
        }
        setEvalStates(prev => ({ ...prev, [q.id]: newStates[q.id] }))
      }

      doneCount++
      setEvalProgress({ done: doneCount, total: queries.length })
    }

    setAutoEvalRunning(false)
  }, [])

  /** Select a session — load queries and auto-evaluate. */
  const handleSelectSession = useCallback(async (s: SessionListItem) => {
    // Abort any in-progress auto-eval
    abortAutoEvalRef.current = true
    setSelectedSession(s)
    setSessionQueries([])
    setEvalStates({})
    setQueriesLoading(true)

    try {
      const items = await fetchQueriesBySession(s.id)
      setSessionQueries(items)
      setQueriesLoading(false)
      // Auto-evaluate
      if (items.length > 0) {
        await autoEvaluateSession(items)
      }
    } catch {
      setSessionQueries([])
      setQueriesLoading(false)
    }
  }, [autoEvaluateSession])

  /** Re-evaluate a single query (force). */
  const handleReEvaluate = useCallback(async (queryId: number) => {
    setEvalStates(prev => ({ ...prev, [queryId]: { status: 'loading' } }))
    try {
      const result = await evaluateFromHistory(queryId, selectedModel)
      const { evaluations } = await fetchEvaluations({ queryRef: queryId, limit: 1 })
      setEvalStates(prev => ({
        ...prev,
        [queryId]: {
          status: 'done',
          result,
          existing: evaluations.length > 0 ? evaluations[0] : null,
        },
      }))
    } catch (err) {
      setEvalStates(prev => ({
        ...prev,
        [queryId]: {
          status: 'error',
          error: err instanceof Error ? err.message : String(err),
        },
      }))
    }
  }, [])

  // ============================================================
  // Render helpers
  // ============================================================

  /** Render a single score bar row. */
  const renderScoreBar = (label: string, score: number | null | undefined, barColor: string) => {
    const grade = getGrade(score)
    const style = GRADE_STYLES[grade]
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground w-28 shrink-0">
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

  /** Extract scores from eval state (supports both API result and Payload doc). */
  const extractGroupedScores = (state: QueryEvalState) => {
    // From fresh API result (grouped structure)
    if (state.result?.scores) {
      return {
        question: state.result.scores.question,
        answer: state.result.scores.answer,
        citation: state.result.scores.citation,
      }
    }
    // From existing Payload doc (flat structure)
    if (state.existing) {
      const e = state.existing
      return {
        question: {
          depth: e.questionDepth,
          depth_score: e.questionDepthScore ? e.questionDepthScore * 5 : null,
          depth_normalized: e.questionDepthScore,
        },
        answer: {
          faithfulness: e.faithfulness,
          answer_relevancy: e.answerRelevancy,
        },
        citation: {
          context_relevancy: e.contextRelevancy,
          relevancy: e.relevancy,
        },
      }
    }
    return null
  }

  /** Render a single evaluation group card. */
  const renderGroupCard = (
    groupKey: 'question' | 'answer' | 'citation',
    scores: ReturnType<typeof extractGroupedScores>,
    feedback: Record<string, string> | null,
  ) => {
    const group = EVAL_GROUPS[groupKey]

    // Question group is special — shows depth label instead of score bars
    if (groupKey === 'question' && scores) {
      const q = scores.question
      const depthLabel = q.depth
      const depthMeta = depthLabel ? DEPTH_META[depthLabel] : null
      const normScore = q.depth_normalized
      const grade = getGrade(normScore)
      const gradeStyle = GRADE_STYLES[grade]

      return (
        <div className={cn('rounded-lg border p-2.5 space-y-2', group.border, 'bg-gradient-to-br', group.gradient)}>
          <div className="flex items-center gap-1.5">
            <group.Icon className={cn('h-3.5 w-3.5', group.accentText)} />
            <span className="text-[10px] font-semibold text-foreground flex-1">
              {isFr ? group.labelFr : group.label}
            </span>
            {normScore != null && (
              <span className={cn('text-sm font-bold tabular-nums', gradeStyle.text)}>
                {normScore.toFixed(2)}
              </span>
            )}
          </div>
          {depthLabel && depthMeta ? (
            <div className="flex items-center gap-2">
              <span className={cn(
                'inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold border',
                depthMeta.color,
                group.accentBg, group.border,
              )}>
                {isFr ? depthMeta.labelFr : depthMeta.label}
              </span>
              {q.depth_score != null && (
                <span className="text-[9px] text-muted-foreground">
                  {isFr ? '原始分' : 'Raw'}: {q.depth_score.toFixed(1)}/5.0
                </span>
              )}
            </div>
          ) : (
            <span className="text-[9px] text-muted-foreground italic">
              {isFr ? '等待评估…' : 'Awaiting assessment…'}
            </span>
          )}
          {feedback?.question_depth && (
            <details className="rounded border border-border/30 bg-card/30">
              <summary className="cursor-pointer list-none px-2 py-1 text-[9px] text-muted-foreground flex items-center gap-1">
                <ChevronRight className="h-2.5 w-2.5 transition-transform details-open:rotate-90" />
                {isFr ? '评估理由' : 'Reasoning'}
              </summary>
              <div className="border-t border-border/20 px-2 py-1.5">
                <p className="text-[9px] text-muted-foreground leading-relaxed whitespace-pre-wrap">
                  {feedback.question_depth}
                </p>
              </div>
            </details>
          )}
        </div>
      )
    }

    // Answer and Citation groups — show score bars
    const dims = group.dimensions
    const groupScores = scores?.[groupKey] as Record<string, number | null> | undefined
    const validScores = dims
      .map(d => groupScores?.[d.key] ?? null)
      .filter((v): v is number => v != null)
    const avg = validScores.length > 0
      ? validScores.reduce((a, b) => a + b, 0) / validScores.length
      : null
    const avgGrade = getGrade(avg)
    const avgStyle = GRADE_STYLES[avgGrade]

    // Collect feedback for this group's dimensions
    const groupFeedback = dims
      .map(d => ({ label: isFr ? d.labelFr : d.label, text: feedback?.[d.key] }))
      .filter(f => f.text)

    return (
      <div className={cn('rounded-lg border p-2.5 space-y-2', group.border, 'bg-gradient-to-br', group.gradient)}>
        <div className="flex items-center gap-1.5">
          <group.Icon className={cn('h-3.5 w-3.5', group.accentText)} />
          <span className="text-[10px] font-semibold text-foreground flex-1">
            {isFr ? group.labelFr : group.label}
          </span>
          {avg != null && (
            <div className="flex items-center gap-1">
              <span className={cn('text-sm font-bold tabular-nums', avgStyle.text)}>
                {avg.toFixed(2)}
              </span>
              <span className={cn(
                'inline-flex px-1 py-0.5 rounded text-[8px] font-semibold',
                avgStyle.text, avgStyle.bg,
              )}>
                {isFr ? avgStyle.labelFr : avgStyle.label}
              </span>
            </div>
          )}
        </div>
        <div className="space-y-1.5">
          {dims.map(d => (
            <div key={d.key}>
              {renderScoreBar(
                isFr ? d.labelFr : d.label,
                groupScores?.[d.key] ?? null,
                d.color,
              )}
            </div>
          ))}
        </div>
        {groupFeedback.length > 0 && (
          <details className="rounded border border-border/30 bg-card/30">
            <summary className="cursor-pointer list-none px-2 py-1 text-[9px] text-muted-foreground flex items-center gap-1">
              <ChevronRight className="h-2.5 w-2.5 transition-transform details-open:rotate-90" />
              {isFr ? '详情' : 'Details'}
            </summary>
            <div className="border-t border-border/20 px-2 py-1.5 space-y-1.5">
              {groupFeedback.map(f => {
                // Extract the key conclusion from verbose LLM feedback
                const fullText = f.text || ''
                const summary = extractFeedbackSummary(fullText)
                const isVerbose = fullText.length > 80

                return (
                  <div key={f.label}>
                    <span className="text-[9px] font-semibold text-foreground">{f.label}: </span>
                    <span className="text-[9px] text-muted-foreground">{summary}</span>
                    {isVerbose && (
                      <details className="mt-0.5">
                        <summary className="cursor-pointer text-[8px] text-primary/60 hover:text-primary">
                          {isFr ? '查看完整反馈' : 'Show full feedback'}
                        </summary>
                        <p className="text-[8px] text-muted-foreground/70 leading-relaxed mt-0.5 whitespace-pre-wrap">
                          {cleanFeedbackText(fullText)}
                        </p>
                      </details>
                    )}
                  </div>
                )
              })}
            </div>
          </details>
        )}
      </div>
    )
  }

  /** Render complete evaluation card for a single query turn. */
  const renderEvalCard = (queryId: number) => {
    const state = evalStates[queryId]

    // Not started yet
    if (!state || state.status === 'idle') {
      return (
        <div className="flex items-center justify-center h-full min-h-[120px]">
          <div className="flex items-center gap-2 text-muted-foreground/40">
            <Clock className="h-4 w-4" />
            <span className="text-xs">{isFr ? '等待评估…' : 'Pending…'}</span>
          </div>
        </div>
      )
    }

    // Loading
    if (state.status === 'loading') {
      return (
        <div className="flex items-center justify-center h-full min-h-[120px]">
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-[10px] text-muted-foreground animate-pulse">
              {isFr ? '评估中…' : 'Evaluating…'}
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
              <p className="text-[10px] font-medium text-destructive">{isFr ? '评估失败' : 'Failed'}</p>
              <p className="text-[9px] text-destructive/60 mt-0.5 line-clamp-2">{state.error}</p>
            </div>
            <button
              type="button"
              onClick={() => handleReEvaluate(queryId)}
              className="p-1 rounded hover:bg-destructive/10 shrink-0"
            >
              <RotateCcw className="h-3 w-3 text-destructive" />
            </button>
          </div>
        </div>
      )
    }

    // Done — show 3 grouped sections
    const scores = extractGroupedScores(state)
    const feedback = state.existing?.feedback ?? state.result?.feedback ?? {}

    return (
      <div className="p-2.5 space-y-2">
        {/* Re-evaluate button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => handleReEvaluate(queryId)}
            className="p-1 rounded hover:bg-secondary transition-colors"
            title={isFr ? '重新评估' : 'Re-evaluate'}
          >
            <RotateCcw className="h-3 w-3 text-muted-foreground" />
          </button>
        </div>

        {/* 3 evaluation groups stacked */}
        {renderGroupCard('question', scores, feedback)}
        {renderGroupCard('answer', scores, feedback)}
        {renderGroupCard('citation', scores, feedback)}
      </div>
    )
  }

  // ============================================================
  // Render
  // ============================================================
  return (
    <div className="flex flex-col h-full">

      {/* ── Header ───────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
        <LineChart className="h-5 w-5 text-emerald-400" />
        <div className="flex-1">
          <h1 className="text-lg font-bold text-foreground">
            {isFr ? '统一评估中枢' : 'Evaluation Hub'}
          </h1>
          <p className="text-xs text-muted-foreground">
            {isFr
              ? '选择对话 → 自动评估 → 结果与对话对齐展示'
              : 'Select a session → auto-evaluate → results aligned with conversation'}
          </p>
        </div>

        {/* Auto-eval progress */}
        {autoEvalRunning && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/5 border border-primary/20">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className="text-xs text-foreground font-medium">
              {evalProgress.done}/{evalProgress.total}
            </span>
            <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${evalProgress.total > 0 ? (evalProgress.done / evalProgress.total) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}
        {/* Model selector */}
        {providers.length > 0 && (
          <select
            value={selectedModel ?? ''}
            onChange={e => setSelectedModel(e.target.value || undefined)}
            className="h-7 px-2 rounded-lg border border-border bg-background text-[11px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            title={isFr ? '选择评估模型' : 'Evaluation Model'}
          >
            <option value="">{isFr ? '默认模型' : 'Default Model'}</option>
            {providers.filter(p => p.available).map(p => (
              <option key={p.name} value={p.model}>
                {p.display_name} ({p.model})
              </option>
            ))}
          </select>
        )}

        {/* Methodology toggle */}
        <button
          type="button"
          onClick={() => setShowMethodology(v => !v)}
          className={cn(
            'p-1.5 rounded-lg transition-colors',
            showMethodology ? 'bg-primary/10 text-primary' : 'hover:bg-secondary text-muted-foreground',
          )}
          title={isFr ? '评估方法论' : 'Methodology'}
        >
          <Info className="h-4 w-4" />
        </button>
      </div>

      {/* ── Methodology panel ────────────────────────────────── */}
      {showMethodology && (
        <div className="px-6 py-3 border-b border-border bg-muted/20 text-[11px] leading-relaxed">
          <div className="grid grid-cols-3 gap-4 max-w-4xl">
            {/* Question Quality */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-foreground">
                <FileText className="h-3.5 w-3.5 text-violet-400" />
                <span>{isFr ? '问题质量' : 'Question Quality'}</span>
              </div>
              <p className="text-muted-foreground">
                {isFr
                  ? '基于 Bloom 认知层次（1-5）评估问题深度。使用 LLM 结构化评审判断问题属于浅层回忆（1）、理解（2）、应用（3）、分析（4）还是综合评估（5）。分数归一化到 0-1。'
                  : 'Cognitive depth based on Bloom\'s taxonomy (1-5). LLM-structured review classifies questions as recall (1), comprehension (2), application (3), analysis (4), or synthesis (5). Score normalised to 0-1.'}
              </p>
              <p className="text-muted-foreground/70 text-[10px]">
                {isFr ? '评估器：QuestionDepthEvaluator (CorrectnessEvaluator)' : 'Evaluator: QuestionDepthEvaluator (CorrectnessEvaluator)'}
              </p>
            </div>
            {/* Answer Quality */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-foreground">
                <Sparkles className="h-3.5 w-3.5 text-blue-400" />
                <span>{isFr ? '回答质量' : 'Answer Quality'}</span>
              </div>
              <p className="text-muted-foreground">
                {isFr
                  ? '忠实度：回答是否基于检索到的上下文（不编造）。答案相关性：回答是否切题回答了用户问题。两项均为 0-1 分，由 LLM 评审。'
                  : 'Faithfulness: Is the answer grounded in retrieved context (no hallucination)? Answer Relevancy: Does the answer address the user\'s question? Both 0-1 via LLM judge.'}
              </p>
              <p className="text-muted-foreground/70 text-[10px]">
                {isFr ? '评估器：FaithfulnessEvaluator + AnswerRelevancyEvaluator' : 'Evaluators: FaithfulnessEvaluator + AnswerRelevancyEvaluator'}
              </p>
            </div>
            {/* Citation Quality */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-foreground">
                <BookOpen className="h-3.5 w-3.5 text-amber-400" />
                <span>{isFr ? '引用质量' : 'Citation Quality'}</span>
              </div>
              <p className="text-muted-foreground">
                {isFr
                  ? '上下文相关性：检索到的文档片段是否与问题相关。来源相关性：检索结果与最终回答的对齐程度。均为 0-1 分。'
                  : 'Context Relevancy: Are retrieved chunks relevant to the question? Source Relevancy: How well do sources align with the final answer? Both 0-1.'}
              </p>
              <p className="text-muted-foreground/70 text-[10px]">
                {isFr ? '评估器：ContextRelevancyEvaluator + RelevancyEvaluator' : 'Evaluators: ContextRelevancyEvaluator + RelevancyEvaluator'}
              </p>
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-border/30 text-[10px] text-muted-foreground/60">
            {isFr
              ? '所有评估基于 LlamaIndex 评估框架，使用配置的 LLM（当前：Azure GPT-4o-mini）作为评审模型。评估不会重新运行 RAG 流水线，直接使用已有的 (问题, 回答, 来源) 数据。'
              : 'All evaluations powered by LlamaIndex evaluation framework using the configured LLM (currently: Azure GPT-4o-mini) as judge. Evaluations do NOT re-run the RAG pipeline — they use existing (question, answer, sources) data.'}
          </div>
        </div>
      )}

      {/* ── Main area ─────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Column 1: Session sidebar ────────────────────── */}
        <div className="flex flex-col bg-muted/30 shrink-0 border-r border-border" style={{ width: sidebarWidth }}>
          <div className="px-3 py-3 border-b border-border flex items-center gap-2">
            <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-foreground flex-1">
              {isFr ? '对话记录' : 'Sessions'}
              {filteredSessions.length > 0 && (
                <span className="ml-1 text-[9px] text-muted-foreground font-normal">({filteredSessions.length})</span>
              )}
            </span>
            <button
              type="button"
              onClick={loadSessions}
              className="p-1 rounded hover:bg-secondary transition-colors"
              title={isFr ? '刷新' : 'Refresh'}
            >
              <RotateCcw className={cn('h-3 w-3 text-muted-foreground', sessionsLoading && 'animate-spin')} />
            </button>
          </div>

          {/* Admin user scope toggle */}
          {isAdmin && (
            <div className="px-3 py-1.5 border-b border-border/50">
              <div className="flex gap-1 rounded-md bg-muted/50 p-0.5">
                <button
                  type="button"
                  onClick={() => setUserScope('mine')}
                  className={cn(
                    'flex-1 flex items-center justify-center gap-1 rounded px-2 py-1 text-[10px] font-medium transition-colors',
                    userScope === 'mine'
                      ? 'bg-card text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  <User className="h-3 w-3" />
                  {isFr ? '我的' : 'Mine'}
                </button>
                <button
                  type="button"
                  onClick={() => setUserScope('all')}
                  className={cn(
                    'flex-1 flex items-center justify-center gap-1 rounded px-2 py-1 text-[10px] font-medium transition-colors',
                    userScope === 'all'
                      ? 'bg-card text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  <Users className="h-3 w-3" />
                  {isFr ? '全部' : 'All'}
                </button>
              </div>
            </div>
          )}

          {/* Time filter */}
          <div className="px-3 py-1.5 border-b border-border/50">
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value as typeof timeFilter)}
              className="w-full text-[10px] bg-transparent text-muted-foreground border border-border/50 rounded px-1.5 py-1 focus:outline-none focus:border-primary/50"
            >
              <option value="all">{isFr ? '全部时间' : 'All time'}</option>
              <option value="today">{isFr ? '今天' : 'Today'}</option>
              <option value="7d">{isFr ? '最近 7 天' : 'Last 7 days'}</option>
              <option value="30d">{isFr ? '最近 30 天' : 'Last 30 days'}</option>
            </select>
          </div>

          {/* Session list */}
          <div className="flex-1 overflow-y-auto">
            {sessionsLoading && sessions.length === 0 && (
              <div className="flex items-center justify-center h-24">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            )}

            {!sessionsLoading && filteredSessions.length === 0 && (
              <div className="flex flex-col items-center justify-center h-32 text-center px-3">
                <Search className="h-5 w-5 text-muted-foreground/30 mb-2" />
                <p className="text-[10px] text-muted-foreground">
                  {isFr ? '暂无对话记录' : 'No sessions found'}
                </p>
              </div>
            )}

            {filteredSessions.map((s) => {
              const isSelected = selectedSession?.id === s.id
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleSelectSession(s)}
                  className={cn(
                    'w-full text-left px-3 py-2.5 border-b border-border/50 transition-colors group relative',
                    isSelected
                      ? 'bg-primary/5 border-l-2 border-l-primary'
                      : 'hover:bg-secondary/50',
                  )}
                >
                  <p className="text-[11px] text-foreground line-clamp-2 leading-relaxed pr-2">
                    {s.title}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="text-[9px] text-muted-foreground">
                      {s.createdAt ? new Date(s.createdAt).toLocaleDateString() : '—'}
                    </span>
                    <span className="text-[9px] text-muted-foreground/50">
                      {s.queryCount} {isFr ? '轮' : 'turns'}
                    </span>
                    {isSelected && autoEvalRunning && (
                      <Loader2 className="h-2.5 w-2.5 animate-spin text-primary ml-auto" />
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Sidebar resize handle */}
        <div
          className="w-1 shrink-0 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors relative group"
          onMouseDown={createDragHandler(setSidebarWidth, 180, 400)}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>

        {/* ── Main content: Two-panel synced scroll ─────────── */}
        {!selectedSession ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
              <Zap className="h-8 w-8 text-muted-foreground/30" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">
              {isFr ? '选择对话开始评估' : 'Select a Session to Evaluate'}
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm">
              {isFr
                ? '从左侧选择一个对话，系统将自动评估所有问答对的质量，结果与对话内容对齐展示'
                : 'Select a session from the left. All Q&A pairs will be evaluated automatically with results shown alongside the conversation.'}
            </p>
          </div>
        ) : queriesLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="text-xs text-muted-foreground">{isFr ? '加载对话…' : 'Loading…'}</span>
            </div>
          </div>
        ) : sessionQueries.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <Search className="h-6 w-6 text-muted-foreground/30 mb-2" />
            <p className="text-xs text-muted-foreground">
              {isFr ? '此对话暂无查询记录' : 'No queries in this session'}
            </p>
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">

            {/* ── Left: Conversation replay ──────────────── */}
            <div
              ref={leftPanelRef}
              onScroll={handleLeftScroll}
              className="flex-1 overflow-y-auto"
            >
              <div className="p-5 space-y-1">
                {/* Session header */}
                <div className="text-[10px] text-muted-foreground bg-muted/50 rounded-lg px-3 py-1.5 flex items-center justify-between mb-4 sticky top-0 z-10 backdrop-blur-sm">
                  <span className="font-medium text-foreground text-[11px] line-clamp-1">
                    {selectedSession.title}
                  </span>
                  <span>
                    {sessionQueries.length} {isFr ? '轮对话' : 'turns'}
                  </span>
                </div>

                {sessionQueries.map((sq, idx) => (
                  <div
                    key={sq.id}
                    ref={el => { if (el) leftRowRefs.current.set(sq.id, el) }}
                    className="space-y-3 pb-4"
                    data-query-id={sq.id}
                  >
                    {/* Turn number badge */}
                    <div className="flex items-center gap-2 text-[9px] text-muted-foreground/50 px-1">
                      <div className="h-px flex-1 bg-border/50" />
                      <span>Turn {idx + 1}</span>
                      <div className="h-px flex-1 bg-border/50" />
                    </div>

                    {/* Q */}
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center">
                          <span className="text-[9px] font-bold text-primary">Q</span>
                        </div>
                        <span className="text-[9px] text-muted-foreground">
                          {sq.createdAt ? new Date(sq.createdAt).toLocaleString() : ''}
                        </span>
                      </div>
                      <div className="ml-7 rounded-xl bg-primary/5 border border-primary/20 px-3.5 py-2.5">
                        <p className="text-sm text-foreground leading-relaxed">
                          {sq.question}
                        </p>
                      </div>
                    </div>

                    {/* A */}
                    {sq.answer && (
                      <div>
                        <div className="flex items-center gap-2 mb-1.5">
                          <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                            <span className="text-[9px] font-bold text-emerald-500">A</span>
                          </div>
                          <span className="text-[9px] text-muted-foreground">
                            {sq.model || 'RAG Pipeline'}
                          </span>
                        </div>
                        <div className="ml-7 rounded-xl bg-card border border-border px-3.5 py-2.5">
                          <AnswerBlockRenderer
                            content={sq.answer}
                            sources={sq.sources}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* ── Right: Evaluation results (synced scroll) ── */}
            {/* Eval resize handle */}
            <div
              className="w-1 shrink-0 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors relative group"
              onMouseDown={createDragHandler(setEvalPanelWidth, 280, 600, true)}
            >
              <div className="absolute inset-y-0 -left-1 -right-1" />
              <GripVertical className="h-4 w-4 text-muted-foreground/30 group-hover:text-muted-foreground/60 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
            </div>
            <div
              ref={rightPanelRef}
              onScroll={handleRightScroll}
              className="shrink-0 overflow-y-auto bg-muted/10"
              style={{ width: evalPanelWidth }}
            >
              <div className="p-3 space-y-1">
                {/* Header */}
                <div className="flex items-center gap-2 bg-muted/50 rounded-lg px-3 py-1.5 mb-4 sticky top-0 z-10 backdrop-blur-sm">
                  <BarChart3 className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-[11px] font-medium text-foreground flex-1">
                    {isFr ? '评估结果' : 'Evaluation Results'}
                  </span>
                  {evalProgress.total > 0 && (
                    <span className="text-[9px] text-muted-foreground">
                      {evalProgress.done}/{evalProgress.total}
                    </span>
                  )}
                </div>

                {sessionQueries.map((sq, idx) => (
                  <div
                    key={sq.id}
                    ref={el => { if (el) rightRowRefs.current.set(sq.id, el) }}
                    className="pb-4"
                    data-query-id={sq.id}
                  >
                    {/* Turn label */}
                    <div className="flex items-center gap-2 text-[9px] text-muted-foreground/50 px-1 mb-2">
                      <div className="h-px flex-1 bg-border/50" />
                      <span>Turn {idx + 1}</span>
                      <div className="h-px flex-1 bg-border/50" />
                    </div>

                    {/* Eval card */}
                    <div className="rounded-xl border border-border bg-card/80 min-h-[120px]">
                      {renderEvalCard(sq.id)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
