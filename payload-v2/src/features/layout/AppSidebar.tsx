'use client'

import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Plus,
  BarChart3,
  LineChart,
  ThumbsUp,
  Brain,
  FileText,
  Settings,
  PanelLeftClose,
  PanelLeft,
  MessageSquare,
  Trash2,
  MessageSquareDot,
  Database,
  Globe,
  Search,
} from 'lucide-react'
import { useState } from 'react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from '@/features/shared/components/ui/tooltip'
import { useAuth } from '@/features/shared/AuthProvider'
import { useChatHistoryContext } from '@/features/chat/history/ChatHistoryContext'
import type { ChatSession } from '@/features/chat/history/useChatHistory'

/* ── helpers ── */
function groupByDay(sessions: ChatSession[]) {
  const now = new Date()
  const todayStr = now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const yesterdayStr = yesterday.toDateString()

  const map = new Map<string, ChatSession[]>()
  for (const s of sessions) {
    const d = new Date(s.updatedAt)
    let label: string
    if (d.toDateString() === todayStr) label = 'Today'
    else if (d.toDateString() === yesterdayStr) label = 'Yesterday'
    else {
      const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000)
      if (diffDays < 7) label = 'This Week'
      else if (diffDays < 30) label = 'This Month'
      else label = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short' })
    }
    if (!map.has(label)) map.set(label, [])
    map.get(label)!.push(s)
  }
  const groups: { label: string; items: ChatSession[] }[] = []
  for (const [label, items] of map) groups.push({ label, items })
  return groups
}

const SIDEBAR_KEY = 'app-sidebar-collapsed'

/** CSS transition timing — shared across width + opacity */
const DURATION = 'duration-200'

/**
 * AppSidebar — GPT-style collapsible sidebar
 *
 * 关键优化：不做条件渲染，所有 DOM 始终存在。
 * collapsed 只改 CSS (width / opacity / overflow)，GPU 合成层动画，零卡顿。
 */
