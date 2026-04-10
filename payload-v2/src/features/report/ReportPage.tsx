/**
 * ReportPage — Report generation + list + preview + PDF export.
 *
 * Layout: left sidebar (session/report history) + right pane (Markdown preview).
 * Mirrors the Evaluation module's sidebar pattern: default shows chat session
 * history, selecting a session generates or loads an existing report.
 *
 * Data flow: Payload /api/chat-sessions + /api/reports (read) → Engine /report/* (generate/PDF).
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  FileText,
  Download,
  RefreshCw,
  Plus,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  MessageSquare,
  Search,
  RotateCcw,
  Users,
  User,
  GripVertical,
} from 'lucide-react'
import Markdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import { cn } from '@/features/shared/utils'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n/I18nProvider'

// ============================================================
// Constants
// ============================================================
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Types
// ============================================================
interface Report {
  id: number
  title: string
  content: string
  sessionId: string
  sessionTitle?: string
  model?: string
  status: 'generating' | 'completed' | 'failed'
  stats?: {
    messageCount?: number
    sourceCount?: number
    avgScores?: Record<string, number>
    questionDepths?: Record<string, number>
  }
  createdAt: string
  updatedAt?: string
}

interface SessionListItem {
  id: number
  title: string
  createdAt: string
  queryCount: number
  hasReport: boolean
}

type UserScope = 'mine' | 'all'
type TimeFilter = 'all' | 'today' | '7d' | '30d'

// ============================================================
// API helpers
// ============================================================

/** Generic typed fetch wrapper. */
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

/** Fetch chat sessions from Payload (same as evaluation sidebar pattern). */
async function fetchSessions(
  limit: number = 50,
  userId?: number,
): Promise<SessionListItem[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    sort: '-createdAt',
  })
  if (userId) {
    params.set('where[user][equals]', String(userId))
  }
  const data = await request<{ docs: any[]; totalDocs: number }>(
    `/api/chat-sessions?${params}`,
  )

  // Count user-role messages per session via ChatMessages
  const sessionIds = data.docs.map((d: any) => d.id)
  let queryCounts: Record<string, number> = {}

  if (sessionIds.length > 0) {
    try {
      const msgParams = new URLSearchParams({
        limit: '0',
        'where[role][equals]': 'user',
        'where[session][in]': sessionIds.join(','),
      })
      const msgData = await request<{ docs: any[] }>(
        `/api/chat-messages?${msgParams}`,
      )
      for (const m of msgData.docs) {
        const sid = String(typeof m.session === 'object' ? m.session?.id : m.session)
        queryCounts[sid] = (queryCounts[sid] || 0) + 1
      }
    } catch {
      // ChatMessages unavailable
    }
  }

  // Check which sessions already have reports
  let reportSessionIds = new Set<string>()
  try {
    const reportParams = new URLSearchParams({
      limit: '200',
      'where[status][equals]': 'completed',
    })
    const reportData = await request<{ docs: any[] }>(
      `/api/reports?${reportParams}`,
    )
    for (const r of reportData.docs) {
      if (r.sessionId) reportSessionIds.add(String(r.sessionId))
    }
  } catch {
    // Reports collection unavailable
  }

  return data.docs.map((d: any) => ({
    id: d.id,
    title: d.title ?? 'Untitled Session',
    createdAt: d.createdAt ?? '',
    queryCount: queryCounts[String(d.id)] || 0,
    hasReport: reportSessionIds.has(String(d.id)),
  }))
}

/** Fetch reports from Payload CMS. */
async function fetchReports(sessionId?: number): Promise<Report[]> {
  const params = new URLSearchParams({
    limit: '50',
    sort: '-createdAt',
  })
  if (sessionId) {
    params.set('where[sessionId][equals]', String(sessionId))
  }
  const data = await request<{ docs: any[] }>(`/api/reports?${params}`)
  return data.docs.map((d: any) => ({
    id: d.id,
    title: d.title ?? 'Untitled Report',
    content: d.content ?? '',
    sessionId: d.sessionId ?? '',
    sessionTitle: d.sessionTitle ?? null,
    model: d.model ?? null,
    status: d.status ?? 'completed',
    stats: d.stats ?? null,
    createdAt: d.createdAt ?? '',
    updatedAt: d.updatedAt ?? null,
  }))
}

