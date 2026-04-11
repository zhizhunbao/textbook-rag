/**
 * RetrieverTestPage — Retrieval debug console (retrieve-only, no generation).
 *
 * Route: /engine/retrievers (tab: test)
 *
 * Two-panel layout:
 *   Left:   Query input + config (top_k, reranker toggle, book filter)
 *   Right:  Retrieval results (chunks with score, book, page)
 *
 * Calls POST /engine/retrievers/search — returns raw chunks without LLM synthesis.
 */

'use client'

import { useState } from 'react'
import {
  Search, Play, Loader2, BookOpen,
  RotateCcw, ArrowUpDown, FileText,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'
import { useBooks } from '@/features/shared/books'

// ============================================================
// Types
// ============================================================
interface RetrieveResult {
  chunk_id: string
  score: number | null
  book_id: string
  book_title: string
  page_idx: number
  content_type: string
  chapter_key: string | null
  text: string
}

interface RetrieveResponse {
  query: string
  results: RetrieveResult[]
  count: number
  reranked: boolean
}

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Component
// ============================================================
export default function RetrieverTestPage() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(5)
  const [useReranker, setUseReranker] = useState(false)
  const [selectedBookIds, setSelectedBookIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<RetrieveResponse | null>(null)

  const { books } = useBooks({ status: 'indexed' })

  // ── Execute retrieve-only search ─────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || loading) return

    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const res = await fetch(`${ENGINE}/engine/retrievers/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question.trim(),
          top_k: topK,
          book_id_strings: selectedBookIds.length > 0 ? selectedBookIds : [],
          reranker: useReranker ? 'llm' : null,
        }),
      })

      if (!res.ok) {
        const body = await res.text()
        throw new Error(`${res.status}: ${body}`)
      }

      const data: RetrieveResponse = await res.json()
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

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
  }

  // ── Score color helper ─────────────────────────────────────
  const scoreColor = (score: number | null) => {
    if (score == null) return 'text-muted-foreground'
    if (score >= 0.04) return 'text-emerald-500'
    if (score >= 0.02) return 'text-amber-500'
    return 'text-muted-foreground'
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
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

      {/* ── Main content ───────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Left panel: Config ──────────────────────────── */}
        <div className="w-80 border-r border-border flex flex-col bg-muted/30">
          <form onSubmit={handleSubmit} className="flex flex-col flex-1 p-4 gap-4">

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

            {/* LLMRerank toggle */}
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
                disabled={!question.trim() || loading}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {isFr ? '检索' : 'Retrieve'}
              </button>
              {response && (
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

        {/* ── Right panel: Results ──────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {/* Results area */}
          <div className="flex-1 overflow-y-auto p-6">
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

            {error && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 mb-4">
                <p className="text-sm font-medium text-destructive">
                  {isFr ? '检索失败' : 'Retrieval failed'}
                </p>
                <p className="text-xs text-destructive/70 mt-1">{error}</p>
              </div>
            )}

            {loading && (
              <div className="flex items-center justify-center h-full gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">
                  {isFr ? '检索中…' : 'Retrieving…'}
                </span>
              </div>
            )}

            {response && (
              <div className="space-y-3">
                {response.results.map((r, i) => (
                  <div
                    key={r.chunk_id}
                    className="rounded-lg border border-border bg-card p-4 hover:border-primary/30 transition-colors"
                  >
                    {/* Header row */}
                    <div className="flex items-center justify-between mb-2">
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
                      <span className="text-[10px] text-muted-foreground">
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
                    <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap">
                      {r.text}
                    </p>

                    {/* Chunk ID */}
                    <div className="mt-2 pt-2 border-t border-border/50">
                      <span className="text-[9px] text-muted-foreground/60 font-mono truncate block">
                        {r.chunk_id}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Status bar */}
          {response && (
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
