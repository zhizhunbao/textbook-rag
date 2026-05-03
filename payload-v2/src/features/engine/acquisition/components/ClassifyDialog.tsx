/**
 * ClassifyDialog — Pre-upload confirmation with LLM auto-classification.
 *
 * Shown after file selection / URL paste, before the actual upload begins.
 * The LLM suggests a category + subcategory; user can accept or override.
 *
 * Usage: <ClassifyDialog file={file} onConfirm={...} onCancel={...} />
 *
 * Ref: AQ-05 — LLM auto-classification for uploaded PDFs
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Sparkles, Loader2, ChevronDown, Check, X, AlertTriangle,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import { classifyBook } from '../api'
import type { ClassifyResult, BookCategory } from '../types'

// ============================================================
// Types
// ============================================================
export interface ClassifyDialogProps {
  /** Derived title from file/URL (editable). */
  initialTitle: string
  /** Original filename (sent to LLM for context). */
  filename?: string
  /** Called when user confirms — includes final title, category, subcategory. */
  onConfirm: (data: { title: string; category: string; subcategory: string }) => void
  /** Called when user cancels. */
  onCancel: () => void
}

// ============================================================
// Well-known categories (shown as quick-pick options)
// ============================================================
const COMMON_CATEGORIES = [
  { value: 'textbooks', label: 'textbooks', emoji: '📚' },
  { value: 'ecdev', label: 'EC Dev', emoji: '📊' },
  { value: 'real_estate', label: 'Real Estate', emoji: '🏠' },
  { value: 'research_paper', label: 'Research', emoji: '🔬' },
  { value: 'policy', label: 'Policy', emoji: '📋' },
  { value: 'finance', label: 'Finance', emoji: '💰' },
]

