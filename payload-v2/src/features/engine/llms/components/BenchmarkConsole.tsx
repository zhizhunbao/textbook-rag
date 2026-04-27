'use client'

/**
 * BenchmarkConsole — Model benchmark testing UI.
 *
 * Allows admin to select models + questions, run serial benchmark tests,
 * and compare results side-by-side.
 *
 * 模型测试控制台 — 选择模型 + 问题，串行跑测试，并排对比结果
 */

import { useState, useCallback, useRef, useMemo, useEffect } from 'react'
import {
  Play, Square, Loader2, Clock, Coins, MessageSquare,
  ChevronDown, ChevronUp, Zap, Hash, AlertCircle,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type {
  BenchmarkQuestion,
  BenchmarkResult,
  BenchmarkRunStatus,
  RuntimeModel,
} from '../types'
import { fetchBenchmarkQuestions, testBatch } from '../api'

interface BenchmarkConsoleProps {
  /** 可用模型列表 / Available models to test */
  models: RuntimeModel[]
  isFr?: boolean
}

export function BenchmarkConsole({ models, isFr = false }: BenchmarkConsoleProps) {
  // ── State ────────────────────────────────────────────────────────────────
  const [questions, setQuestions] = useState<BenchmarkQuestion[]>([])
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [selectedQuestions, setSelectedQuestions] = useState<string[]>([])
  const [customQuestion, setCustomQuestion] = useState('')
  const [results, setResults] = useState<BenchmarkResult[]>([])
  const [status, setStatus] = useState<BenchmarkRunStatus>('idle')
  const [runningInfo, setRunningInfo] = useState<{ model: string; question: string; progress: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showQuestions, setShowQuestions] = useState(true)
  const controllerRef = useRef<AbortController | null>(null)

  // ── Load benchmark questions on mount ────────────────────────────────────
  useEffect(() => {
    fetchBenchmarkQuestions().then((qs) => {
      setQuestions(qs)
      // Default: select first 3 questions
      setSelectedQuestions(qs.slice(0, 3).map((q) => q.question))
    }).catch(() => { /* non-blocking */ })
  }, [])

  // ── Auto-select first 2 available models ─────────────────────────────────
  useEffect(() => {
    if (models.length > 0 && selectedModels.length === 0) {
      const avail = models
        .filter((m) => m.availability.status === 'available')
        .slice(0, 2)
        .map((m) => m.name)
      setSelectedModels(avail)
    }
  }, [models, selectedModels.length])

  // ── Toggle model selection ───────────────────────────────────────────────
  const toggleModel = useCallback((name: string) => {
    setSelectedModels((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    )
  }, [])

  // ── Toggle question selection ────────────────────────────────────────────
  const toggleQuestion = useCallback((q: string) => {
    setSelectedQuestions((prev) =>
      prev.includes(q) ? prev.filter((x) => x !== q) : [...prev, q],
    )
  }, [])

  // ── Add custom question ──────────────────────────────────────────────────
  const addCustom = useCallback(() => {
    const q = customQuestion.trim()
    if (q && !selectedQuestions.includes(q)) {
      setSelectedQuestions((prev) => [...prev, q])
      setCustomQuestion('')
    }
  }, [customQuestion, selectedQuestions])

  // ── Build final question list ────────────────────────────────────────────
  const finalQuestions = useMemo(() => selectedQuestions, [selectedQuestions])

  // ── Run benchmark ────────────────────────────────────────────────────────
  const handleRun = useCallback(() => {
    if (selectedModels.length === 0 || finalQuestions.length === 0) return
    setResults([])
    setStatus('running')
    setError(null)
    setRunningInfo(null)

    controllerRef.current = testBatch(
      selectedModels,
      finalQuestions,
      (r) => setResults((prev) => [...prev, r]),
      (info) => setRunningInfo(info),
      () => { setStatus('done'); setRunningInfo(null) },
      (err) => { setStatus('error'); setError(err) },
    )
  }, [selectedModels, finalQuestions])

  // ── Stop benchmark ───────────────────────────────────────────────────────
  const handleStop = useCallback(() => {
    controllerRef.current?.abort()
    setStatus('idle')
    setRunningInfo(null)
  }, [])

  // ── Group results by model ───────────────────────────────────────────────
  const resultsByModel = useMemo(() => {
    const map = new Map<string, BenchmarkResult[]>()
    for (const r of results) {
      const arr = map.get(r.model) || []
      arr.push(r)
      map.set(r.model, arr)
    }
    return map
  }, [results])

  // ── Model averages ───────────────────────────────────────────────────────
  const modelAverages = useMemo(() => {
    const avgs: Record<string, { avgLatency: number; totalTokens: number; totalCost: number; count: number }> = {}
    for (const [model, rs] of resultsByModel) {
      const ok = rs.filter((r) => !r.error)
      avgs[model] = {
        avgLatency: ok.length > 0 ? Math.round(ok.reduce((s, r) => s + r.latencyMs, 0) / ok.length) : 0,
        totalTokens: ok.reduce((s, r) => s + r.totalTokens, 0),
        totalCost: ok.reduce((s, r) => s + r.estimatedCost, 0),
        count: ok.length,
      }
    }
    return avgs
  }, [resultsByModel])

  const isRunning = status === 'running'
  const canRun = selectedModels.length > 0 && finalQuestions.length > 0 && !isRunning

  return (
    <div className="space-y-6">
      {/* ── Model selection ── */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary" />
          {isFr ? 'Sélectionner les modèles' : 'Select Models'}
          <span className="text-[10px] text-muted-foreground font-normal">
            ({selectedModels.length} {isFr ? 'sélectionné(s)' : 'selected'})
          </span>
        </h3>
        <div className="flex flex-wrap gap-2">
          {models
            .filter((m) => m.availability.status === 'available')
            .map((m) => (
              <button
                key={m.name}
                onClick={() => toggleModel(m.name)}
                disabled={isRunning}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-all border',
                  selectedModels.includes(m.name)
                    ? 'bg-primary/15 text-primary border-primary/30'
                    : 'bg-card text-muted-foreground border-border hover:border-primary/20 hover:text-foreground',
                  isRunning && 'opacity-50 cursor-not-allowed',
                )}
              >
                {m.displayName || m.name}
              </button>
            ))}
          {models.filter((m) => m.availability.status === 'available').length === 0 && (
            <p className="text-xs text-muted-foreground">{isFr ? 'Aucun modèle disponible' : 'No available models'}</p>
          )}
        </div>
      </div>

      {/* ── Question selection ── */}
      <div>
        <button
          onClick={() => setShowQuestions((p) => !p)}
          className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3 hover:text-primary transition-colors"
        >
          <MessageSquare className="h-4 w-4 text-primary" />
          {isFr ? 'Questions de test' : 'Test Questions'}
          <span className="text-[10px] text-muted-foreground font-normal">
            ({selectedQuestions.length} {isFr ? 'sélectionnée(s)' : 'selected'})
          </span>
          {showQuestions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>

        {showQuestions && (
          <div className="space-y-2">
            {questions.map((q) => (
              <label
                key={q.id}
                className={cn(
                  'flex items-start gap-2.5 p-2.5 rounded-lg border border-border cursor-pointer transition-all',
                  selectedQuestions.includes(q.question)
                    ? 'bg-primary/5 border-primary/20'
                    : 'hover:bg-card/80',
                  isRunning && 'opacity-50 cursor-not-allowed',
                )}
              >
                <input
                  type="checkbox"
                  checked={selectedQuestions.includes(q.question)}
                  onChange={() => toggleQuestion(q.question)}
                  disabled={isRunning}
                  className="mt-0.5 rounded"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-foreground line-clamp-2">{q.question}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{q.description}</p>
                </div>
                <span className={cn(
                  'shrink-0 px-1.5 py-0.5 rounded text-[9px] font-medium',
                  q.category === 'simple' ? 'bg-emerald-500/10 text-emerald-400' :
                  q.category === 'reasoning' ? 'bg-amber-500/10 text-amber-400' :
                  q.category === 'multilingual' ? 'bg-blue-500/10 text-blue-400' :
                  'bg-purple-500/10 text-purple-400',
                )}>
                  {q.category}
                </span>
              </label>
            ))}

            {/* Custom question input */}
            <div className="flex gap-2 mt-2">
              <input
                type="text"
                value={customQuestion}
                onChange={(e) => setCustomQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addCustom()}
                placeholder={isFr ? 'Ajouter une question personnalisée...' : 'Add custom question...'}
                disabled={isRunning}
                className="flex-1 px-3 py-1.5 rounded-lg text-xs bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
              />
              <button
                onClick={addCustom}
                disabled={!customQuestion.trim() || isRunning}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary text-foreground hover:bg-secondary/80 disabled:opacity-50"
              >
                {isFr ? 'Ajouter' : 'Add'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Run / Stop button ── */}
      <div className="flex items-center gap-3">
        {isRunning ? (
          <button
            onClick={handleStop}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors"
          >
            <Square className="h-4 w-4" />
            {isFr ? 'Arrêter' : 'Stop'}
          </button>
        ) : (
          <button
            onClick={handleRun}
            disabled={!canRun}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20',
              !canRun && 'opacity-50 cursor-not-allowed',
            )}
          >
            <Play className="h-4 w-4" />
            {isFr ? 'Lancer le test' : 'Run Benchmark'}
          </button>
        )}

        {/* Running status */}
        {isRunning && runningInfo && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className="font-medium text-foreground">{runningInfo.model}</span>
            <span>—</span>
            <span className="truncate max-w-[200px]">{runningInfo.question}</span>
            <span className="text-primary font-medium">{runningInfo.progress}</span>
          </div>
        )}

        {status === 'done' && (
          <span className="text-xs text-emerald-400 font-medium">
            ✓ {isFr ? `${results.length} test(s) terminé(s)` : `${results.length} test(s) completed`}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded-lg bg-red-500/5 border border-red-500/10">
          <p className="text-xs text-red-400 flex items-center gap-1.5">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </p>
        </div>
      )}

      {/* ── Results comparison table ── */}
      {results.length > 0 && (
        <div className="space-y-4">
          {/* Summary row */}
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${resultsByModel.size}, 1fr)` }}>
            {Array.from(resultsByModel.keys()).map((model) => {
              const avg = modelAverages[model]
              return (
                <div key={model} className="rounded-xl border border-border bg-card p-4">
                  <h4 className="text-sm font-semibold text-foreground mb-2 truncate">{model}</h4>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="text-center">
                      <p className="text-lg font-bold text-primary">{avg?.avgLatency || 0}</p>
                      <p className="text-[10px] text-muted-foreground">ms avg</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-foreground">{avg?.totalTokens || 0}</p>
                      <p className="text-[10px] text-muted-foreground">tokens</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-emerald-400">
                        {(avg?.totalCost || 0) === 0 ? 'Free' : `$${avg?.totalCost.toFixed(4)}`}
                      </p>
                      <p className="text-[10px] text-muted-foreground">{isFr ? 'coût' : 'cost'}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Detailed results table */}
          <div className="rounded-xl border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-card/80 border-b border-border">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    {isFr ? 'Question' : 'Question'}
                  </th>
                  {Array.from(resultsByModel.keys()).map((model) => (
                    <th key={model} className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      {model}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {finalQuestions.map((q) => (
                  <BenchmarkResultRow
                    key={q}
                    question={q}
                    modelNames={Array.from(resultsByModel.keys())}
                    resultsByModel={resultsByModel}
                    isFr={isFr}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}


// ── Result row sub-component ───────────────────────────────────────────────────
function BenchmarkResultRow({
  question,
  modelNames,
  resultsByModel,
  isFr,
}: {
  question: string
  modelNames: string[]
  resultsByModel: Map<string, BenchmarkResult[]>
  isFr: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr
        className="border-b border-border/50 hover:bg-card/50 transition-colors cursor-pointer"
        onClick={() => setExpanded((p) => !p)}
      >
        <td className="px-4 py-3">
          <p className="text-xs text-foreground line-clamp-2 max-w-[250px]">{question}</p>
        </td>
        {modelNames.map((model) => {
          const r = resultsByModel.get(model)?.find((x) => x.question === question)
          if (!r) {
            return (
              <td key={model} className="px-4 py-3">
                <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
              </td>
            )
          }
          if (r.error) {
            return (
              <td key={model} className="px-4 py-3">
                <span className="text-[10px] text-red-400">{r.error}</span>
              </td>
            )
          }
          return (
            <td key={model} className="px-4 py-3">
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1 text-primary">
                  <Clock className="h-3 w-3" />
                  {r.latencyMs}ms
                </span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Hash className="h-3 w-3" />
                  {r.totalTokens}
                </span>
                <span className="flex items-center gap-1 text-emerald-400">
                  <Coins className="h-3 w-3" />
                  {r.estimatedCost === 0 ? 'Free' : `$${r.estimatedCost.toFixed(4)}`}
                </span>
              </div>
            </td>
          )
        })}
      </tr>
      {/* Expanded answer view */}
      {expanded && (
        <tr className="border-b border-border/30 bg-card/30">
          <td className="px-4 py-3 text-[10px] text-muted-foreground align-top">
            {isFr ? 'Réponses' : 'Answers'}
          </td>
          {modelNames.map((model) => {
            const r = resultsByModel.get(model)?.find((x) => x.question === question)
            return (
              <td key={model} className="px-4 py-3 align-top">
                <p className="text-xs text-foreground whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                  {r?.answer || '—'}
                </p>
              </td>
            )
          })}
        </tr>
      )}
    </>
  )
}