/** Generate a report from a session via the Engine API. */
async function generateReport(sessionId: string): Promise<Report> {
  const resp = await fetch(`${ENGINE_URL}/engine/report/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || 'Report generation failed')
  }
  const data = await resp.json()
  return data.report
}

/** Download report as PDF via the Engine API. */
function downloadPdf(reportId: number, title: string) {
  const url = `${ENGINE_URL}/engine/report/${reportId}/pdf`
  const a = document.createElement('a')
  a.href = url
  a.download = `${title}.pdf`
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// ============================================================
// Sub-components
// ============================================================

/** Status badge for report cards */
function StatusBadge({ status }: { status: Report['status'] }) {
  const config = {
    generating: { icon: Loader2, label: 'Generating', cls: 'text-amber-600 bg-amber-500/10' },
    completed: { icon: CheckCircle2, label: 'Completed', cls: 'text-green-600 bg-green-500/10' },
    failed: { icon: AlertCircle, label: 'Failed', cls: 'text-red-500 bg-red-500/10' },
  }
  const { icon: Icon, label, cls } = config[status]
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium', cls)}>
      <Icon size={12} className={status === 'generating' ? 'animate-spin' : ''} />
      {label}
    </span>
  )
}

/** Score card for quality assessment display */
function ScoreCard({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100)
  const grade = pct >= 85 ? 'Excellent' : pct >= 70 ? 'Good' : pct >= 50 ? 'Fair' : 'Poor'
  const color = pct >= 85 ? 'text-emerald-500' : pct >= 70 ? 'text-blue-500' : pct >= 50 ? 'text-amber-500' : 'text-red-500'
  const barColor = pct >= 85 ? 'bg-emerald-500' : pct >= 70 ? 'bg-blue-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  const bgColor = pct >= 85 ? 'bg-emerald-500/5' : pct >= 70 ? 'bg-blue-500/5' : pct >= 50 ? 'bg-amber-500/5' : 'bg-red-500/5'
  return (
    <div className={cn('rounded-lg border border-border p-3 space-y-2', bgColor)}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground capitalize">{label}</span>
        <span className={cn('text-xs font-semibold', color)}>{grade}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-muted/60 overflow-hidden">
          <div className={cn('h-full rounded-full transition-all duration-500', barColor)} style={{ width: `${pct}%` }} />
        </div>
        <span className={cn('text-sm font-bold tabular-nums', color)}>{pct}%</span>
      </div>
    </div>
  )
}

/**
 * Preprocess LLM-generated report content to ensure proper Markdown heading syntax.
 *
 * The LLM sometimes generates headings without `#` markers (e.g. "1. Executive Summary")
 * or as bold-only lines (e.g. "**Location of Course Outline:**").
 * This function converts those patterns into proper Markdown headings.
 */
function preprocessMarkdown(content: string): string {
  return content
    .split('\n')
    .map((line) => {
      const trimmed = line.trim()

      // Skip lines that already have heading markers
      if (/^#{1,6}\s/.test(trimmed)) return line

      // "Research Report: ..." or "Report: ..." at start → H1
      if (/^Research Report:/i.test(trimmed) || /^Report:/i.test(trimmed)) {
        return `# ${trimmed}`
      }

      // Numbered section headers: "1. Executive Summary", "2. Key Findings", etc.
      // Only match if the text after the number looks like a title (capitalized, no trailing period sentence)
      if (/^\d+\.\s+[A-Z][A-Za-z\s&:,/()-]+$/.test(trimmed) && trimmed.length < 80) {
        return `## ${trimmed}`
      }

      // Bold-only lines that act as sub-headings: "**Something Something:**" or "**Something**"
      if (/^\*\*[^*]+\*\*:?\s*$/.test(trimmed) && trimmed.length < 120) {
        const inner = trimmed.replace(/^\*\*/, '').replace(/\*\*:?\s*$/, '')
        return `### ${inner}`
      }

      return line
    })
    .join('\n')
}

/** Animated progress steps shown during report generation (frontend-only). */
function GenerationProgress({ sessionTitle, isFr }: { sessionTitle: string; isFr: boolean }) {
  const [currentStep, setCurrentStep] = useState(0)

  const steps = [
    { label: isFr ? '收集对话消息' : 'Collecting chat messages' },
    { label: isFr ? '获取评估数据' : 'Fetching evaluation data' },
    { label: isFr ? '分析对话模式' : 'Analyzing conversation patterns' },
    { label: isFr ? '构建报告大纲' : 'Building report outline' },
    { label: isFr ? '撰写报告章节' : 'Writing report sections' },
    { label: isFr ? '最终格式化' : 'Finalizing document' },
  ]

  useEffect(() => {
    const delays = [1800, 3500, 6000, 9000, 14000]
    const timers = delays.map((delay, i) =>
      setTimeout(() => setCurrentStep(i + 1), delay),
    )
    return () => timers.forEach(clearTimeout)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const progress = Math.min(((currentStep + 1) / steps.length) * 100, 95)

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Title */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 mb-4">
            <Loader2 size={14} className="animate-spin text-primary" />
            <span className="text-xs font-medium text-primary">
              {isFr ? '生成报告中' : 'Generating Report'}
            </span>
          </div>
          <p className="text-sm text-muted-foreground truncate">{sessionTitle}</p>
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-1000 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-[10px] text-muted-foreground/60 text-right tabular-nums">
            {Math.round(progress)}%
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-0">
          {steps.map((step, i) => {
            const isDone = i < currentStep
            const isCurrent = i === currentStep
            const isPending = i > currentStep
            return (
              <div
                key={i}
                className={cn(
                  'flex items-center gap-3 py-2 transition-all duration-500',
                  isPending && 'opacity-30',
                )}
              >
                <div className="shrink-0 w-5 h-5 flex items-center justify-center">
                  {isDone ? (
                    <CheckCircle2 size={16} className="text-green-500" />
                  ) : isCurrent ? (
                    <Loader2 size={16} className="animate-spin text-primary" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/20" />
                  )}
                </div>
                <span
                  className={cn(
                    'text-sm transition-colors duration-300',
                    isDone && 'text-green-600 dark:text-green-400',
                    isCurrent && 'text-foreground font-medium',
                    isPending && 'text-muted-foreground',
                  )}
                >
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Main component
// ============================================================
export default function ReportPage() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  // ── State ──
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [selectedSession, setSelectedSession] = useState<SessionListItem | null>(null)
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── Filters ──
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all')
  const [userScope, setUserScope] = useState<UserScope>('mine')

  // ── Resizable sidebar ──
  const [sidebarWidth, setSidebarWidth] = useState(280)

  // ── Load sessions ──
  const loadSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const scopedUserId = (isAdmin && userScope === 'all') ? undefined : user?.id
      const list = await fetchSessions(100, scopedUserId)
      setSessions(list)
    } catch {
      // Payload unavailable
    } finally {
      setSessionsLoading(false)
    }
  }, [user?.id, isAdmin, userScope])

  // Auto-load sessions
  useEffect(() => {
    if (user === undefined) return
    loadSessions()
  }, [user?.id, userScope]) // eslint-disable-line react-hooks/exhaustive-deps

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

  /** Create a drag handler for resizable panels. */
  const createDragHandler = useCallback(
    (setter: React.Dispatch<React.SetStateAction<number>>, min: number, max: number) => {
      return (e: React.MouseEvent) => {
        e.preventDefault()
        const startX = e.clientX
        let startWidth = 0
        setter(w => { startWidth = w; return w })

        const onMove = (ev: MouseEvent) => {
          const delta = ev.clientX - startX
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

  /** Select a session — load existing report or prepare to generate one. */
  const handleSelectSession = useCallback(async (s: SessionListItem) => {
    setSelectedSession(s)
    setSelectedReport(null)
    setError(null)

    // Try to load existing report for this session
    try {
      const reports = await fetchReports(s.id)
      if (reports.length > 0) {
        // Use the most recent completed report, or the first one
        const completed = reports.find(r => r.status === 'completed')
        setSelectedReport(completed || reports[0])
      }
    } catch {
      // No existing report — user can generate one
    }
  }, [])

  /** Generate/regenerate report from selected session. */
  const handleGenerate = async () => {
    if (!selectedSession) return
    setGenerating(true)
    setError(null)
    try {
      const report = await generateReport(String(selectedSession.id))
      setSelectedReport(report)
      // Refresh sessions to update hasReport badges
      await loadSessions()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  // ============================================================
  // Render
  // ============================================================
  return (
    <div className="flex flex-col h-full">

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
        <FileText className="h-5 w-5 text-blue-400" />
        <div className="flex-1">
          <h1 className="text-lg font-bold text-foreground">
            {isFr ? '研究报告' : 'Research Reports'}
          </h1>
          <p className="text-xs text-muted-foreground">
            {isFr
              ? '选择对话 → 生成结构化研究报告 → 导出 PDF'
              : 'Select a session → generate structured analysis report → export PDF'}
          </p>
        </div>
      </div>

      {/* ── Main area ─────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Column 1: Session sidebar  ────────────────────── */}
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
              onChange={(e) => setTimeFilter(e.target.value as TimeFilter)}
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
                <p className="text-[9px] text-muted-foreground/60 mt-0.5">
                  {isFr ? '先在 Chat 中开始对话' : 'Start a conversation in Chat first'}
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
                    {s.hasReport && (
                      <span className="ml-auto inline-flex items-center gap-0.5 text-[8px] text-green-500 bg-green-500/10 px-1.5 py-0.5 rounded-full">
                        <FileText className="h-2.5 w-2.5" />
                        {isFr ? '已有报告' : 'Report'}
                      </span>
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
          onMouseDown={createDragHandler(setSidebarWidth, 200, 420)}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>

        {/* ── Right pane: report preview ── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {error && (
            <div className="shrink-0 mx-4 mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-600 dark:border-red-900 dark:bg-red-950/30 dark:text-red-400 flex items-center gap-2">
              <AlertCircle size={14} />
              {error}
              <button type="button" onClick={() => setError(null)} className="ml-auto hover:text-red-800 dark:hover:text-red-300">
                <X size={14} />
              </button>
            </div>
          )}

          {generating ? (
            <GenerationProgress
              sessionTitle={selectedSession?.title || ''}
              isFr={isFr}
            />
          ) : selectedReport ? (
            <>
              {/* Toolbar */}
              <div className="shrink-0 flex items-center justify-between border-b border-border px-6 py-3">
                <div className="min-w-0 flex-1">
                  <h1 className="text-base font-bold text-foreground truncate">
                    {selectedReport.title}
                  </h1>
                  <div className="flex items-center gap-3 mt-0.5 text-[11px] text-muted-foreground">
                    <StatusBadge status={selectedReport.status} />
                    <span>{new Date(selectedReport.createdAt).toLocaleDateString(undefined, {
                      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}</span>
                    {selectedReport.model && <span>Model: {selectedReport.model}</span>}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Regenerate */}
                  <button
                    type="button"
                    onClick={handleGenerate}
                    disabled={generating}
                    className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors disabled:opacity-40"
                    title={isFr ? '重新生成' : 'Regenerate'}
                  >
                    <RefreshCw size={13} className={generating ? 'animate-spin' : ''} />
                    {isFr ? '重新生成' : 'Regenerate'}
                  </button>

                  {/* Export PDF button */}
                  {selectedReport.status === 'completed' && (
                    <button
                      type="button"
                      onClick={() => downloadPdf(selectedReport.id, selectedReport.title)}
                      className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity"
                    >
                      <Download size={14} />
                      Export PDF
                    </button>
                  )}
                </div>
              </div>

              {/* Quality scores summary (if available) */}
              {selectedReport.stats?.avgScores && Object.keys(selectedReport.stats.avgScores).length > 0 && (
                <div className="shrink-0 border-b border-border px-6 py-4 bg-muted/10">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                    Quality Assessment
                  </p>
                  <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
                    {Object.entries(selectedReport.stats.avgScores).map(([key, val]) => (
                      <ScoreCard key={key} label={key.replace(/_/g, ' ')} value={val} />
                    ))}
                  </div>
                </div>
              )}

              {/* Markdown content */}
              <div className="flex-1 overflow-y-auto">
                {selectedReport.status === 'generating' ? (
                  <div className="flex flex-col items-center justify-center py-24">
                    <Loader2 size={32} className="animate-spin text-primary mb-3" />
                    <p className="text-sm text-muted-foreground">
                      {isFr ? '正在生成报告...' : 'Generating report...'}
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-1">
                      {isFr ? '这可能需要一分钟' : 'This may take a minute'}
                    </p>
                  </div>
                ) : selectedReport.status === 'failed' ? (
                  <div className="flex flex-col items-center justify-center py-24 text-center px-8">
                    <AlertCircle size={32} className="text-red-400 mb-3" />
                    <p className="text-sm font-medium text-foreground">
                      {isFr ? '报告生成失败' : 'Report generation failed'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 max-w-md">
                      {selectedReport.content || (isFr ? '发生未知错误' : 'An unexpected error occurred')}
                    </p>
                    <button
                      type="button"
                      onClick={handleGenerate}
                      disabled={generating}
                      className="mt-4 flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity"
                    >
                      <RefreshCw size={14} />
                      {isFr ? '重试' : 'Retry'}
                    </button>
                  </div>
                ) : (
                  <div className="flex justify-center">
                    <article className="prose prose-sm w-full max-w-4xl px-8 py-8 dark:prose-invert
                      prose-headings:text-foreground prose-headings:font-bold
                      prose-h1:text-2xl prose-h1:border-b prose-h1:border-border prose-h1:pb-3 prose-h1:mb-6
                      prose-h2:text-xl prose-h2:mt-10 prose-h2:mb-4 prose-h2:text-primary
                      prose-h3:text-base prose-h3:mt-6 prose-h3:mb-2
                      prose-p:text-foreground/90 prose-p:leading-7 prose-p:mb-4
                      prose-strong:text-foreground prose-strong:font-semibold
                      prose-ul:text-foreground/90 prose-ul:my-3 prose-li:text-foreground/90 prose-li:my-1
                      prose-ol:text-foreground/90 prose-ol:my-3
                      prose-code:bg-muted prose-code:rounded prose-code:px-1.5 prose-code:py-0.5 prose-code:text-xs
                      prose-blockquote:border-l-primary/50 prose-blockquote:bg-muted/30 prose-blockquote:rounded-r-lg
                      prose-blockquote:text-muted-foreground prose-blockquote:not-italic prose-blockquote:py-1
                      prose-table:text-sm prose-th:text-left prose-th:text-foreground prose-th:font-semibold
                      prose-td:text-foreground/80
                      prose-hr:border-border prose-hr:my-8
                    ">
                      <Markdown
                        remarkPlugins={[remarkMath]}
                        rehypePlugins={[rehypeKatex, rehypeRaw]}
                      >
                        {preprocessMarkdown(selectedReport.content)}
                      </Markdown>
                    </article>
                  </div>
                )}
              </div>
            </>
          ) : selectedSession ? (
            /* Session selected but no report found — prompt to generate */
            <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
              <div className="rounded-2xl bg-muted/30 p-6 mb-4">
                <FileText size={48} className="text-muted-foreground/30" />
              </div>
              <h2 className="text-lg font-semibold text-foreground">
                {isFr ? '生成研究报告' : 'Generate Research Report'}
              </h2>
              <p className="text-sm text-muted-foreground mt-2 max-w-md">
                {isFr
                  ? `从对话「${selectedSession.title}」生成结构化研究报告，包含关键发现、质量评估和来源分析。`
                  : `Generate a structured analysis report from "${selectedSession.title}" with key findings, quality assessment, and source analysis.`}
              </p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                {selectedSession.queryCount} {isFr ? '轮对话' : 'turns in this session'}
              </p>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating}
                className="mt-6 flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40"
              >
                {generating ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    {isFr ? '生成中...' : 'Generating...'}
                  </>
                ) : (
                  <>
                    <Plus size={16} />
                    {isFr ? '生成报告' : 'Generate Report'}
                  </>
                )}
              </button>
            </div>
          ) : (
            /* No session selected — empty state */
            <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
              <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
                <FileText className="h-8 w-8 text-muted-foreground/30" />
              </div>
              <h3 className="text-sm font-semibold text-foreground mb-1">
                {isFr ? '选择对话生成报告' : 'Select a Session to Generate Report'}
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm">
                {isFr
                  ? '从左侧选择一个对话，系统将从对话内容生成结构化研究报告，包含关键发现、来源追溯和质量评估。'
                  : 'Select a session from the left. A structured research report will be generated from the conversation, including key findings, source tracing, and quality assessment.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
