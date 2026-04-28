/**
 * RetrieverTestPage — Retrieval debug console with strategy comparison.
 *
 * Route: /engine/retrievers
 *
 * Features:
 *   - Single query mode: BM25+Vector hybrid retrieval
 *   - Comparison mode: run same query with different configs side-by-side
 *   - Controls: top_k slider, LLMRerank toggle, book scope filter
 *
 * Calls POST /engine/retrievers/search via api.ts.
 *
 * Ref: S2-FE-02 + S2-FE-03
 */

'use client'

import { useState, useCallback } from 'react'
import {
  Search, Play, Loader2, BookOpen,
  RotateCcw, ArrowUpDown, FileText,
  Columns2, LayoutList, Zap, Shield,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import { useBooks } from '@/features/shared/books'
import { retrieveSearch, type RetrieveResponse, type RetrieveResult } from '../api'
import QuestionPicker from '@/features/shared/components/QuestionPicker'
import type { Question } from '@/features/engine/question_gen/types'

// ============================================================
// Types
// ============================================================
interface ComparisonRun {
  label: string
  config: { top_k: number; reranker: boolean }
  response: RetrieveResponse | null
  loading: boolean
  error: string | null
}

// ============================================================
// Component
// ============================================================
export default function RetrieverTestPage() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  // ── Query state ──
  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(5)
  const [useReranker, setUseReranker] = useState(false)
  const [selectedBookIds, setSelectedBookIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<RetrieveResponse | null>(null)

  // ── QuestionPicker state (QD-08) ──
  const [activeSourceChunkId, setActiveSourceChunkId] = useState<string | null>(null)
  const [pickerDatasetHint, setPickerDatasetHint] = useState<string | null>(null)

  // ── Comparison mode ──
  const [compareMode, setCompareMode] = useState(false)
  const [compareRuns, setCompareRuns] = useState<ComparisonRun[]>([])
  const [compareLoading, setCompareLoading] = useState(false)

  // ── Elapsed time tracking ──
  const [elapsedMs, setElapsedMs] = useState<number | null>(null)

  const { books } = useBooks({ status: 'indexed' })

  // ── Execute single search ──
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || loading) return

    setLoading(true)
    setError(null)
    setResponse(null)
    setElapsedMs(null)

    const start = performance.now()
    try {
      const data = await retrieveSearch({
        question: question.trim(),
        top_k: topK,
        book_id_strings: selectedBookIds.length > 0 ? selectedBookIds : [],
        reranker: useReranker ? 'llm' : null,
      })
      setElapsedMs(Math.round(performance.now() - start))
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  // ── Execute comparison: run 3 configs in parallel ──
  const handleCompare = useCallback(async () => {
    if (!question.trim() || compareLoading) return

    setCompareLoading(true)
    setCompareRuns([])

    const configs: Array<{ label: string; config: { top_k: number; reranker: boolean } }> = [
      { label: `top_k=${topK}`, config: { top_k: topK, reranker: false } },
      { label: `top_k=${topK} + Rerank`, config: { top_k: topK, reranker: true } },
      { label: `top_k=${Math.min(topK * 2, 20)}`, config: { top_k: Math.min(topK * 2, 20), reranker: false } },
    ]

    const runs: ComparisonRun[] = configs.map((c) => ({
      ...c,
      response: null,
      loading: true,
      error: null,
    }))
    setCompareRuns([...runs])

    // Run all in parallel
    await Promise.all(
      configs.map(async (cfg, i) => {
        try {
          const data = await retrieveSearch({
            question: question.trim(),
            top_k: cfg.config.top_k,
            book_id_strings: selectedBookIds.length > 0 ? selectedBookIds : [],
            reranker: cfg.config.reranker ? 'llm' : null,
          })
          runs[i] = { ...runs[i], response: data, loading: false }
        } catch (err) {
          runs[i] = { ...runs[i], error: err instanceof Error ? err.message : String(err), loading: false }
        }
        setCompareRuns([...runs])
      })
    )

    setCompareLoading(false)
  }, [question, topK, selectedBookIds, compareLoading])

  const handleBookToggle = (bookId: string) => {
    setSelectedBookIds((prev) =>
      prev.includes(bookId)
        ? prev.filter((id) => id !== bookId)
        : [...prev, bookId]
    )
  }

  const handleReset = () => {
    setResponse(null)
    setError(null)
    setCompareRuns([])
    setElapsedMs(null)
  }

  // ── Score color helper ──
  const scoreColor = (score: number | null) => {
    if (score == null) return 'text-muted-foreground'
    if (score >= 0.04) return 'text-emerald-500'
    if (score >= 0.02) return 'text-amber-500'
    return 'text-muted-foreground'
  }

  // ── Render a single result card ──
  const renderResult = (r: RetrieveResult, i: number) => (
    <div
      key={r.chunk_id}
      className="rounded-lg border border-border bg-card p-3.5 hover:border-primary/30 transition-colors"
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-primary text-sm">
            #{i + 1}
          </span>
          <span className={cn('font-mono text-xs font-medium', scoreColor(r.score))}>
            {r.score != null ? r.score.toFixed(4) : '—'}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">
            {r.content_type}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground tabular-nums">
          p.{r.page_idx}
        </span>
      </div>

      {/* Book info */}
      {(r.book_title || r.book_id) && (
        <p className="text-[10px] text-muted-foreground mb-1.5 flex items-center gap-1">
          <BookOpen className="h-2.5 w-2.5" />
          {r.book_title || r.book_id}
          {r.chapter_key && (
            <span className="text-muted-foreground/60"> · {r.chapter_key}</span>
          )}
        </p>
      )}

      {/* Content */}
      <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap line-clamp-4">
        {r.text}
      </p>

      {/* Chunk ID + source hit indicator (QD-08) */}
      <div className="mt-2 pt-1.5 border-t border-border/50 flex items-center justify-between">
        <span className="text-[9px] text-muted-foreground/60 font-mono truncate block">
          {r.chunk_id}
        </span>
        {activeSourceChunkId && r.chunk_id === activeSourceChunkId && (
          <span className="text-[10px] font-semibold text-emerald-500 flex items-center gap-1">
            ✅ Source Hit
          </span>
        )}
        {activeSourceChunkId && r.chunk_id !== activeSourceChunkId && (
          <span className="text-[9px] text-muted-foreground/40">
            ❌
          </span>
        )}
      </div>
    </div>
  )

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Search className="h-5 w-5 text-primary" />
          <div>
            <h1 className="text-lg font-bold text-foreground">
              {isFr ? '检索测试台' : 'Retriever Test Console'}
            </h1>
            <p className="text-xs text-muted-foreground">
              {isFr
                ? '纯检索调试 — 无 LLM 生成，直接查看 BM25 + Vector → RRF 融合结果'
                : 'Retrieve-only debug — no generation, raw BM25 + Vector → RRF results'}
            </p>
          </div>
        </div>

        {/* Mode toggle */}
        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
          <button
            type="button"
            onClick={() => { setCompareMode(false); setCompareRuns([]) }}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              !compareMode ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <LayoutList className="h-3.5 w-3.5" />
            {isFr ? '单次' : 'Single'}
          </button>
          <button
            type="button"
            onClick={() => { setCompareMode(true); setResponse(null); setError(null) }}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              compareMode ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Columns2 className="h-3.5 w-3.5" />
            {isFr ? '对比' : 'Compare'}
          </button>
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Left panel: Config ── */}
        <div className="w-80 border-r border-border flex flex-col bg-muted/30 shrink-0">
          <form
            onSubmit={compareMode ? (e) => { e.preventDefault(); handleCompare() } : handleSubmit}
            className="flex flex-col flex-1 p-4 gap-4"
          >

            {/* Question input */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                {isFr ? '检索查询' : 'Retrieval Query'}
              </label>
              <textarea
                id="retrieve-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={isFr ? '输入检索查询…' : 'Enter retrieval query…'}
                className="w-full h-28 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none resize-none transition-colors"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    if (compareMode) handleCompare()
                    else handleSubmit(e)
                  }
                }}
              />
            </div>

            {/* QD-08: QuestionPicker — select a test question */}
            <div>
              <QuestionPicker
                bookFilter={selectedBookIds.length > 0 ? selectedBookIds : undefined}
                onSelect={(q: Question) => {
                  setQuestion(q.question)
                  setActiveSourceChunkId(q.sourceChunkId || null)
                  setPickerDatasetHint(q.datasetId ? `Dataset #${q.datasetId}` : null)
                }}
              />
              {pickerDatasetHint && (
                <p className="mt-1 text-[10px] text-primary/70">
                  Question from {pickerDatasetHint}
                </p>
              )}
            </div>

            {/* Top K slider */}
            <div>
              <label className="flex items-center justify-between text-xs font-medium text-muted-foreground mb-1.5">
                <span>top_k</span>
                <span className="text-foreground font-mono">{topK}</span>
              </label>
              <input
                type="range"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full accent-primary"
              />
            </div>

            {/* LLMRerank toggle (single mode only) */}
            {!compareMode && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setUseReranker(!useReranker)}
                  className={cn(
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                    useReranker ? 'bg-primary' : 'bg-muted-foreground/30'
                  )}
                >
                  <span
                    className={cn(
                      'inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform',
                      useReranker ? 'translate-x-4' : 'translate-x-0.5'
                    )}
                  />
                </button>
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <ArrowUpDown className="h-3 w-3" />
                  LLMRerank
                </span>
              </div>
            )}

            {/* Comparison mode info */}
            {compareMode && (
              <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 space-y-1">
                <p className="text-xs font-medium text-primary flex items-center gap-1.5">
                  <Zap className="h-3.5 w-3.5" />
                  {isFr ? '对比模式' : 'Comparison Mode'}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {isFr
                    ? `将同时运行 3 种配置: top_k=${topK} / top_k=${topK}+Rerank / top_k=${Math.min(topK * 2, 20)}`
                    : `Runs 3 configs in parallel: top_k=${topK} / top_k=${topK}+Rerank / top_k=${Math.min(topK * 2, 20)}`}
                </p>
              </div>
            )}

            {/* Book filter */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                <BookOpen className="inline h-3 w-3 mr-1" />
                {isFr ? '书籍范围（可选）' : 'Book filter (optional)'}
              </label>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {books.map((b) => (
                  <label
                    key={b.book_id}
                    className="flex items-center gap-2 text-xs text-foreground cursor-pointer hover:bg-secondary/50 rounded px-2 py-1 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedBookIds.includes(b.book_id)}
                      onChange={() => handleBookToggle(b.book_id)}
                      className="accent-primary rounded"
                    />
                    <span className="truncate">{b.title}</span>
                  </label>
                ))}
                {books.length === 0 && (
                  <p className="text-[10px] text-muted-foreground/60 italic px-2">
                    {isFr ? '无已索引书籍' : 'No indexed books'}
                  </p>
                )}
              </div>
            </div>

            {/* Submit / Reset */}
            <div className="flex gap-2 mt-auto">
              <button
                type="submit"
                disabled={!question.trim() || loading || compareLoading}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {(loading || compareLoading) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {compareMode
                  ? (isFr ? '对比检索' : 'Compare')
                  : (isFr ? '检索' : 'Retrieve')}
              </button>
              {(response || compareRuns.length > 0) && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-3 py-2 rounded-lg border border-border text-muted-foreground hover:bg-secondary transition-colors"
                  title={isFr ? '重置' : 'Reset'}
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
              )}
            </div>
          </form>
        </div>

        {/* ── Right panel: Results ── */}
        <div className="flex-1 flex flex-col overflow-hidden">

          <div className="flex-1 overflow-y-auto p-6">

            {/* ── Single mode results ── */}
            {!compareMode && (
              <>
                {/* Empty state */}
                {!response && !loading && !error && (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
                      <Search className="h-8 w-8 text-muted-foreground/30" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground mb-1">
                      {isFr ? '准备就绪' : 'Ready'}
                    </h3>
                    <p className="text-xs text-muted-foreground max-w-sm">
                      {isFr
                        ? '输入查询后点击"检索"查看 BM25 + Vector 融合结果'
                        : 'Enter a query and click "Retrieve" to see hybrid BM25 + Vector results'}
                    </p>
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 mb-4">
                    <p className="text-sm font-medium text-destructive">
                      {isFr ? '检索失败' : 'Retrieval failed'}
                    </p>
                    <p className="text-xs text-destructive/70 mt-1">{error}</p>
                  </div>
                )}

                {/* Loading */}
                {loading && (
                  <div className="flex items-center justify-center h-full gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    <span className="text-sm text-muted-foreground">
                      {isFr ? '检索中…' : 'Retrieving…'}
                    </span>
                  </div>
                )}

                {/* Results */}
                {response && (
                  <div className="space-y-3">
                    {response.results.map((r, i) => renderResult(r, i))}
                  </div>
                )}
              </>
            )}

            {/* ── Compare mode results ── */}
            {compareMode && (
              <>
                {/* Empty state */}
                {compareRuns.length === 0 && !compareLoading && (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
                      <Columns2 className="h-8 w-8 text-muted-foreground/30" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground mb-1">
                      {isFr ? '对比模式' : 'Comparison Mode'}
                    </h3>
                    <p className="text-xs text-muted-foreground max-w-sm">
                      {isFr
                        ? '同一查询同时运行 3 种配置，对比检索质量差异'
                        : 'Run 3 different configs on the same query to compare retrieval quality'}
                    </p>
                  </div>
                )}

                {/* Comparison columns */}
                {compareRuns.length > 0 && (
                  <div className="grid grid-cols-3 gap-4 h-full">
                    {compareRuns.map((run, colIdx) => (
                      <div key={colIdx} className="flex flex-col min-h-0">
                        {/* Column header */}
                        <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border">
                          <span className={cn(
                            'text-xs font-semibold px-2 py-1 rounded-md',
                            colIdx === 0 && 'bg-blue-500/10 text-blue-500',
                            colIdx === 1 && 'bg-purple-500/10 text-purple-500',
                            colIdx === 2 && 'bg-emerald-500/10 text-emerald-500',
                          )}>
                            {run.label}
                          </span>
                          {run.config.reranker && (
                            <Shield className="h-3 w-3 text-purple-500" />
                          )}
                          {run.loading && <Loader2 className="h-3 w-3 animate-spin text-primary" />}
                          {run.response && (
                            <span className="text-[10px] text-muted-foreground ml-auto">
                              {run.response.count} results
                            </span>
                          )}
                        </div>

                        {/* Column results */}
                        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                          {run.error && (
                            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive">
                              {run.error}
                            </div>
                          )}
                          {run.response?.results.map((r, i) => (
                            <div
                              key={r.chunk_id}
                              className="rounded-lg border border-border bg-card p-2.5 hover:border-primary/30 transition-colors"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-mono font-bold text-primary text-xs">
                                    #{i + 1}
                                  </span>
                                  <span className={cn('font-mono text-[10px] font-medium', scoreColor(r.score))}>
                                    {r.score != null ? r.score.toFixed(4) : '—'}
                                  </span>
                                </div>
                                <span className="text-[9px] text-muted-foreground tabular-nums">
                                  p.{r.page_idx}
                                </span>
                              </div>
                              <p className="text-[10px] text-muted-foreground mb-1 flex items-center gap-1 truncate">
                                <BookOpen className="h-2 w-2 shrink-0" />
                                {r.book_title || r.book_id}
                              </p>
                              <p className="text-[10px] text-foreground/80 leading-relaxed line-clamp-3">
                                {r.text}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── Status bar ── */}
          {!compareMode && response && (
            <div className="px-6 py-2 border-t border-border bg-muted/30 flex items-center gap-4 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <FileText className="h-3 w-3" />
                {response.count} {isFr ? '条结果' : 'results'}
              </span>
              {response.reranked && (
                <span className="flex items-center gap-1 text-primary font-medium">
                  <ArrowUpDown className="h-3 w-3" />
                  LLMReranked
                </span>
              )}
              {selectedBookIds.length > 0 && (
                <span className="flex items-center gap-1">
                  <BookOpen className="h-3 w-3" />
                  {selectedBookIds.length} {isFr ? '本书' : 'books filtered'}
                </span>
              )}
              {elapsedMs != null && (
                <span className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  {elapsedMs}ms
                </span>
              )}
              <span className="ml-auto font-mono">
                top_k={topK}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