export default function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { t } = useI18n()
  // Persist collapsed state in localStorage so it survives refresh
  const [collapsed, setCollapsedRaw] = useState(() => {
    if (typeof window === 'undefined') return false
    try { return localStorage.getItem(SIDEBAR_KEY) === '1' } catch { return false }
  })
  const setCollapsed = (v: boolean) => {
    setCollapsedRaw(v)
    try { localStorage.setItem(SIDEBAR_KEY, v ? '1' : '0') } catch {}
  }
  const { sessions, activeSessionId, deleteSession, clearHistory } = useChatHistoryContext()
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)

  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const groups = groupByDay(sessions)

  // ── Admin nav: single flat list ordered by RAG pipeline execution flow ──
  // Import → Library → LLMs → Prompts → Query Engine → Evaluation → Feedback → Analytics → Seed
  const adminLinks = [
    { titleKey: 'navAcquisition', icon: Globe, href: '/engine/acquisition' },
    { titleKey: 'navLlms', icon: Brain, href: '/engine/llms' },
    { titleKey: 'navResponseSynthesizers', icon: FileText, href: '/engine/response_synthesizers' },
    { titleKey: 'navRetrievers', icon: Search, href: '/engine/retrievers' },
    { titleKey: 'navQueryEngine', icon: MessageSquare, href: '/engine/query_engine' },
    { titleKey: 'navEvaluation', icon: LineChart, href: '/engine/evaluation' },
    { titleKey: 'navFeedback', icon: ThumbsUp, href: '/engine/feedback' },
    { titleKey: 'navAnalytics', icon: BarChart3, href: '/engine/analytics' },
    { titleKey: 'navSeed', icon: Database, href: '/seed' },
  ] as const

  /* ── Label: opacity+width transition, no DOM swap ── */
  const labelCls = cn(
    'whitespace-nowrap overflow-hidden transition-all', DURATION,
    collapsed ? 'w-0 opacity-0' : 'w-auto opacity-100',
  )

  /** Nav link — always renders icon + label; label fades via CSS */
  function navLink(href: string, Icon: React.ElementType, label: string) {
    const active = pathname === href || (href !== '/chat' && pathname.startsWith(href))
    const link = (
      <Link
        href={href}
        className={cn(
          'flex items-center gap-3 h-9 rounded-lg text-sm font-medium transition-colors',
          collapsed ? 'justify-center px-0' : 'px-3',
          active
            ? 'bg-sidebar-accent text-sidebar-primary'
            : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
        )}
      >
        <Icon size={18} className="shrink-0" />
        <span className={labelCls}>{label}</span>
      </Link>
    )

    return (
      <Tooltip key={href}>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        {collapsed && <TooltipContent side="right" sideOffset={8}>{label}</TooltipContent>}
      </Tooltip>
    )
  }

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'flex flex-col h-full shrink-0 overflow-hidden',
          'bg-sidebar border-r border-sidebar-border',
          collapsed ? 'w-[52px]' : 'w-64',
        )}
        style={{
          transition: 'width 200ms cubic-bezier(0.4, 0, 0.2, 1)',
          willChange: 'width',
        }}
      >
        {/* ── Top bar: Logo + Toggle (merged) ── */}
        <div className="flex items-center shrink-0 border-b border-sidebar-border h-12 px-2 gap-2">
          {/* Logo icon — when collapsed, clicking it expands the sidebar */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => { if (collapsed) setCollapsed(false); else router.push('/chat') }}
                className="flex items-center justify-center h-9 w-9 shrink-0 rounded-lg hover:bg-sidebar-accent transition-colors"
              >
                {collapsed ? (
                  <PanelLeft size={18} className="text-muted-foreground" />
                ) : (
                  <img src="/ottawa-logo.jpg" alt="Ottawa" className="h-5 w-5 rounded-sm object-contain" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={8}>
              {collapsed ? 'Expand sidebar' : t.appName}
            </TooltipContent>
          </Tooltip>

          {/* Title — fades/collapses via CSS */}
          <span className={cn('font-bold text-sm tracking-tight text-sidebar-foreground truncate min-w-0 transition-all', DURATION, collapsed ? 'w-0 opacity-0' : 'flex-1 opacity-100')}>
            {t.appName}
            <span className="text-[10px] font-mono ml-1 text-muted-foreground">{t.appVersion}</span>
          </span>

          {/* Collapse button — right side, fades out when collapsed */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => setCollapsed(true)}
                className={cn(
                  'flex items-center justify-center h-8 w-8 shrink-0 rounded-lg transition-all',
                  'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  DURATION,
                  collapsed ? 'w-0 opacity-0 overflow-hidden' : 'opacity-100',
                )}
              >
                <PanelLeftClose size={18} />
              </button>
            </TooltipTrigger>
            {!collapsed && <TooltipContent side="right" sideOffset={8}>Collapse sidebar</TooltipContent>}
          </Tooltip>
        </div>

        {/* ── New Chat button ── */}
        <div className={cn('shrink-0 py-2', collapsed ? 'px-1.5' : 'px-3')}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => router.push('/chat?new=1')}
                className={cn(
                  'flex items-center gap-2.5 h-9 w-full rounded-lg bg-sidebar-accent text-sidebar-primary hover:opacity-80 transition-opacity text-sm font-medium',
                  collapsed ? 'justify-center px-0' : 'px-3',
                )}
              >
                <Plus size={16} className="shrink-0" />
                <span className={labelCls}>{String(t.navNewChat)}</span>
              </button>
            </TooltipTrigger>
            {collapsed && <TooltipContent side="right" sideOffset={8}>{String(t.navNewChat)}</TooltipContent>}
          </Tooltip>
        </div>

        {/* ── Chat history (hidden when collapsed via CSS) ── */}
        <div className={cn(
          'flex-1 min-h-0 flex flex-col overflow-hidden transition-all', DURATION,
          collapsed ? 'opacity-0 pointer-events-none' : 'opacity-100',
        )}>
          {/* Section header */}
          {sessions.length > 0 && (
            <div className="shrink-0 flex items-center justify-between px-4 pb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Chat History
              </span>
              <button
                type="button"
                onClick={() => setConfirmClear(true)}
                className="text-[10px] text-muted-foreground hover:text-destructive transition-colors"
                title="Clear all history"
              >
                Clear
              </button>
            </div>
          )}

          {/* Session list */}
          <div className="flex-1 min-h-0 overflow-y-auto pb-2">
            {sessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                <MessageSquare size={24} className="text-muted-foreground/40 mb-2" />
                <p className="text-xs text-muted-foreground">No conversations yet</p>
              </div>
            ) : (
              <div className="py-0.5">
                {groups.map(({ label, items }) => (
                  <div key={label}>
                    <div className="sticky top-0 z-10 bg-sidebar px-3 py-1">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {label}
                      </span>
                    </div>
                    {items.map((session) => {
                      const isActive = session.id === activeSessionId && pathname === '/chat'
                      const isHovered = hoveredId === session.id
                      return (
                        <div
                          key={session.id}
                          className="group relative px-2"
                          onMouseEnter={() => setHoveredId(session.id)}
                          onMouseLeave={() => setHoveredId(null)}
                        >
                          <button
                            type="button"
                            onClick={() => router.push(`/chat?session=${session.id}`)}
                            className={cn(
                              'w-full rounded-lg px-2.5 py-2 text-left text-xs transition-colors',
                              isActive
                                ? 'bg-sidebar-accent text-sidebar-primary font-medium'
                                : 'text-sidebar-foreground hover:bg-sidebar-accent/60',
                            )}
                          >
                            <p className="truncate leading-snug pr-5">{session.title}</p>
                            {session.bookTitles.length > 0 && (
                              <p className="truncate text-[10px] text-muted-foreground mt-0.5 pr-5">
                                {session.bookTitles.slice(0, 2).join(', ')}
                                {session.bookTitles.length > 2 && ` +${session.bookTitles.length - 2}`}
                              </p>
                            )}
                          </button>
                          {isHovered && (
                            <button
                              type="button"
                              onClick={(e) => { e.stopPropagation(); deleteSession(session.id) }}
                              className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-destructive transition-colors"
                              title="Delete"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Confirm clear */}
          {confirmClear && (
            <div className="shrink-0 mx-3 mb-2 rounded-lg border border-border bg-card p-3 shadow-sm">
              <p className="text-xs text-foreground mb-2">Clear all history?</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => { clearHistory(); setConfirmClear(false) }}
                  className="flex-1 rounded bg-destructive px-2 py-1 text-[11px] font-medium text-destructive-foreground hover:opacity-80"
                >
                  Clear all
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmClear(false)}
                  className="flex-1 rounded border border-border bg-background px-2 py-1 text-[11px] font-medium text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Resources (all users) ── */}
        <div className={cn('shrink-0 border-t border-sidebar-border py-2', collapsed ? 'px-1' : 'px-2')}>
          <p className={cn('px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground transition-all', DURATION, collapsed ? 'h-0 opacity-0 overflow-hidden py-0' : 'opacity-100')}>
            {t.navGroupResources}
          </p>
          <nav className="flex flex-col gap-0.5">
            {navLink('/engine/question_gen', MessageSquareDot, String(t.navQuestionGen))}
            {navLink('/reports', FileText, String(t.navReports))}
            {navLink('/settings', Settings, String(t.settings))}
          </nav>
        </div>

        {/* ── Admin (role-gated, single flat list by pipeline execution order) ── */}
        {isAdmin && (
          <div className={cn('shrink-0 border-t border-sidebar-border py-2', collapsed ? 'px-1' : 'px-2')}>
            <p className={cn('px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground transition-all', DURATION, collapsed ? 'h-0 opacity-0 overflow-hidden py-0' : 'opacity-100')}>
              {t.navGroupAdmin}
            </p>
            {collapsed && <div className="mx-auto my-1 h-px w-8 bg-sidebar-border" />}
            <nav className="flex flex-col gap-0.5">
              {adminLinks.map((item) => navLink(item.href, item.icon, String(t[item.titleKey])))}
            </nav>
          </div>
        )}
      </aside>
    </TooltipProvider>
  )
}
