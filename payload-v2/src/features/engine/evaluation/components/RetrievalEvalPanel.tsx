'use client'
/**
 * RetrievalEvalPanel — Retrieval Quality evaluation panel (QD-11).
 *
 * Displays Hit Rate / MRR metrics and per-question hit/miss details
 * for a given QuestionSet. Supports reranker toggle for A/B comparison.
 *
 * Usage: <RetrievalEvalPanel />
 */

import React, { useState, useEffect } from 'react'
import { Loader2, Search, BarChart3, CheckCircle2, XCircle } from 'lucide-react'
import type { QuestionSet } from '@/features/engine/question_gen/types'
import { fetchQuestionSets } from '@/features/engine/question_gen/api'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ── Types ───────────────────────────────────────────────────────────────────
interface QuestionHitResult {
  question_id: number
  question: string
  source_chunk_id: string
  hit: boolean
  rank: number | null
}

interface RetrievalEvalResponse {
  dataset_id: number
  hit_rate: number
  mrr: number
  total_questions: number
  hits: number
  misses: number
  reranker_used: boolean
  per_question: QuestionHitResult[]
}

// ── Component ───────────────────────────────────────────────────────────────
export default function RetrievalEvalPanel() {
  const [datasets, setDatasets] = useState<QuestionSet[]>([])
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null)
  const [topK, setTopK] = useState(5)
  const [reranker, setReranker] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<RetrievalEvalResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load datasets
  useEffect(() => {
    fetchQuestionSets()
      .then((ds) => {
        const ready = ds.filter((d) => d.status === 'ready')
        setDatasets(ready)
        if (ready.length > 0) setSelectedDataset(ready[0].id)
      })
      .catch(() => {})
  }, [])

  const runEval = async () => {
    if (!selectedDataset) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch(`${ENGINE}/engine/evaluation/retrieval-eval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: selectedDataset,
          top_k: topK,
          reranker,
        }),
      })
      if (!res.ok) throw new Error(`Eval failed: ${res.status}`)
      const data: RetrievalEvalResponse = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      id="retrieval-eval-panel"
      className="rounded-xl border border-border bg-card shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <BarChart3 className="h-4 w-4 text-blue-500" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Retrieval Quality</h3>
            <p className="text-[10px] text-muted-foreground">
              Hit Rate &amp; MRR evaluation on QuestionSet
            </p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="px-5 py-3 border-b border-border space-y-3">
        {/* Dataset selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-muted-foreground shrink-0">Dataset:</label>
          <select
            id="retrieval-eval-dataset"
            value={selectedDataset ?? ''}
            onChange={(e) => setSelectedDataset(Number(e.target.value) || null)}
            className="flex-1 rounded-lg border border-border bg-muted/30 px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none"
          >
            {datasets.length === 0 && <option value="">No datasets</option>}
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.name} ({ds.questionCount} Q)
              </option>
            ))}
          </select>
        </div>

        {/* top_k + reranker + run */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground">top_k:</label>
            <input
              type="range"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-20 accent-primary"
            />
            <span className="text-xs font-mono text-foreground w-5">{topK}</span>
          </div>

          <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={reranker}
              onChange={(e) => setReranker(e.target.checked)}
              className="accent-primary"
            />
            Reranker
          </label>

          <button
            id="retrieval-eval-run"
            onClick={runEval}
            disabled={loading || !selectedDataset}
            className="ml-auto flex items-center gap-2 px-4 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Run Eval
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="px-5 py-4">
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive mb-4">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Metric cards */}
            <div className="grid grid-cols-3 gap-3">
              <MetricCard
                label="Hit Rate"
                value={`${(result.hit_rate * 100).toFixed(1)}%`}
                color={result.hit_rate >= 0.8 ? 'emerald' : result.hit_rate >= 0.5 ? 'amber' : 'red'}
              />
              <MetricCard
                label="MRR"
                value={result.mrr.toFixed(4)}
                color={result.mrr >= 0.7 ? 'emerald' : result.mrr >= 0.4 ? 'amber' : 'red'}
              />
              <MetricCard
                label="Hits / Total"
                value={`${result.hits} / ${result.total_questions}`}
                color="blue"
              />
            </div>

            {/* Reranker indicator */}
            {result.reranker_used && (
              <div className="text-[10px] text-purple-500 flex items-center gap-1 px-2">
                <Search className="h-3 w-3" /> Reranker enabled
              </div>
            )}

            {/* Per-question table */}
            <div className="border border-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted/50 text-muted-foreground">
                    <th className="text-left px-3 py-2 font-medium">Question</th>
                    <th className="text-center px-2 py-2 font-medium w-16">Hit</th>
                    <th className="text-center px-2 py-2 font-medium w-16">Rank</th>
                  </tr>
                </thead>
                <tbody>
                  {result.per_question.map((q, i) => (
                    <tr
                      key={q.question_id || i}
                      className="border-t border-border/50 hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-3 py-2 text-foreground/80 max-w-[400px] truncate" title={q.question}>
                        {q.question}
                      </td>
                      <td className="text-center px-2 py-2">
                        {q.hit ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-400 mx-auto" />
                        )}
                      </td>
                      <td className="text-center px-2 py-2 font-mono text-muted-foreground">
                        {q.rank ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!result && !loading && !error && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-3">
              <BarChart3 className="h-6 w-6 text-muted-foreground/30" />
            </div>
            <p className="text-xs text-muted-foreground">
              Select a dataset and click &quot;Run Eval&quot; to evaluate retrieval quality
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-component: MetricCard ───────────────────────────────────────────────
function MetricCard({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: 'emerald' | 'amber' | 'red' | 'blue'
}) {
  const colorMap = {
    emerald: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    blue: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  }

  return (
    <div className={`rounded-lg border px-4 py-3 text-center ${colorMap[color]}`}>
      <p className="text-[10px] font-medium uppercase tracking-wider opacity-70 mb-1">
        {label}
      </p>
      <p className="text-lg font-bold font-mono">{value}</p>
    </div>
  )
}
