'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  MessageSquare, BookOpen, ThumbsUp, Sparkles, User,
  Loader2, RefreshCw, Layers, Building2, Home,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type SidebarItem, type ViewMode } from '@/features/shared/components/SidebarLayout'

interface Question {
  id: number
  question: string
  bookId: string
  bookTitle: string | null
  topicHint: string | null
  source: 'ai' | 'manual'
  likes: number
  category: string | null
  subcategory: string | null
  createdAt: string
}

const SOURCE_CONFIG: Record<string, { icon: typeof Sparkles; label: string; color: string }> = {
  ai:     { icon: Sparkles, label: 'AI',     color: 'text-purple-400 bg-purple-500/10' },
  manual: { icon: User,     label: 'Manual', color: 'text-blue-400 bg-blue-500/10' },
}

const CATEGORY_CONFIG: Record<string, { label: string; labelZh: string; icon: typeof BookOpen; color: string }> = {
  textbook:    { label: 'Textbooks',      labelZh: '教材',     icon: BookOpen,  color: 'text-blue-400' },
  ecdev:       { label: 'EC Development', labelZh: '经济发展', icon: Building2, color: 'text-emerald-400' },
  real_estate: { label: 'Real Estate',    labelZh: '房地产',   icon: Home,      color: 'text-amber-400' },
}

