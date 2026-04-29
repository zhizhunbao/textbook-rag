/**
 * PromptEditorPage — Prompt template editor with live preview.
 *
 * Route: /engine/response_synthesizers
 *
 * Two-panel layout:
 *   Left sidebar: Prompt mode list (SidebarLayout)
 *   Right main:   Edit tab (name/description/systemPrompt) + Preview tab (SSE query)
 *
 * Ref: Payload — Prompts Collection (type='mode')
 */

'use client'

import { useState, useEffect, useMemo, useCallback, useRef, Suspense } from 'react'
import {
  FileText, RefreshCw, Star, Save, Eye, Pencil,
  Loader2, CheckCircle2, AlertCircle, Play,
  Search, Zap, RotateCcw,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { SidebarLayout, type SidebarItem } from '@/features/shared/components/SidebarLayout'
import { useQueryState } from '@/features/shared/hooks/useQueryState'
import { fetchPromptModes, updatePromptMode } from '../api'
import type { PromptMode, PromptModeUpdatePayload } from '../types'

// ============================================================
// Constants
// ============================================================

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

function displayRoleName(name?: string): string {
  return (name ?? '').replace(/^[^\p{L}\p{N}]+/u, '').trim()
}

// ============================================================
// Component
// ============================================================

export default function PromptEditorPage() {
  return (
    <Suspense>
      <PromptEditorPageInner />
    </Suspense>
  )
}

function PromptEditorPageInner() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  // ==========================================================
  // Data state
  // ==========================================================
  const [modes, setModes] = useState<PromptMode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedStr, setSelectedStr] = useQueryState('selected', '')
  const selected = selectedStr ? Number(selectedStr) : null
  const setSelected = useCallback((id: number | null) => {
    setSelectedStr(id != null ? String(id) : '')
  }, [setSelectedStr])

  // ==========================================================
  // Edit state
  // ==========================================================
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit')
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editSystemPrompt, setEditSystemPrompt] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  // ==========================================================
  // Preview state
  // ==========================================================
  const [previewQuestion, setPreviewQuestion] = useState('')
  const [previewText, setPreviewText] = useState('')
  const [previewing, setPreviewing] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // ==========================================================
  // Fetch modes
  // ==========================================================
  const loadModes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const docs = await fetchPromptModes()
      setModes(docs)
      if (docs.length > 0 && selected === null) {
        setSelected(docs[0].id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [selected])

  useEffect(() => { loadModes() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ==========================================================
  // Sync edit fields when selection changes
  // ==========================================================
  const activeMode = useMemo(
    () => modes.find((m) => m.id === selected) ?? null,
    [modes, selected],
  )

  useEffect(() => {
    if (activeMode) {
      setEditName(activeMode.name)
      setEditDescription(activeMode.description)
      setEditSystemPrompt(activeMode.systemPrompt ?? '')
      setDirty(false)
      setSaveSuccess(false)
      setSaveError(null)
      setActiveTab('edit')
      setPreviewText('')
      setPreviewError(null)
    }
  }, [activeMode?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // ==========================================================
  // Track dirty state
  // ==========================================================
  useEffect(() => {
    if (!activeMode) return
    const changed =
      editName !== activeMode.name ||
      editDescription !== activeMode.description ||
      editSystemPrompt !== (activeMode.systemPrompt ?? '')
    setDirty(changed)
    if (changed) setSaveSuccess(false)
  }, [editName, editDescription, editSystemPrompt, activeMode])

  // ==========================================================
  // Save handler
  // ==========================================================
  const handleSave = async () => {
    if (!activeMode || !dirty) return
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)
    try {
      const payload: PromptModeUpdatePayload = {}
      if (editName !== activeMode.name) payload.name = editName
      if (editDescription !== activeMode.description) payload.description = editDescription
      if (editSystemPrompt !== (activeMode.systemPrompt ?? '')) payload.systemPrompt = editSystemPrompt

      const updated = await updatePromptMode(activeMode.id, payload)
      setModes((prev) => prev.map((m) => (m.id === updated.id ? updated : m)))
      setDirty(false)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  // ==========================================================
  // Preview handler — SSE stream with edited systemPrompt
  // ==========================================================
  const handlePreview = async () => {
    if (!previewQuestion.trim()) return
    abortRef.current?.abort()

    const controller = new AbortController()
    abortRef.current = controller

    setPreviewing(true)
    setPreviewText('')
    setPreviewError(null)

    try {
      const res = await fetch(`${ENGINE}/engine/query/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: previewQuestion.trim(),
          top_k: 3,
          custom_system_prompt: editSystemPrompt,
        }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const body = await res.text()
        throw new Error(`${res.status}: ${body}`)
      }

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (currentEvent === 'token') {
                setPreviewText((prev) => prev + (data.t ?? ''))
              } else if (currentEvent === 'done') {
                setPreviewText(data.answer ?? '')
              }
            } catch {
              // Skip malformed JSON
            }
            currentEvent = ''
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setPreviewError(err instanceof Error ? err.message : String(err))
    } finally {
      setPreviewing(false)
      abortRef.current = null
    }
  }

  const handleAbortPreview = () => {
    abortRef.current?.abort()
    setPreviewing(false)
  }

  // ==========================================================
  // Sidebar items
  // ==========================================================
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    return modes.map((mode) => {
      return {
        key: String(mode.id),
        label: displayRoleName(mode.name),
        icon: false,
        highlight: mode.isDefault,
      }
    })
  }, [modes])

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <SidebarLayout
      title={isFr ? 'Role Manager' : 'Role Manager'}
      icon={false}
      sidebarItems={sidebarItems}
      activeFilter={selected != null ? String(selected) : ''}
      onFilterChange={(key) => setSelected(Number(key))}
      sidebarWidthPx={200}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {isFr ? `${modes.length} roles` : `${modes.length} roles`}
        </p>
      }
      loading={loading}
      loadingText={isFr ? 'Loading roles...' : 'Loading roles...'}
      error={error}
      onRetry={loadModes}
      toolbar={
        <div className="flex items-center gap-2">
          {dirty && (
            <span className="text-[10px] text-amber-400 font-medium">
              {isFr ? '● 未保存' : '● Unsaved'}
            </span>
          )}
          {saveSuccess && (
            <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
              <CheckCircle2 className="h-3 w-3" />
              {isFr ? '已保存' : 'Saved'}
            </span>
          )}
          <button
            onClick={loadModes}
            className="p-2 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            title={isFr ? '刷新' : 'Refresh'}
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      }
    >
      {activeMode ? (
        <div className="flex flex-col h-full">
          {/* ── Header ─────────────────────────────────────── */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold text-foreground">{displayRoleName(activeMode.name)}</h1>
                  {activeMode.isDefault && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-0.5">
                      <Star className="h-2.5 w-2.5" />{isFr ? '默认' : 'Default'}
                    </span>
                  )}
                </div>
                <code className="text-xs text-muted-foreground font-mono bg-secondary px-1.5 py-0.5 rounded">
                  {activeMode.slug}
                </code>
              </div>
            </div>

            {/* Tab switcher + Save */}
            <div className="flex items-center gap-2">
              <div className="flex items-center rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => setActiveTab('edit')}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors',
                    activeTab === 'edit'
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary',
                  )}
                >
                  <Pencil className="h-3 w-3" />
                  {isFr ? '编辑' : 'Edit'}
                </button>
                <button
                  onClick={() => setActiveTab('preview')}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors',
                    activeTab === 'preview'
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary',
                  )}
                >
                  <Eye className="h-3 w-3" />
                  {isFr ? '预览' : 'Preview'}
                </button>
              </div>

              <button
                onClick={handleSave}
                disabled={!dirty || saving}
                className={cn(
                  'flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  dirty
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'bg-muted text-muted-foreground cursor-not-allowed',
                )}
              >
                {saving ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                {isFr ? '保存' : 'Save'}
              </button>
            </div>
          </div>

          {/* ── Save error ─────────────────────────────────── */}
          {saveError && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2.5 mb-4 flex items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5 text-destructive shrink-0" />
              <p className="text-xs text-destructive">{saveError}</p>
            </div>
          )}

          {/* ── Edit tab ───────────────────────────────────── */}
          {activeTab === 'edit' && (
            <div className="flex-1 space-y-5 overflow-y-auto">
              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                  {isFr ? '名称' : 'Name'}
                </label>
                <input
                  type="text"
                  value={displayRoleName(editName)}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none transition-colors"
                />
              </div>

              <div className="hidden" aria-hidden="true">
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                  {isFr ? '图标 (Lucide 名称)' : 'Icon (Lucide name)'}
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value=""
                    onChange={() => {}}
                    placeholder="lightbulb, book, chart, minimize"
                    className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                  {isFr ? '描述' : 'Description'}
                </label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none resize-none transition-colors"
                />
              </div>

              {/* System Prompt */}
              <div className="flex-1">
                <label className="flex items-center justify-between text-xs font-medium text-muted-foreground mb-1.5">
                  <span>System Prompt</span>
                  <span className="text-[10px] font-mono text-muted-foreground/60">
                    {editSystemPrompt.length} chars
                  </span>
                </label>
                <textarea
                  value={editSystemPrompt}
                  onChange={(e) => setEditSystemPrompt(e.target.value)}
                  rows={16}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground font-mono leading-relaxed focus:border-primary focus:outline-none resize-y transition-colors"
                  placeholder={isFr ? '输入系统提示词…' : 'Enter system prompt…'}
                />
              </div>
            </div>
          )}

          {/* ── Preview tab ────────────────────────────────── */}
          {activeTab === 'preview' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Preview input bar */}
              <div className="flex items-center gap-2 mb-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
                  <input
                    type="text"
                    value={previewQuestion}
                    onChange={(e) => setPreviewQuestion(e.target.value)}
                    placeholder={isFr ? '输入测试问题…' : 'Enter a test question…'}
                    className="w-full rounded-lg border border-border bg-card pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none transition-colors"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handlePreview()
                      }
                    }}
                  />
                </div>
                {previewing ? (
                  <button
                    onClick={handleAbortPreview}
                    className="flex items-center gap-1.5 rounded-lg bg-destructive/10 text-destructive px-3 py-2 text-xs font-medium hover:bg-destructive/20 transition-colors"
                  >
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    {isFr ? '中断' : 'Stop'}
                  </button>
                ) : (
                  <button
                    onClick={handlePreview}
                    disabled={!previewQuestion.trim()}
                    className="flex items-center gap-1.5 rounded-lg bg-primary text-primary-foreground px-3 py-2 text-xs font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Play className="h-3.5 w-3.5" />
                    {isFr ? '测试' : 'Test'}
                  </button>
                )}
                {previewText && !previewing && (
                  <button
                    onClick={() => { setPreviewText(''); setPreviewError(null) }}
                    className="p-2 rounded-lg border border-border text-muted-foreground hover:bg-secondary transition-colors"
                    title={isFr ? '清除' : 'Clear'}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Active system prompt indicator */}
              <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 mb-4">
                <div className="flex items-center gap-1.5 mb-1">
                  <Zap className="h-3 w-3 text-amber-400" />
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    {isFr ? '使用的 System Prompt' : 'Active System Prompt'}
                  </span>
                  {dirty && (
                    <span className="text-[10px] text-amber-400 font-medium ml-auto">
                      {isFr ? '(已编辑, 未保存)' : '(edited, unsaved)'}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-foreground/60 font-mono line-clamp-2">
                  {editSystemPrompt.slice(0, 200)}{editSystemPrompt.length > 200 ? '…' : ''}
                </p>
              </div>

              {/* Preview output */}
              <div className="flex-1 overflow-y-auto rounded-lg border border-border bg-card p-4">
                {!previewText && !previewing && !previewError && (
                  <div className="flex flex-col items-center justify-center h-full text-center py-12">
                    <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-3">
                      <Eye className="h-7 w-7 text-muted-foreground/30" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground mb-1">
                      {isFr ? '实时预览' : 'Live Preview'}
                    </h3>
                    <p className="text-xs text-muted-foreground max-w-xs">
                      {isFr
                        ? '输入测试问题，使用当前编辑的 System Prompt 查看 AI 回答效果'
                        : 'Enter a test question to see how the AI responds with your edited system prompt'}
                    </p>
                  </div>
                )}

                {previewError && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-destructive">
                          {isFr ? '预览失败' : 'Preview failed'}
                        </p>
                        <p className="text-xs text-destructive/70 mt-1">{previewError}</p>
                      </div>
                    </div>
                  </div>
                )}

                {previewText && (
                  <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                    {previewText}
                    {previewing && (
                      <span className="inline-block w-1.5 h-4 bg-primary/60 animate-pulse ml-0.5 align-text-bottom rounded-sm" />
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-full py-20">
          <FileText className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">
            {isFr ? '选择左侧的 Prompt 模式查看详情' : 'Select a prompt mode from the sidebar'}
          </p>
        </div>
      )}
    </SidebarLayout>
  )
}
