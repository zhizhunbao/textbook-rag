'use client'

import { useState, useEffect, useCallback, useMemo, Suspense } from 'react'
import {
  HelpCircle, Plus, Save, Trash2, Loader2, Check,
  Shuffle, Focus, LayoutList, MessageCircleQuestion,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type SidebarItem } from '@/features/shared/components/SidebarLayout'
import { useQueryState } from '@/features/shared/hooks/useQueryState'

interface QueryTemplate {
  id: number
  name: string
  category: string
  triggerPatterns: string[]
  clarifyPrompt: string
  clarifyPromptZh: string
  suggestedQuestions: string[]
  suggestedQuestionsZh: string[]
  answerFormat: string
  answerFormatZh: string
  isEnabled: boolean
  sortOrder: number
}

const CATEGORY_CONFIG: Record<string, { icon: typeof Shuffle; label: string; labelZh: string; color: string }> = {
  disambiguation: { icon: Shuffle, label: 'Disambiguation', labelZh: '消歧义', color: 'text-violet-400 bg-violet-500/10' },
  scope: { icon: Focus, label: 'Scope Narrowing', labelZh: '范围缩小', color: 'text-blue-400 bg-blue-500/10' },
  format: { icon: LayoutList, label: 'Format Guidance', labelZh: '格式引导', color: 'text-emerald-400 bg-emerald-500/10' },
  followup: { icon: MessageCircleQuestion, label: 'Follow-up', labelZh: '追问', color: 'text-amber-400 bg-amber-500/10' },
}

function CategoryBadge({ category, isZh }: { category: string; isZh: boolean }) {
  const cfg = CATEGORY_CONFIG[category] ?? CATEGORY_CONFIG.disambiguation
  const Icon = cfg.icon
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium', cfg.color)}>
      <Icon className="h-2.5 w-2.5" />
      {isZh ? cfg.labelZh : cfg.label}
    </span>
  )
}

export default function Page() {
  return (
    <Suspense>
      <RetrieversPageInner />
    </Suspense>
  )
}