// ============================================================
// Component
// ============================================================
export default function ClassifyDialog({
  initialTitle,
  filename,
  onConfirm,
  onCancel,
}: ClassifyDialogProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // ==========================================================
  // State
  // ==========================================================
  const [title, setTitle] = useState(initialTitle)
  const [category, setCategory] = useState('')
  const [subcategory, setSubcategory] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [classifying, setClassifying] = useState(true)
  const [classifyError, setClassifyError] = useState<string | null>(null)
  const [showCategoryPicker, setShowCategoryPicker] = useState(false)
  const [customCategory, setCustomCategory] = useState('')

  const pickerRef = useRef<HTMLDivElement>(null)

  // ==========================================================
  // Auto-classify on mount
  // ==========================================================
  useEffect(() => {
    let cancelled = false

    async function classify() {
      try {
        setClassifying(true)
        setClassifyError(null)
        const result: ClassifyResult = await classifyBook(initialTitle, filename)
        if (cancelled) return

        setCategory(result.category)
        setSubcategory(result.subcategory)
        setConfidence(result.confidence)
      } catch (err) {
        if (cancelled) return
        setClassifyError(
          err instanceof Error ? err.message : 'Classification failed',
        )
        // Default to textbook on error
        setCategory('textbooks')
      } finally {
        if (!cancelled) setClassifying(false)
      }
    }

    classify()
    return () => { cancelled = true }
  }, [initialTitle, filename])

  // ==========================================================
  // Close picker on outside click
  // ==========================================================
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowCategoryPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // ==========================================================
  // Handlers
  // ==========================================================
  const handleConfirm = useCallback(() => {
    onConfirm({
      title: title.trim() || initialTitle,
      category: category || 'textbooks',
      subcategory: subcategory.trim(),
    })
  }, [title, category, subcategory, initialTitle, onConfirm])

  const handleSelectCategory = useCallback((value: string) => {
    setCategory(value)
    setShowCategoryPicker(false)
    setCustomCategory('')
  }, [])

  const handleCustomCategorySubmit = useCallback(() => {
    if (customCategory.trim()) {
      const sanitized = customCategory.trim().toLowerCase().replace(/\s+/g, '_')
      setCategory(sanitized)
      setShowCategoryPicker(false)
      setCustomCategory('')
    }
  }, [customCategory])

  // ==========================================================
  // Confidence badge color
  // ==========================================================
  const confidenceColor = confidence >= 0.7
    ? 'text-emerald-500'
    : confidence >= 0.4
      ? 'text-amber-500'
      : 'text-red-400'

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className={cn(
        'w-full max-w-lg mx-4 rounded-2xl border border-border bg-card shadow-2xl',
        'animate-in fade-in-0 zoom-in-95 duration-200',
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                {isZh ? '智能分类' : 'Smart Classification'}
              </h2>
              <p className="text-[11px] text-muted-foreground">
                {isZh ? 'LLM 自动分析，可手动调整' : 'LLM auto-detected, editable'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 pb-5 space-y-4">
          {/* Title field */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {isZh ? '标题' : 'Title'}
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className={cn(
                'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm',
                'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary',
                'placeholder:text-muted-foreground/50',
              )}
              placeholder={initialTitle}
            />
          </div>

          {/* Category + Subcategory row */}
          <div className="grid grid-cols-2 gap-3">
            {/* Category */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {isZh ? '分类' : 'Category'}
                </label>
                {classifying && (
                  <Loader2 className="h-3 w-3 text-primary animate-spin" />
                )}
                {!classifying && !classifyError && confidence > 0 && (
                  <span className={cn('text-[10px] font-mono', confidenceColor)}>
                    {Math.round(confidence * 100)}%
                  </span>
                )}
              </div>

              {/* Category combobox */}
              <div className="relative" ref={pickerRef}>
                <button
                  type="button"
                  onClick={() => setShowCategoryPicker(!showCategoryPicker)}
                  disabled={classifying}
                  className={cn(
                    'w-full flex items-center justify-between rounded-lg border border-border',
                    'bg-background px-3 py-2 text-sm text-left',
                    'hover:border-primary/30 transition-colors',
                    'disabled:opacity-50 disabled:cursor-wait',
                    classifying && 'animate-pulse',
                  )}
                >
                  <span className={cn(
                    'truncate',
                    category ? 'text-foreground' : 'text-muted-foreground',
                  )}>
                    {classifying
                      ? (isZh ? '分析中...' : 'Analyzing...')
                      : category || (isZh ? '选择分类' : 'Select category')}
                  </span>
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                </button>

                {/* Dropdown */}
                {showCategoryPicker && (
                  <div className={cn(
                    'absolute top-full left-0 right-0 mt-1 z-10',
                    'rounded-lg border border-border bg-card shadow-lg',
                    'animate-in fade-in-0 slide-in-from-top-2 duration-150',
                    'max-h-60 overflow-y-auto',
                  )}>
                    {/* Common categories */}
                    {COMMON_CATEGORIES.map((cat) => (
                      <button
                        key={cat.value}
                        type="button"
                        onClick={() => handleSelectCategory(cat.value)}
                        className={cn(
                          'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                          'hover:bg-secondary/50 transition-colors',
                          category === cat.value && 'bg-primary/5 text-primary',
                        )}
                      >
                        <span className="text-base">{cat.emoji}</span>
                        <span className="flex-1">{cat.label}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {cat.value}
                        </span>
                        {category === cat.value && (
                          <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                        )}
                      </button>
                    ))}

                    {/* LLM suggestion (if not in common list) */}
                    {category && !COMMON_CATEGORIES.some((c) => c.value === category) && (
                      <>
                        <div className="border-t border-border my-1" />
                        <button
                          type="button"
                          onClick={() => handleSelectCategory(category)}
                          className={cn(
                            'w-full flex items-center gap-2 px-3 py-2 text-sm text-left',
                            'bg-primary/5 text-primary',
                          )}
                        >
                          <Sparkles className="h-3.5 w-3.5" />
                          <span className="flex-1">
                            {isZh ? 'LLM 建议' : 'LLM suggestion'}: {category}
                          </span>
                          <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                        </button>
                      </>
                    )}

                    {/* Custom input */}
                    <div className="border-t border-border mt-1 p-2">
                      <div className="flex gap-1.5">
                        <input
                          type="text"
                          value={customCategory}
                          onChange={(e) => setCustomCategory(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleCustomCategorySubmit()}
                          placeholder={isZh ? '自定义分类...' : 'Custom...'}
                          className={cn(
                            'flex-1 rounded border border-border bg-background px-2 py-1 text-xs',
                            'focus:outline-none focus:ring-1 focus:ring-primary/30',
                            'placeholder:text-muted-foreground/50',
                          )}
                        />
                        <button
                          type="button"
                          onClick={handleCustomCategorySubmit}
                          disabled={!customCategory.trim()}
                          className={cn(
                            'rounded px-2 py-1 text-xs font-medium',
                            'bg-primary text-primary-foreground',
                            'disabled:opacity-50 disabled:cursor-not-allowed',
                          )}
                        >
                          OK
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Subcategory */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {isZh ? '子分类' : 'Subcategory'}
              </label>
              <input
                type="text"
                value={subcategory}
                onChange={(e) => setSubcategory(e.target.value)}
                disabled={classifying}
                className={cn(
                  'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm',
                  'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary',
                  'placeholder:text-muted-foreground/50',
                  'disabled:opacity-50 disabled:cursor-wait',
                  classifying && 'animate-pulse',
                )}
                placeholder={isZh ? 'e.g. Python, Q4 报告' : 'e.g. Python, Q4 Report'}
              />
            </div>
          </div>

          {/* Classification error warning */}
          {classifyError && (
            <div className="flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>
                {isZh
                  ? `自动分类失败，已默认为 textbook: ${classifyError}`
                  : `Auto-classify failed, defaulted to textbook: ${classifyError}`}
              </span>
            </div>
          )}

          {/* Filename hint */}
          {filename && (
            <p className="text-[11px] text-muted-foreground truncate">
              📄 {filename}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-3">
          <button
            type="button"
            onClick={onCancel}
            className={cn(
              'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
              'text-muted-foreground hover:text-foreground hover:bg-secondary',
            )}
          >
            {isZh ? '取消' : 'Cancel'}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={classifying || !title.trim()}
            className={cn(
              'rounded-lg px-5 py-2 text-sm font-medium transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            {isZh ? '确认上传' : 'Confirm & Upload'}
          </button>
        </div>
      </div>
    </div>
  )
}
