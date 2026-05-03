/**
 * GenerationPanel — question generation panel driven by sidebar selection.
 *
 * Usage: <GenerationPanel filter={sidebarFilter} books={books} onGenerated={load} />
 *
 * Reads the current sidebar filter to determine generation scope.
 * When a single book is selected, shows a chapter mini-sidebar (from TOC API)
 * for fine-grained chapter-level generation.
 */

'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  Sparkles, Loader2, AlertCircle, SlidersHorizontal, Check,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import type { BookBase } from '@/features/shared/books'
import { generateQuestions, generateDataset } from '../api'
import GenerationProgress from './GenerationProgress'

// ============================================================
// Types
// ============================================================

interface TocEntry {
  id: string
  title: string
  level: number
  number?: string
  pdf_page?: number
}

interface GenerationPanelProps {
  /** Current sidebar filter value (e.g. 'all', 'textbooks', 'book::abc') */
  filter: string
  /** All indexed books (from useBooks) */
  books: BookBase[]
  /** Called when generation completes — parent should refresh its list */
  onGenerated?: () => void
}

// ============================================================
// Constants
// ============================================================

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Component
// ============================================================

export default function GenerationPanel({
  filter,
  books,
  onGenerated,
}: GenerationPanelProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // ==========================================================
  // Derived: target books from sidebar filter
  // ==========================================================
  const targetBooks = useMemo(() => {
    if (filter === 'all') return books
    if (filter.startsWith('book::')) {
      const bookId = filter.slice(6)
      return books.filter((b) => b.book_id === bookId)
    }
    if (filter.includes('::')) {
      const [cat, sub] = filter.split('::')
      return books.filter((b) => (b.category || 'textbooks') === cat && b.subcategory === sub)
    }
    return books.filter((b) => (b.category || 'textbooks') === filter)
  }, [filter, books])

  const targetBookIds = useMemo(() => targetBooks.map((b) => b.book_id), [targetBooks])
  const isSingleBook = targetBooks.length === 1

  // ==========================================================
  // State
  // ==========================================================
  const [selectedChapterKeys, setSelectedChapterKeys] = useState<Set<string>>(new Set())
  const [chapters, setChapters] = useState<TocEntry[]>([])
  const [chaptersLoading, setChaptersLoading] = useState(false)
  const [count, setCount] = useState(5)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resultCount, setResultCount] = useState<number | null>(null)

  // ── QD-06: Dataset generation state ──
  const [showDatasetModal, setShowDatasetModal] = useState(false)
  const [datasetName, setDatasetName] = useState('')
  const [datasetStrategy, setDatasetStrategy] = useState('stratified')
  const [datasetKPerBook, setDatasetKPerBook] = useState(10)
  const [datasetGenerating, setDatasetGenerating] = useState(false)
  const [datasetResult, setDatasetResult] = useState<string | null>(null)

  // ==========================================================
  // Effects
  // ==========================================================

  // Fetch TOC chapters when a single book is selected
  useEffect(() => {
    setSelectedChapterKeys(new Set())
    setChapters([])

    if (!isSingleBook) return

    const bookId = targetBookIds[0]
    setChaptersLoading(true)

    fetch(`${ENGINE}/engine/books/${bookId}/toc`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data: TocEntry[]) => setChapters(data))
      .catch(() => setChapters([]))
      .finally(() => setChaptersLoading(false))
  }, [isSingleBook, targetBookIds])

  // Clear feedback on filter change
  useEffect(() => {
    setResultCount(null)
    setError(null)
  }, [filter])

  // ==========================================================
  // Handlers
  // ==========================================================

  const toggleChapter = useCallback((key: string) => {
    setSelectedChapterKeys((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const handleGenerate = useCallback(async () => {
    if (targetBookIds.length === 0) return

    setGenerating(true)
    setError(null)
    setResultCount(null)

    try {
      const chapterKeys = Array.from(selectedChapterKeys)
      const category = !filter.startsWith('book::') && filter !== 'all' && !filter.includes('::')
        ? filter
        : undefined

      const questions = await generateQuestions(targetBookIds, count, {
        category,
        chapterKey: chapterKeys.length === 1 ? chapterKeys[0] : undefined,
      })

      setResultCount(questions.length)
      if (questions.length === 0) {
        setError(isZh ? '未生成任何问题，请检查书籍是否已索引' : 'No questions generated. Check if books are indexed.')
      }
      onGenerated?.()
    } catch {
      setError(isZh ? '生成失败，请稍后重试' : 'Generation failed. Please retry.')
    } finally {
      setGenerating(false)
    }
  }, [targetBookIds, selectedChapterKeys, filter, count, isZh, onGenerated])

  // ── QD-06: Dataset generation handler ──
  const handleGenerateDataset = useCallback(async () => {
    if (!datasetName.trim()) return

    setDatasetGenerating(true)
    setDatasetResult(null)

    try {
      const result = await generateDataset({
        name: datasetName.trim(),
        purpose: 'eval',
        bookIds: targetBookIds.length > 0 ? targetBookIds : undefined,
        kPerBook: datasetKPerBook,
        strategy: datasetStrategy,
      })
      setDatasetResult(
        isZh
          ? `✅ 生成完成: ${result.total_generated} 个问题`
          : `✅ Generated ${result.total_generated} questions`,
      )
      setShowDatasetModal(false)
      onGenerated?.()
    } catch (err) {
      setDatasetResult(
        isZh ? '❌ 生成失败' : '❌ Generation failed',
      )
    } finally {
      setDatasetGenerating(false)
    }
  }, [datasetName, targetBookIds, datasetKPerBook, datasetStrategy, isZh, onGenerated])

  // ==========================================================
  // Scope label
  // ==========================================================
  const scopeLabel = useMemo(() => {
    if (targetBooks.length === 0) return isZh ? '暂无可用书籍' : 'No books available'
    if (isSingleBook) return targetBooks[0].title
    return isZh ? `${targetBooks.length} 本书` : `${targetBooks.length} books`
  }, [targetBooks, isSingleBook, isZh])

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-foreground leading-none">
              {isZh ? '问题生成器' : 'Question Generator'}
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {isZh ? '范围' : 'Scope'}: {scopeLabel}
            </p>
          </div>
        </div>
      </div>

      {/* ── Body: two-column when single book with chapters ── */}
      <div className={cn(
        'flex',
        isSingleBook && chapters.length > 0 ? 'flex-row' : 'flex-col',
      )}>
        {/* ── Chapter mini-sidebar (single book only) ──── */}
        {isSingleBook && (
          <div className="border-r border-border bg-muted/20 flex flex-col" style={{ width: 220 }}>
            {/* Chapter sidebar header */}
            <div className="px-3 py-2 border-b border-border">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                {isZh ? '章节筛选' : 'Chapters'}
              </span>
              {selectedChapterKeys.size > 0 && (
                <span className="text-[10px] text-primary ml-1">
                  ({selectedChapterKeys.size})
                </span>
              )}
            </div>

            {/* Chapter list */}
            <div className="flex-1 overflow-y-auto max-h-52">
              {chaptersLoading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground p-3">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  {isZh ? '加载中…' : 'Loading…'}
                </div>
              ) : chapters.length === 0 ? (
                <p className="text-[11px] text-muted-foreground p-3">
                  {isZh ? '无可用章节' : 'No chapters'}
                </p>
              ) : (
                <div className="py-1">
                  {chapters.map((ch) => {
                    const isSelected = selectedChapterKeys.has(ch.id)
                    return (
                      <button
                        key={ch.id}
                        onClick={() => toggleChapter(ch.id)}
                        className={cn(
                          'flex items-center gap-1.5 w-full text-left px-3 py-1.5 transition-colors',
                          'hover:bg-secondary/50',
                          isSelected && 'bg-primary/5',
                        )}
                        style={{ paddingLeft: `${12 + (ch.level - 1) * 12}px` }}
                      >
                        {/* Checkbox indicator */}
                        <div className={cn(
                          'w-3.5 h-3.5 rounded border shrink-0 flex items-center justify-center transition-colors',
                          isSelected
                            ? 'border-primary bg-primary'
                            : 'border-muted-foreground/30'
                        )}>
                          {isSelected && <Check className="h-2.5 w-2.5 text-primary-foreground" strokeWidth={3} />}
                        </div>

                        {/* Chapter title */}
                        <span className={cn(
                          'text-[11px] truncate',
                          isSelected ? 'text-primary font-medium' : 'text-muted-foreground',
                        )}>
                          {ch.number ? `${ch.number} ` : ''}{ch.title}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Chapter footer hint */}
            <div className="px-3 py-1.5 border-t border-border">
              <p className="text-[9px] text-muted-foreground/60">
                {isZh ? '不选则全书生成' : 'No selection = whole book'}
              </p>
            </div>
          </div>
        )}

        {/* ── Right side: controls + feedback ──────────── */}
        <div className="flex-1 p-4 flex flex-col gap-3">
          {/* Controls row */}
          <div className="flex items-center gap-4">
            {/* Count slider */}
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
              <label className="text-[11px] text-muted-foreground whitespace-nowrap">
                {isZh ? '数量' : 'Count'}
              </label>
              <input
                type="range"
                min={1}
                max={20}
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
                className="w-24 h-1 accent-primary"
                disabled={generating}
              />
              <span className="text-xs font-mono text-foreground w-5 text-right">{count}</span>
            </div>

            {/* Generate button */}
            <button
              onClick={handleGenerate}
              disabled={generating || targetBookIds.length === 0}
              className={cn(
                'ml-auto flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                generating
                  ? 'bg-primary/20 text-primary cursor-wait'
                  : targetBookIds.length === 0
                    ? 'bg-muted text-muted-foreground cursor-not-allowed'
                    : 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm'
              )}
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {generating
                ? (isZh ? '生成中…' : 'Generating…')
                : (isZh ? '开始生成' : 'Generate')
              }
            </button>

            {/* QD-06: Generate Dataset button */}
            <button
              onClick={() => {
                setDatasetName(`dataset-${new Date().toISOString().slice(0, 10)}`)
                setShowDatasetModal(true)
              }}
              disabled={generating || targetBookIds.length === 0}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg text-[11px] font-medium transition-all',
                'border border-primary/30 text-primary hover:bg-primary/10',
                (generating || targetBookIds.length === 0) && 'opacity-50 cursor-not-allowed',
              )}
            >
              {isZh ? '生成题集' : 'Dataset'}
            </button>
          </div>

          {/* Generation progress */}
          {generating && (
            <div className="pt-1">
              <GenerationProgress />
            </div>
          )}

          {/* Result feedback */}
          {!generating && resultCount != null && (
            <div className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-xs',
              resultCount > 0
                ? 'bg-emerald-500/10 text-emerald-500'
                : 'bg-amber-500/10 text-amber-500'
            )}>
              <Sparkles className="h-3.5 w-3.5" />
              {resultCount > 0
                ? (isZh ? `成功生成 ${resultCount} 个问题` : `Generated ${resultCount} questions`)
                : (isZh ? '未生成问题' : 'No questions generated')
              }
            </div>
          )}

          {/* Error */}
          {error && !generating && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-destructive/10 text-destructive text-xs">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {error}
            </div>
          )}

          {/* QD-06: Dataset generation result */}
          {datasetResult && !datasetGenerating && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10 text-blue-500 text-xs">
              {datasetResult}
            </div>
          )}
        </div>
      </div>

      {/* QD-06: Dataset Generation Modal */}
      {showDatasetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card border border-border rounded-xl shadow-2xl p-6 w-96 max-w-[90vw] space-y-4">
            <h3 className="text-sm font-bold text-foreground">
              {isZh ? '生成问题题集' : 'Generate Question Dataset'}
            </h3>

            {/* Dataset name */}
            <div>
              <label className="block text-[11px] text-muted-foreground mb-1">
                {isZh ? '题集名称' : 'Dataset Name'}
              </label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                className="w-full rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
                placeholder="e.g. v1-retriever-eval"
              />
            </div>

            {/* Strategy */}
            <div>
              <label className="block text-[11px] text-muted-foreground mb-1">
                {isZh ? '采样策略' : 'Sampling Strategy'}
              </label>
              <select
                value={datasetStrategy}
                onChange={(e) => setDatasetStrategy(e.target.value)}
                className="w-full rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
              >
                <option value="stratified">Stratified (text 60%, table 20%, image 20%)</option>
                <option value="chapter_balanced">Chapter Balanced</option>
                <option value="random">Random</option>
              </select>
            </div>

            {/* K per book */}
            <div>
              <label className="flex items-center justify-between text-[11px] text-muted-foreground mb-1">
                <span>{isZh ? '每本书 Chunk 数' : 'Chunks per book'}</span>
                <span className="font-mono text-foreground">{datasetKPerBook}</span>
              </label>
              <input
                type="range"
                min={3}
                max={50}
                value={datasetKPerBook}
                onChange={(e) => setDatasetKPerBook(Number(e.target.value))}
                className="w-full accent-primary"
              />
            </div>

            {/* Scope info */}
            <div className="text-[10px] text-muted-foreground bg-muted/50 rounded-lg px-3 py-2">
              {isZh ? '范围' : 'Scope'}: {scopeLabel}
              {' • '}
              {isZh ? '预估' : 'Est.'}: ~{targetBooks.length * datasetKPerBook} {isZh ? '个问题' : 'questions'}
            </div>

            {/* Actions */}
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDatasetModal(false)}
                className="px-4 py-2 rounded-lg border border-border text-muted-foreground text-sm hover:bg-secondary transition-colors"
                disabled={datasetGenerating}
              >
                {isZh ? '取消' : 'Cancel'}
              </button>
              <button
                onClick={handleGenerateDataset}
                disabled={datasetGenerating || !datasetName.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {datasetGenerating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                {datasetGenerating
                  ? (isZh ? '生成中…' : 'Generating…')
                  : (isZh ? '开始生成' : 'Generate Dataset')
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