function RetrieversPageInner() {
  const { t, locale } = useI18n()
  const isZh = locale === 'zh'

  const [templates, setTemplates] = useState<QueryTemplate[]>([])
  const [selected, setSelected] = useState<QueryTemplate | null>(null)
  const [draft, setDraft] = useState<Partial<QueryTemplate>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [isNew, setIsNew] = useState(false)
  const [filter, setFilter] = useQueryState('filter', 'all')

  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/prompts?limit=50&sort=sortOrder')
      const data = await res.json()
      const items: QueryTemplate[] = (data.docs ?? []).map((m: any) => ({
        id: m.id,
        name: m.name ?? '',
        category: m.category ?? 'disambiguation',
        triggerPatterns: Array.isArray(m.triggerPatterns) ? m.triggerPatterns : [],
        clarifyPrompt: m.clarifyPrompt ?? '',
        clarifyPromptZh: m.clarifyPromptZh ?? '',
        suggestedQuestions: Array.isArray(m.suggestedQuestions) ? m.suggestedQuestions : [],
        suggestedQuestionsZh: Array.isArray(m.suggestedQuestionsZh) ? m.suggestedQuestionsZh : [],
        answerFormat: m.answerFormat ?? '',
        answerFormatZh: m.answerFormatZh ?? '',
        isEnabled: m.isEnabled ?? true,
        sortOrder: m.sortOrder ?? 0,
      }))
      setTemplates(items)
      if (!selected && items.length > 0) {
        setSelected(items[0])
        setDraft(items[0])
      }
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchTemplates() }, [fetchTemplates])

  const selectTpl = (tpl: QueryTemplate) => {
    setSelected(tpl)
    setDraft(tpl)
    setIsNew(false)
    setSaved(false)
  }

  const startNew = () => {
    setSelected(null)
    setDraft({
      name: '', category: 'disambiguation', triggerPatterns: [],
      clarifyPrompt: '', clarifyPromptZh: '',
      suggestedQuestions: [], suggestedQuestionsZh: [],
      answerFormat: '', answerFormatZh: '',
      isEnabled: true, sortOrder: 0,
    })
    setIsNew(true)
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const url = isNew ? '/api/prompts' : `/api/prompts/${selected!.id}`
      const method = isNew ? 'POST' : 'PATCH'
      const res = await fetch(url, {
        method, headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify(draft),
      })
      if (res.ok) {
        setIsNew(false)
        await fetchTemplates()
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      }
    } catch {}
    setSaving(false)
  }

  const handleDelete = async () => {
    if (!selected || !confirm(isZh ? '确定删除该模板？' : 'Delete this template?')) return
    await fetch(`/api/prompts/${selected.id}`, { method: 'DELETE', credentials: 'include' })
    setSelected(null)
    setDraft({})
    await fetchTemplates()
  }

  // ── Category counts ────────────────────────────────────────────────────────
  const categoryCounts = useMemo(() => {
    const c: Record<string, number> = { all: templates.length }
    for (const tpl of templates) {
      c[tpl.category] = (c[tpl.category] || 0) + 1
    }
    return c
  }, [templates])

  // ── Filtered templates ─────────────────────────────────────────────────────
  const displayTemplates = useMemo(() => {
    if (filter === 'all') return templates
    return templates.filter((t) => t.category === filter)
  }, [templates, filter])

  // ── Sidebar items ──────────────────────────────────────────────────────────
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    const items: SidebarItem[] = [
      { key: 'all', label: isZh ? '全部模板' : 'All Templates', count: categoryCounts.all || 0 },
    ]
    for (const [key, cfg] of Object.entries(CATEGORY_CONFIG)) {
      if ((categoryCounts[key] || 0) > 0) {
        items.push({
          key,
          label: isZh ? cfg.labelZh : cfg.label,
          count: categoryCounts[key] || 0,
          indent: true,
        })
      }
    }
    return items
  }, [categoryCounts, isZh])

  return (
    <SidebarLayout
      title={isZh ? '问题引导模板' : 'Query Templates'}
      icon={<HelpCircle className="h-4 w-4 text-cyan-400" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={setFilter}
      sidebarWidth="w-48"
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">{templates.length} templates</p>
      }
      subtitle={`${displayTemplates.length} ${isZh ? '个模板' : 'templates'}`}
      loading={loading}
      loadingText={isZh ? '加载模板...' : 'Loading templates...'}
      toolbar={
        <button
          onClick={startNew}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-primary/30 text-primary hover:bg-primary/10 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          {isZh ? '新建' : 'New'}
        </button>
      }
    >
      {/* Template list + edit panel in a split layout */}
      <div className="flex h-[calc(100vh-11rem)] -m-6 mt-0">
        {/* Inner list panel */}
        <div className="w-64 shrink-0 border-r border-border bg-card/30 flex flex-col">
          <nav className="flex-1 overflow-y-auto py-2 px-2">
            {displayTemplates.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                onClick={() => selectTpl(tpl)}
                className={cn(
                  'flex flex-col gap-1 w-full rounded-lg px-3 py-2.5 text-left transition-colors mb-1',
                  selected?.id === tpl.id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground',
                  !tpl.isEnabled && 'opacity-50'
                )}
              >
                <span className="text-xs font-medium truncate">{tpl.name}</span>
                <CategoryBadge category={tpl.category} isZh={isZh} />
              </button>
            ))}
          </nav>
        </div>

        {/* Edit panel */}
        <div className="flex-1 min-w-0 flex flex-col">
          {draft.name !== undefined ? (
            <>
              <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/30">
                <h2 className="text-sm font-semibold text-foreground">
                  {isNew ? (isZh ? '新建模板' : 'New Template') : draft.name}
                </h2>
                <div className="flex items-center gap-2">
                  {selected && !isNew && (
                    <button onClick={handleDelete} className="p-2 rounded-md text-destructive/70 hover:bg-destructive/10 hover:text-destructive transition-colors">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={saving || !draft.name}
                    className={cn(
                      'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-colors',
                      saved ? 'bg-emerald-500/20 text-emerald-400' : 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50'
                    )}
                  >
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : saved ? <Check className="h-3.5 w-3.5" /> : <Save className="h-3.5 w-3.5" />}
                    {saving ? '...' : saved ? '✓' : (isZh ? '保存' : 'Save')}
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                {/* Row 1: Name + Category + Enabled */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '模板名称' : 'Name'}
                    </label>
                    <input
                      type="text" value={draft.name ?? ''}
                      onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                      className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring/30"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '类别' : 'Category'}
                    </label>
                    <select
                      value={draft.category ?? 'disambiguation'}
                      onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                      className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring/30"
                    >
                      {Object.entries(CATEGORY_CONFIG).map(([k, v]) => (
                        <option key={k} value={k}>{isZh ? v.labelZh : v.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-end pb-1">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={draft.isEnabled ?? true} onChange={(e) => setDraft({ ...draft, isEnabled: e.target.checked })} className="h-4 w-4 rounded accent-primary" />
                      <span className="text-xs text-muted-foreground">{isZh ? '启用' : 'Enabled'}</span>
                    </label>
                  </div>
                </div>

                {/* Row 2: Trigger Patterns */}
                <div>
                  <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                    {isZh ? '触发关键词' : 'Trigger Patterns'}
                  </label>
                  <input
                    type="text"
                    value={Array.isArray(draft.triggerPatterns) ? draft.triggerPatterns.join(', ') : ''}
                    onChange={(e) => setDraft({ ...draft, triggerPatterns: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                    placeholder="what is, explain, 什么是"
                    className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/30"
                  />
                  <p className="mt-1 text-[10px] text-muted-foreground">{isZh ? '逗号分隔' : 'Comma-separated keywords'}</p>
                </div>

                {/* Row 3: Clarification Prompts (EN + ZH) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '澄清提示 (EN)' : 'Clarify Prompt (EN)'}
                    </label>
                    <textarea
                      value={draft.clarifyPrompt ?? ''}
                      onChange={(e) => setDraft({ ...draft, clarifyPrompt: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm text-foreground leading-relaxed focus:outline-none focus:ring-1 focus:ring-ring/30 resize-y"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '澄清提示 (ZH)' : 'Clarify Prompt (ZH)'}
                    </label>
                    <textarea
                      value={draft.clarifyPromptZh ?? ''}
                      onChange={(e) => setDraft({ ...draft, clarifyPromptZh: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm text-foreground leading-relaxed focus:outline-none focus:ring-1 focus:ring-ring/30 resize-y"
                    />
                  </div>
                </div>

                {/* Row 4: Suggested Questions (EN + ZH) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '建议问题 (EN)' : 'Suggested Questions (EN)'}
                    </label>
                    <textarea
                      value={Array.isArray(draft.suggestedQuestions) ? draft.suggestedQuestions.join('\n') : ''}
                      onChange={(e) => setDraft({ ...draft, suggestedQuestions: e.target.value.split('\n').filter(Boolean) })}
                      rows={4}
                      placeholder="One question per line"
                      className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm text-foreground font-mono leading-relaxed placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/30 resize-y"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '建议问题 (ZH)' : 'Suggested Questions (ZH)'}
                    </label>
                    <textarea
                      value={Array.isArray(draft.suggestedQuestionsZh) ? draft.suggestedQuestionsZh.join('\n') : ''}
                      onChange={(e) => setDraft({ ...draft, suggestedQuestionsZh: e.target.value.split('\n').filter(Boolean) })}
                      rows={4}
                      placeholder="每行一个问题"
                      className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm text-foreground font-mono leading-relaxed placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/30 resize-y"
                    />
                  </div>
                </div>

                {/* Row 5: Answer Format (EN + ZH) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '回答格式 (EN)' : 'Answer Format (EN)'}
                    </label>
                    <textarea
                      value={draft.answerFormat ?? ''}
                      onChange={(e) => setDraft({ ...draft, answerFormat: e.target.value })}
                      rows={2}
                      className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm text-foreground leading-relaxed focus:outline-none focus:ring-1 focus:ring-ring/30 resize-y"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                      {isZh ? '回答格式 (ZH)' : 'Answer Format (ZH)'}
                    </label>
                    <textarea
                      value={draft.answerFormatZh ?? ''}
                      onChange={(e) => setDraft({ ...draft, answerFormatZh: e.target.value })}
                      rows={2}
                      className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm text-foreground leading-relaxed focus:outline-none focus:ring-1 focus:ring-ring/30 resize-y"
                    />
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-muted-foreground">
                {isZh ? '选择一个模板查看详情' : 'Select a template to view details'}
              </p>
            </div>
          )}
        </div>
      </div>
    </SidebarLayout>
  )
}
