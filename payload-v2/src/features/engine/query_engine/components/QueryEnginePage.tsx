/**
 * QueryEnginePage — Interactive debug console for the query engine.
 *
 * Route: /engine/query_engine
 *
 * Three-panel layout:
 *   Left:   Query input + config (book filter, top_k, model)
 *   Center: Response display (streaming text + final answer)
 *   Right:  Trace panel (retrieval stats + source list)
 */

'use client'

import { useState, useMemo } from 'react'
import {
  Cpu, Search, Play, Loader2, Zap,
  BookOpen, FileText, AlertCircle, RotateCcw,
  ChevronDown, ChevronRight,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import { useBooks } from '@/features/shared/books'
import { useQueryEngine } from '../useQueryEngine'
import type { QueryRequest, QueryResponse } from '../types'

// ============================================================
// Component
// ============================================================
export default function QueryEnginePage() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  // ==========================================================
  // Query engine hook
  // ==========================================================
  const {
    result,
    streamingText,
    loading,
    error,
    query,
    queryStream,
    reset,
    abort,
  } = useQueryEngine()

  // ==========================================================
  // Form state
  // ==========================================================
  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(5)
  const [selectedBookIds, setSelectedBookIds] = useState<string[]>([])
  const [useStreaming, setUseStreaming] = useState(true)
  const [useReranker, setUseReranker] = useState(false)
  const [traceOpen, setTraceOpen] = useState(true)

  const { books } = useBooks({ status: 'indexed' })

  // ==========================================================
  // Handlers
  // ==========================================================
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || loading) return

    const req: QueryRequest = {
      question: question.trim(),
      top_k: topK,
      filters: selectedBookIds.length > 0
        ? { book_id_strings: selectedBookIds }
        : undefined,
      reranker: useReranker ? 'llm' : null,
    }

    if (useStreaming) {
      await queryStream(req)
    } else {
      await query(req)
    }
  }

  const handleBookToggle = (bookId: string) => {
    setSelectedBookIds((prev) =>
      prev.includes(bookId)
        ? prev.filter((id) => id !== bookId)
        : [...prev, bookId]
    )
  }

  // ==========================================================
  // Derived state
  // ==========================================================
  const displayText = useMemo(() => {
    if (result?.answer) return result.answer
    if (streamingText) return streamingText
    return ''
  }, [result, streamingText])

  const stats = result?.retrieval_stats

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <div className="flex flex-col h-full">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
        <Cpu className="h-5 w-5 text-primary" />
        <div>
          <h1 className="text-lg font-bold text-foreground">
            {isFr ? '查询引擎调试台' : 'Query Engine Console'}
          </h1>
          <p className="text-xs text-muted-foreground">
            {isFr
              ? '端到端查询测试 — 检索 → 合成 → 引用追溯'
              : 'End-to-end query testing — retrieval → synthesis → citation tracing'}
          </p>
        </div>
      </div>

      {/* ── Main content ───────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Left panel: Query input ──────────────────────── */}
        <div className="w-80 border-r border-border flex flex-col bg-muted/30">
          <form onSubmit={handleSubmit} className="flex flex-col flex-1 p-4 gap-4">

            {/* Question input */}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                {isFr ? '问题' : 'Question'}
              </label>
              <textarea
                id="query-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={isFr ? '输入你的问题…' : 'Enter your question…'}
                className="w-full h-28 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none resize-none transition-colors"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    handleSubmit(e)
                  }
                }}
              />
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

            {/* Streaming toggle */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setUseStreaming(!useStreaming)}
                className={cn(
                  'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                  useStreaming ? 'bg-primary' : 'bg-muted-foreground/30'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform',
                    useStreaming ? 'translate-x-4' : 'translate-x-0.5'
                  )}
                />
              </button>
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Zap className="h-3 w-3" />
                {isFr ? '流式输出' : 'Streaming'}
              </span>
            </div>

            {/* Reranker toggle */}
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
                <Search className="h-3 w-3" />
                LLMRerank
              </span>
            </div>

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

            {/* Submit / Abort / Reset buttons */}
            <div className="flex gap-2 mt-auto">
              {loading ? (
                <>
                  <button
                    type="button"
                    onClick={abort}
                    className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-destructive/10 text-destructive px-4 py-2 text-sm font-medium hover:bg-destructive/20 transition-colors"
                  >
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {isFr ? '中断' : 'Abort'}
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="submit"
                    disabled={!question.trim()}
                    className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Play className="h-4 w-4" />
                    {isFr ? '执行查询' : 'Run Query'}
                  </button>
                  {result && (
                    <button
                      type="button"
                      onClick={reset}
                      className="px-3 py-2 rounded-lg border border-border text-muted-foreground hover:bg-secondary transition-colors"
                      title={isFr ? '重置' : 'Reset'}
                    >
                      <RotateCcw className="h-4 w-4" />
                    </button>
                  )}
                </>
              )}
            </div>
          </form>
        </div>

        {/* ── Center panel: Response ───────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {/* Response area */}
          <div className="flex-1 overflow-y-auto p-6">
            {!displayText && !loading && !error && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-4">
                  <Search className="h-8 w-8 text-muted-foreground/30" />
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-1">
                  {isFr ? '准备就绪' : 'Ready'}
                </h3>
                <p className="text-xs text-muted-foreground max-w-sm">
                  {isFr
                    ? '在左侧输入问题，按 ⌘+Enter 或点击"执行查询"开始调试'
                    : 'Enter a question on the left and press ⌘+Enter or "Run Query" to start'}
                </p>
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 mb-4">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-destructive">
                      {isFr ? '查询失败' : 'Query failed'}
                    </p>
                    <p className="text-xs text-destructive/70 mt-1">{error.message}</p>
                  </div>
                </div>
              </div>
            )}

            {displayText && (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                  {displayText}
                  {loading && (
                    <span className="inline-block w-1.5 h-4 bg-primary/60 animate-pulse ml-0.5 align-text-bottom rounded-sm" />
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Stats bar */}
          {stats && (
            <div className="px-6 py-2 border-t border-border bg-muted/30 flex items-center gap-4 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                FTS: {stats.fts_hits}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                Vector: {stats.vector_hits}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                TOC: {stats.toc_hits}
              </span>
              <span className="flex items-center gap-1 ml-auto font-medium text-foreground">
                {isFr ? '融合结果' : 'Fused'}: {stats.fused_count}
              </span>
            </div>
          )}
        </div>

        {/* ── Right panel: Trace / Sources ─────────────────── */}
        {result && (
          <div className="w-72 border-l border-border bg-muted/20 overflow-y-auto">
            <div className="p-4 space-y-4">

              {/* Sources section */}
              <div>
                <button
                  type="button"
                  onClick={() => setTraceOpen(!traceOpen)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-2 hover:text-primary transition-colors"
                >
                  {traceOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  <FileText className="h-3 w-3" />
                  {isFr ? '来源引用' : 'Sources'} ({result.sources.length})
                </button>

                {traceOpen && (
                  <div className="space-y-2">
                    {result.sources.map((source, i) => (
                      <div
                        key={source.source_id}
                        className="rounded-lg border border-border bg-card p-3 text-xs"
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-mono font-bold text-primary">
                            [{source.citation_index ?? i + 1}]
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            p.{source.page_number}
                          </span>
                        </div>
                        {source.book_title && (
                          <p className="text-[10px] text-muted-foreground mb-1 truncate">
                            <BookOpen className="inline h-2.5 w-2.5 mr-0.5" />
                            {source.book_title}
                          </p>
                        )}
                        <p className="text-foreground/80 line-clamp-3 leading-relaxed">
                          {source.snippet}
                        </p>
                        <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-border/50">
                          <span className="text-[9px] text-muted-foreground/60 font-mono truncate max-w-[60%]">
                            {source.source_id}
                          </span>
                          <span className="text-[9px] text-muted-foreground">
                            {(source.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}

                    {result.sources.length === 0 && (
                      <p className="text-[10px] text-muted-foreground/60 italic">
                        {isFr ? '无来源引用' : 'No sources retrieved'}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
