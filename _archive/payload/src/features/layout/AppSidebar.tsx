'use client'

import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Plus,
  Library,
  BarChart3,
  LineChart,
  ThumbsUp,
  Brain,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Trash2,
  Zap,
  MessageSquareDot,
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
import { useChatHistoryContext } from '@/features/chat/history/ChatHistoryContext'
import type { ChatSession } from '@/features/chat/history/useChatHistory'

/** Group sessions by recency label */
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

/**
 * AppSidebar — GPT-style left nav
 *
 * Layout (expanded):
 *  ┌────────────────────┐
 *  │ Logo               │  ← shrink-0
 *  │ + New Chat         │  ← shrink-0
 *  │ ─── Today ───      │
 *  │  session title     │  ← flex-1, overflow-y-auto (chat history)
 *  │  session title     │
 *  │ ─── Yesterday ─── │
 *  │  session title     │
 *  ├────────────────────┤
 *  │ Library            │  ← shrink-0
 *  │ Analytics …        │
 *  ├────────────────────┤
 *  │ Settings  Collapse │  ← shrink-0
 *  └────────────────────┘
 */
export default function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { t } = useI18n()
  const [collapsed, setCollapsed] = useState(false)
  const { sessions, activeSessionId, deleteSession, clearHistory } = useChatHistoryContext()
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)

  // TODO: check user role from Payload
  const isAdmin = true

  const groups = groupByDay(sessions)

  const adminLinks = [
    { titleKey: 'navAnalytics', icon: BarChart3, href: '/dashboard/analytics' },
    { titleKey: 'navModels', icon: Brain, href: '/dashboard/models' },
    { titleKey: 'navPrompts', icon: FileText, href: '/dashboard/prompts' },
    { titleKey: 'navEvaluation', icon: LineChart, href: '/dashboard/evaluation' },
    { titleKey: 'navFeedback', icon: ThumbsUp, href: '/dashboard/feedback' },
    { titleKey: 'navPipeline', icon: Zap, href: '/dashboard/pipeline' },
  ] as const

  function navLink(href: string, Icon: React.ElementType, label: string) {
    const active = pathname === href || (href !== '/chat' && pathname.startsWith(href))
    const cls = cn(
      'flex items-center gap-3 h-9 rounded-lg text-sm font-medium transition-colors',
      collapsed ? 'justify-center px-0' : 'px-3',
      active
        ? 'bg-sidebar-accent text-sidebar-primary'
        : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
    )
    const el = (
      <Link href={href} className={cls}>
        <Icon size={18} />
        {!collapsed && <span>{label}</span>}
      </Link>
    )
    if (collapsed) {
      return (
        <Tooltip key={href}>
          <TooltipTrigger asChild>{el}</TooltipTrigger>
          <TooltipContent side="right" sideOffset={8}>{label}</TooltipContent>
        </Tooltip>
      )
    }
    return <div key={href}>{el}</div>
  }

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'flex flex-col h-full shrink-0 transition-all duration-200',
          'bg-sidebar border-r border-sidebar-border',
          collapsed ? 'w-16' : 'w-64',
        )}
      >
        {/* ── Logo ── */}
        <div className="flex items-center gap-2.5 px-4 py-3 border-b border-sidebar-border shrink-0">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#004890" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15z" />
          </svg>
          {!collapsed && (
            <span className="font-bold text-sm tracking-tight text-sidebar-foreground">
              {t.appName}
              <span className="text-[10px] font-mono ml-1 text-muted-foreground">{t.appVersion}</span>
            </span>
          )}
        </div>

        {/* ── New Chat button ── */}
        <div className={cn('shrink-0 py-2', collapsed ? 'px-2' : 'px-3')}>
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => router.push('/chat?new=1')}
                  className="flex h-9 w-full items-center justify-center rounded-lg bg-sidebar-accent text-sidebar-primary hover:opacity-80 transition-opacity"
                >
                  <Plus size={18} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>{String(t.navNewChat)}</TooltipContent>
            </Tooltip>
          ) : (
            <button
              type="button"
              onClick={() => router.push('/chat?new=1')}
              className="flex w-full items-center gap-2.5 rounded-lg bg-sidebar-accent px-3 h-9 text-sm font-medium text-sidebar-primary hover:opacity-80 transition-opacity"
            >
              <Plus size={16} />
              {String(t.navNewChat)}
            </button>
          )}
        </div>

        {/* ── Chat history list (fills remaining space) ── */}
        {!collapsed && (
          <div className="flex flex-1 min-h-0 flex-col">
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
                            {/* Delete button */}
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

            {/* Confirm clear overlay */}
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
        )}

        {/* Collapsed: spacer */}
        {collapsed && <div className="flex-1" />}

        {/* ── Secondary nav (Library + Admin) ── */}
        <div className={cn('shrink-0 border-t border-sidebar-border py-2', collapsed ? 'px-2' : 'px-2')}>
          {!collapsed && (
            <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {t.navGroupResources}
            </p>
          )}
          <nav className="flex flex-col gap-0.5">
            {navLink('/library', Library, String(t.navLibrary))}
            {navLink('/dashboard/questions', MessageSquareDot, String(t.navQuestions))}
          </nav>

          {isAdmin && (
            <>
              {!collapsed && (
                <p className="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {t.navGroupAdmin}
                </p>
              )}
              {collapsed && <div className="mx-auto my-1 h-px w-8 bg-sidebar-border" />}
              <nav className="flex flex-col gap-0.5">
                {adminLinks.map((item) => navLink(item.href, item.icon, String(t[item.titleKey])))}
              </nav>
            </>
          )}
        </div>

        {/* ── Bottom: Settings + Collapse ── */}
        <div className={cn('shrink-0 p-2 space-y-0.5 border-t border-sidebar-border', collapsed ? '' : '')}>
          <Link
            href="/settings"
            className={cn(
              'flex items-center gap-3 h-9 rounded-lg text-sm font-medium transition-colors',
              'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              collapsed ? 'justify-center px-0' : 'px-3',
            )}
          >
            <Settings size={18} />
            {!collapsed && <span>{t.settings}</span>}
          </Link>
          <button
            className={cn(
              'flex items-center gap-3 h-9 w-full rounded-lg text-sm font-medium transition-colors',
              'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              collapsed ? 'justify-center px-0' : 'px-3',
            )}
            onClick={() => setCollapsed((prev) => !prev)}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            {!collapsed && <span>{t.collapse}</span>}
          </button>
        </div>
      </aside>
    </TooltipProvider>
  )
}
