/**
 * RetrievalDiagnostics — BM25/Vector/Both hit distribution + strategy advice (EV2-T5-02).
 *
 * Renders a horizontal stacked bar + donut-style visual showing the
 * retrieval strategy breakdown, plus context-aware strategy suggestions.
 *
 * Can be embedded in EvalScoreCard, TracePanel, or EvaluationPage.
 *
 * Usage: <RetrievalDiagnostics evaluation={evalResult} locale="en" />
 */

'use client'

import { useMemo } from 'react'
import {
  Search, Shuffle, Grid3X3, ArrowUpRight,
  CheckCircle2, AlertTriangle, Info,
  Navigation,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { EvaluationResult } from '../types'

// ============================================================
// Constants
// ============================================================

/** Color palette for retrieval sources. */
const SOURCE_COLORS = {
  bm25:   { bar: 'bg-blue-500',    dot: 'bg-blue-400',    text: 'text-blue-400',    label: 'BM25',   labelFr: '关键词' },
  vector: { bar: 'bg-purple-500',  dot: 'bg-purple-400',  text: 'text-purple-400',  label: 'Vector', labelFr: '向量' },
  both:   { bar: 'bg-emerald-500', dot: 'bg-emerald-400', text: 'text-emerald-400', label: 'Both',   labelFr: '双路' },
} as const

/** Routing decision display. */
const ROUTING_META: Record<string, { icon: string; label: string; labelFr: string; cls: string }> = {
  standard: { icon: '🔍', label: 'Standard RAG', labelFr: '标准检索', cls: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  smart:    { icon: '⚡', label: 'Smart Retrieve', labelFr: '智能检索', cls: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
  deep:     { icon: '🧠', label: 'Deep Solve', labelFr: '深度推理', cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
}

// ============================================================
// Strategy suggestion engine
// ============================================================
interface StrategySuggestion {
  type: 'success' | 'warning' | 'info'
  text: string
  textFr: string
}

function generateStrategySuggestions(
  bm25: number,
  vector: number,
  both: number,
  total: number,
  retrievalMode: string | null,
  ragScore: number | null,
): StrategySuggestion[] {
  const suggestions: StrategySuggestion[] = []
  if (total === 0) return suggestions

  const bm25Ratio = bm25 / total
  const vectorRatio = vector / total
  const bothRatio = both / total

  // High BM25 dominance → keyword search effective
  if (bm25Ratio > 0.6) {
    suggestions.push({
      type: 'info',
      text: `BM25 dominates (${(bm25Ratio * 100).toFixed(0)}%) — keyword matching is effective for this query.`,
      textFr: `BM25 占主导 (${(bm25Ratio * 100).toFixed(0)}%) — 关键词匹配对此查询很有效。`,
    })
  }

  // High vector dominance → semantic search needed
  if (vectorRatio > 0.7) {
    suggestions.push({
      type: 'info',
      text: `Vector dominates (${(vectorRatio * 100).toFixed(0)}%) — semantic understanding is key for this query.`,
      textFr: `向量占主导 (${(vectorRatio * 100).toFixed(0)}%) — 语义理解对此查询至关重要。`,
    })
  }

  // High overlap → both strategies find same chunks (redundancy)
  if (bothRatio > 0.5) {
    suggestions.push({
      type: 'success',
      text: `High overlap (${(bothRatio * 100).toFixed(0)}%) — both strategies agree, high confidence retrieval.`,
      textFr: `高重叠率 (${(bothRatio * 100).toFixed(0)}%) — 两种策略一致，检索置信度高。`,
    })
  }

  // Zero BM25 in hybrid mode → BM25 not contributing
  if (retrievalMode === 'hybrid' && bm25 === 0 && both === 0) {
    suggestions.push({
      type: 'warning',
      text: 'BM25 retrieved zero results in hybrid mode — consider reviewing keyword index or query terms.',
      textFr: 'BM25 在混合模式中未检索到结果 — 考虑检查关键词索引或查询术语。',
    })
  }

  // Low RAG score
  if (ragScore != null && ragScore < 0.5) {
    suggestions.push({
      type: 'warning',
      text: `RAG score is low (${(ragScore * 100).toFixed(0)}%) — consider increasing top_k or reviewing chunk quality.`,
      textFr: `RAG 分数较低 (${(ragScore * 100).toFixed(0)}%) — 考虑增加 top_k 或审查分块质量。`,
    })
  }

  return suggestions
}

// ============================================================
// Props
// ============================================================
interface RetrievalDiagnosticsProps {
  /** Evaluation result with retrieval strategy data. */
  evaluation: EvaluationResult
  /** UI locale. */
  locale?: 'en' | 'fr'
  /** If true, renders in compact inline mode. */
  compact?: boolean
}

// ============================================================
// Component
// ============================================================
export default function RetrievalDiagnostics({
  evaluation,
  locale = 'en',
  compact = false,
}: RetrievalDiagnosticsProps) {
  const isFr = locale === 'fr'

  const bm25 = evaluation.bm25Hits ?? 0
  const vector = evaluation.vectorHits ?? 0
  const both = evaluation.bothHits ?? 0
  const total = bm25 + vector + both
  const mode = evaluation.retrievalMode

  const suggestions = useMemo(
    () => generateStrategySuggestions(bm25, vector, both, total, mode, evaluation.ragScore),
    [bm25, vector, both, total, mode, evaluation.ragScore],
  )

  // Percentages for bar segments
  const pcts = total > 0
    ? { bm25: (bm25 / total) * 100, vector: (vector / total) * 100, both: (both / total) * 100 }
    : { bm25: 0, vector: 0, both: 0 }

  // ── Compact mode ────────────────────────────────
  if (compact) {
    return (
      <div className="flex items-center gap-2 text-[9px] text-muted-foreground">
        {mode === 'hybrid'
          ? <><Shuffle className="h-3 w-3 shrink-0" /> Hybrid</>
          : <><Grid3X3 className="h-3 w-3 shrink-0" /> Vector</>
        }
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden flex">
          {pcts.bm25 > 0 && (
            <div className={cn('h-full', SOURCE_COLORS.bm25.bar)} style={{ width: `${pcts.bm25}%` }} />
          )}
          {pcts.both > 0 && (
            <div className={cn('h-full', SOURCE_COLORS.both.bar)} style={{ width: `${pcts.both}%` }} />
          )}
          {pcts.vector > 0 && (
            <div className={cn('h-full', SOURCE_COLORS.vector.bar)} style={{ width: `${pcts.vector}%` }} />
          )}
        </div>
        <span className="tabular-nums">{total}</span>
      </div>
    )
  }

  // ── Full diagnostic panel ──────────────────────
  return (
    <div className="rounded-lg border border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-purple-500/5 p-3 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-blue-400" />
        <span className="text-[11px] font-semibold text-foreground">
          {isFr ? '检索策略诊断' : 'Retrieval Strategy Diagnostics'}
        </span>
        <div className="flex-1" />
        <span className={cn(
          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-medium border',
          mode === 'hybrid'
            ? 'text-blue-400 bg-blue-500/10 border-blue-500/30'
            : 'text-purple-400 bg-purple-500/10 border-purple-500/30',
        )}>
          {mode === 'hybrid'
            ? <><Shuffle className="h-3 w-3" />{isFr ? '混合' : 'Hybrid'}</>
            : <><Grid3X3 className="h-3 w-3" />{isFr ? '纯向量' : 'Vector-only'}</>
          }
        </span>
      </div>

      {/* Stacked bar chart */}
      <div className="space-y-1.5">
        <div className="h-4 rounded-full bg-muted/50 overflow-hidden flex">
          {pcts.bm25 > 0 && (
            <div
              className={cn('h-full transition-all duration-500 flex items-center justify-center', SOURCE_COLORS.bm25.bar)}
              style={{ width: `${pcts.bm25}%` }}
            >
              {pcts.bm25 > 15 && (
                <span className="text-[8px] font-bold text-white/90">{pcts.bm25.toFixed(0)}%</span>
              )}
            </div>
          )}
          {pcts.both > 0 && (
            <div
              className={cn('h-full transition-all duration-500 flex items-center justify-center', SOURCE_COLORS.both.bar)}
              style={{ width: `${pcts.both}%` }}
            >
              {pcts.both > 15 && (
                <span className="text-[8px] font-bold text-white/90">{pcts.both.toFixed(0)}%</span>
              )}
            </div>
          )}
          {pcts.vector > 0 && (
            <div
              className={cn('h-full transition-all duration-500 flex items-center justify-center', SOURCE_COLORS.vector.bar)}
              style={{ width: `${pcts.vector}%` }}
            >
              {pcts.vector > 15 && (
                <span className="text-[8px] font-bold text-white/90">{pcts.vector.toFixed(0)}%</span>
              )}
            </div>
          )}
          {total === 0 && (
            <div className="h-full w-full flex items-center justify-center">
              <span className="text-[8px] text-muted-foreground">{isFr ? '无数据' : 'No data'}</span>
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3">
          {([['bm25', bm25], ['vector', vector], ['both', both]] as const).map(([key, count]) => (
            <div key={key} className="flex items-center gap-1">
              <span className={cn('inline-block w-2 h-2 rounded-full', SOURCE_COLORS[key].dot)} />
              <span className={cn('text-[9px] font-medium', SOURCE_COLORS[key].text)}>
                {isFr ? SOURCE_COLORS[key].labelFr : SOURCE_COLORS[key].label}
              </span>
              <span className="text-[9px] text-muted-foreground tabular-nums">{count}</span>
            </div>
          ))}
          <span className="ml-auto text-[8px] text-muted-foreground tabular-nums">
            {isFr ? `共 ${total} 条` : `${total} total`}
          </span>
        </div>
      </div>

      {/* Routing decision (EV2-T4-02) */}
      {evaluation.routingDecision && (
        <div className="rounded-md border border-border/30 bg-card/30 p-2 space-y-1">
          <div className="flex items-center gap-1.5">
            <Navigation className="h-3 w-3 text-muted-foreground" />
            <span className="text-[9px] font-medium text-muted-foreground">
              {isFr ? '路由决策' : 'Routing Decision'}
            </span>
            <span className={cn(
              'inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-semibold border',
              ROUTING_META[evaluation.routingDecision]?.cls ?? 'text-zinc-400',
            )}>
              {ROUTING_META[evaluation.routingDecision]?.icon}{' '}
              {isFr
                ? ROUTING_META[evaluation.routingDecision]?.labelFr
                : ROUTING_META[evaluation.routingDecision]?.label
              }
            </span>
            {evaluation.routingCorrect != null && (
              <span className={cn(
                'inline-flex items-center gap-0.5 text-[8px] font-semibold ml-auto',
                evaluation.routingCorrect ? 'text-emerald-400' : 'text-red-400',
              )}>
                {evaluation.routingCorrect
                  ? <><CheckCircle2 className="h-3 w-3" />{isFr ? '正确' : 'Correct'}</>
                  : <><AlertTriangle className="h-3 w-3" />{isFr ? '不当' : 'Incorrect'}</>
                }
              </span>
            )}
          </div>
          {evaluation.routingReasoning && (
            <p className="text-[8px] text-muted-foreground/70 leading-relaxed pl-4">
              {evaluation.routingReasoning}
            </p>
          )}
        </div>
      )}

      {/* Strategy suggestions */}
      {suggestions.length > 0 && (
        <div className="space-y-1">
          {suggestions.map((s, i) => {
            const SIcon = s.type === 'success' ? CheckCircle2
              : s.type === 'warning' ? AlertTriangle
              : Info
            const iconCls = s.type === 'success' ? 'text-emerald-400'
              : s.type === 'warning' ? 'text-amber-400'
              : 'text-blue-400'
            return (
              <div key={i} className="flex items-start gap-1.5 text-[9px] text-muted-foreground">
                <SIcon className={cn('h-3 w-3 shrink-0 mt-0.5', iconCls)} />
                <span>{isFr ? s.textFr : s.text}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