export default function Page() {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  const [questions, setQuestions] = useState<Question[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('all')
  const [viewMode, setViewMode] = useState<ViewMode>('cards')
  const [likingIds, setLikingIds] = useState<Set<number>>(new Set())

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/questions?limit=500&sort=-likes')
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setQuestions(data.docs.map((d: any) => ({
        id: d.id,
        question: d.question,
        bookId: d.bookId ?? '',
        bookTitle: d.bookTitle ?? null,
        topicHint: d.topicHint ?? null,
        source: d.source ?? 'ai',
        likes: d.likes ?? 0,
        category: d.category ?? null,
        subcategory: d.subcategory ?? null,
        createdAt: d.createdAt ?? '',
      })))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Like handler
  const handleLike = async (id: number) => {
    setLikingIds((prev) => new Set(prev).add(id))
    const q = questions.find((x) => x.id === id)
    if (!q) return

    try {
      await fetch(`/api/questions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ likes: q.likes + 1 }),
      })
      setQuestions((prev) => prev.map((x) => x.id === id ? { ...x, likes: x.likes + 1 } : x))
    } catch { /* silently fail */ }
    finally {
      setLikingIds((prev) => { const next = new Set(prev); next.delete(id); return next })
    }
  }

  // Build sidebar tree
  const { sidebarItems, counts } = useMemo(() => {
    const c: Record<string, number> = { all: questions.length }
    const subMap: Record<string, Set<string>> = {}

    for (const q of questions) {
      const src = q.source || 'ai'
      c[`source::${src}`] = (c[`source::${src}`] || 0) + 1

      const cat = q.category || 'textbook'
      c[cat] = (c[cat] || 0) + 1
      if (q.subcategory) {
        const sk = `${cat}::${q.subcategory}`
        c[sk] = (c[sk] || 0) + 1
        if (!subMap[cat]) subMap[cat] = new Set()
        subMap[cat].add(q.subcategory)
      }
    }

    const items: SidebarItem[] = [
      { key: 'all', label: isZh ? '全部问题' : 'All Questions', count: c.all || 0, icon: <Layers className="h-4 w-4 shrink-0" /> },
      { key: 'source::ai', label: isZh ? 'AI 生成' : 'AI Generated', count: c['source::ai'] || 0, icon: <Sparkles className="h-4 w-4 shrink-0 text-purple-400" /> },
      { key: 'source::manual', label: isZh ? '用户提交' : 'User Submitted', count: c['source::manual'] || 0, icon: <User className="h-4 w-4 shrink-0 text-blue-400" /> },
    ]

    // Add category tree
    for (const [catKey, cfg] of Object.entries(CATEGORY_CONFIG)) {
      const count = c[catKey] || 0
      if (count === 0) continue
      const Icon = cfg.icon
      items.push({
        key: catKey,
        label: isZh ? cfg.labelZh : cfg.label,
        count,
        icon: <Icon className={cn('h-4 w-4 shrink-0', cfg.color)} />,
      })
      const subs = subMap[catKey]
      if (subs) {
        for (const sub of [...subs].sort()) {
          items.push({
            key: `${catKey}::${sub}`,
            label: sub,
            count: c[`${catKey}::${sub}`] || 0,
            indent: true,
          })
        }
      }
    }

    return { sidebarItems: items, counts: c }
  }, [questions, isZh])

  // Filter
  const displayQuestions = useMemo(() => {
    if (filter === 'all') return questions
    if (filter.startsWith('source::')) {
      const src = filter.split('::')[1]
      return questions.filter((q) => q.source === src)
    }
    if (filter.includes('::')) {
      const sub = filter.split('::')[1]
      return questions.filter((q) => q.subcategory === sub)
    }
    return questions.filter((q) => (q.category || 'textbook') === filter)
  }, [questions, filter])

  const formatDate = (d: string) => {
    if (!d) return ''
    return new Date(d).toLocaleDateString(isZh ? 'zh-CN' : 'en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  }

  return (
    <SidebarLayout
      title={isZh ? '问题库' : 'Questions'}
      icon={<MessageSquare className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={setFilter}
      showViewToggle
      viewMode={viewMode}
      onViewModeChange={setViewMode}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {isZh ? `共 ${questions.length} 个问题` : `${questions.length} questions`}
        </p>
      }
      loading={loading}
      loadingText={isZh ? '正在加载...' : 'Loading...'}
      error={error}
      onRetry={load}
      toolbar={
        <button
          onClick={load}
          className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          title={isZh ? '刷新' : 'Refresh'}
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      }
    >
      {/* Empty */}
      {!loading && displayQuestions.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
            <MessageSquare className="h-7 w-7 text-muted-foreground" />
          </div>
          <h3 className="text-sm font-semibold text-foreground mb-1">
            {isZh ? '暂无问题' : 'No questions yet'}
          </h3>
          <p className="text-xs text-muted-foreground text-center max-w-xs">
            {isZh ? '在 Chat 中生成学习问题后会自动保存到这里' : 'Questions generated in Chat will appear here'}
          </p>
        </div>
      )}

      {/* Card view */}
      {displayQuestions.length > 0 && viewMode === 'cards' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {displayQuestions.map((q) => (
            <div
              key={q.id}
              className="group rounded-xl border border-border bg-card p-4 shadow-sm hover:shadow-md hover:border-primary/20 transition-all"
            >
              {/* Header: topic + source */}
              <div className="flex items-center gap-2 mb-2">
                {q.topicHint && (
                  <span className="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-muted text-muted-foreground">
                    {q.topicHint}
                  </span>
                )}
                <span className={cn(
                  'text-[10px] font-semibold rounded-full px-2 py-0.5',
                  SOURCE_CONFIG[q.source]?.color || 'bg-muted text-muted-foreground'
                )}>
                  {SOURCE_CONFIG[q.source]?.label || q.source}
                </span>
              </div>

              {/* Question text */}
              <p className="text-sm text-foreground leading-relaxed mb-3 line-clamp-3">
                {q.question}
              </p>

              {/* Footer: book + like */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground truncate max-w-[60%]">
                  <BookOpen className="h-3 w-3 shrink-0" />
                  <span className="truncate">{q.bookTitle || q.bookId}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleLike(q.id)}
                  disabled={likingIds.has(q.id)}
                  className={cn(
                    'flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-all',
                    q.likes > 0
                      ? 'bg-primary/10 text-primary hover:bg-primary/20'
                      : 'bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary'
                  )}
                >
                  <ThumbsUp className={cn('h-3 w-3', likingIds.has(q.id) && 'animate-bounce')} />
                  {q.likes}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Table view */}
      {displayQuestions.length > 0 && viewMode === 'table' && (
        <div className="rounded-lg border border-border overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-4 px-4 py-2 bg-muted/50 text-[11px] font-medium text-muted-foreground uppercase tracking-wider border-b border-border select-none">
            <span className="flex-1">{isZh ? '问题' : 'Question'}</span>
            <span className="w-32 hidden sm:block text-right">{isZh ? '书籍' : 'Book'}</span>
            <span className="w-20 hidden md:block text-center">{isZh ? '来源' : 'Source'}</span>
            <span className="w-24 hidden lg:block text-right">{isZh ? '时间' : 'Date'}</span>
            <span className="w-16 text-center">👍</span>
          </div>

          {/* Rows */}
          {displayQuestions.map((q, idx) => (
            <div
              key={q.id}
              className={cn(
                'flex items-center gap-4 px-4 py-3 transition-colors hover:bg-secondary/50',
                idx > 0 && 'border-t border-border'
              )}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground truncate">{q.question}</p>
                {q.topicHint && (
                  <span className="text-[10px] text-muted-foreground">{q.topicHint}</span>
                )}
              </div>

              <span className="w-32 hidden sm:block text-xs text-muted-foreground truncate text-right">
                {q.bookTitle || q.bookId}
              </span>

              <div className="w-20 hidden md:flex justify-center">
                <span className={cn(
                  'text-[10px] font-semibold rounded-full px-2 py-0.5',
                  SOURCE_CONFIG[q.source]?.color
                )}>
                  {SOURCE_CONFIG[q.source]?.label}
                </span>
              </div>

              <span className="w-24 hidden lg:block text-[10px] text-muted-foreground text-right">
                {formatDate(q.createdAt)}
              </span>

              <div className="w-16 flex justify-center">
                <button
                  type="button"
                  onClick={() => handleLike(q.id)}
                  disabled={likingIds.has(q.id)}
                  className={cn(
                    'flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium transition-all',
                    q.likes > 0
                      ? 'bg-primary/10 text-primary hover:bg-primary/20'
                      : 'bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary'
                  )}
                >
                  <ThumbsUp className={cn('h-3 w-3', likingIds.has(q.id) && 'animate-bounce')} />
                  {q.likes}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </SidebarLayout>
  )
}
