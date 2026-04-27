/**
 * EvalScoreCard — Four-category evaluation score card (EV2-T5-01).
 *
 * Displays RAG / LLM / Answer / Question scores in a compact,
 * color-coded card layout with expandable detail dimensions.
 *
 * Usage: <EvalScoreCard evaluation={evalResult} locale="en" />
 */

'use client'

import { useState } from 'react'
import {
  Search, Bot, Sparkles, FileText,
  ChevronDown,
  CheckCircle2, XCircle, Clock,
  Shuffle, Grid3X3,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { EvaluationResult, EvalStatus } from '../types'

// ============================================================
// Constants
// ============================================================

/** Four evaluation categories with display metadata. */
const CATEGORIES = [
  {
    key: 'rag' as const,
    label: 'RAG',
    labelFr: '检索',
    Icon: Search,
    gradient: 'from-blue-500/20 to-cyan-500/10',
    border: 'border-blue-500/30',
    accent: 'text-blue-400',
    accentBg: 'bg-blue-500/10',
    barColor: 'bg-blue-500',
    scoreKey: 'ragScore' as const,
    dimensions: [
      { key: 'contextRelevancy', label: 'Context Relevancy', labelFr: '上下文相关性' },
      { key: 'relevancy', label: 'Source Relevancy', labelFr: '来源相关性' },
    ],
  },
  {
    key: 'llm' as const,
    label: 'LLM',
    labelFr: '模型',
    Icon: Bot,
    gradient: 'from-purple-500/20 to-violet-500/10',
    border: 'border-purple-500/30',
    accent: 'text-purple-400',
    accentBg: 'bg-purple-500/10',
    barColor: 'bg-purple-500',
    scoreKey: 'llmScore' as const,
    dimensions: [
      { key: 'faithfulness', label: 'Faithfulness', labelFr: '忠实度' },
    ],
  },
  {
    key: 'answer' as const,
    label: 'Answer',
    labelFr: '回答',
    Icon: Sparkles,
    gradient: 'from-emerald-500/20 to-green-500/10',
    border: 'border-emerald-500/30',
    accent: 'text-emerald-400',
    accentBg: 'bg-emerald-500/10',
    barColor: 'bg-emerald-500',
    scoreKey: 'answerScore' as const,
    dimensions: [
      { key: 'answerRelevancy', label: 'Answer Relevancy', labelFr: '答案相关性' },
      { key: 'completeness', label: 'Completeness', labelFr: '完整度' },
      { key: 'clarity', label: 'Clarity', labelFr: '清晰度' },
    ],
  },
  {
    key: 'question' as const,
    label: 'Question',
    labelFr: '问题',
    Icon: FileText,
    gradient: 'from-amber-500/20 to-orange-500/10',
    border: 'border-amber-500/30',
    accent: 'text-amber-400',
    accentBg: 'bg-amber-500/10',
    barColor: 'bg-amber-500',
    scoreKey: null,
    dimensions: [],
  },
] as const

/** Depth label display info. */
const DEPTH_META: Record<string, { label: string; labelFr: string; color: string }> = {
  surface:       { label: 'Surface',       labelFr: '浅层', color: 'text-amber-400' },
  understanding: { label: 'Understanding', labelFr: '理解', color: 'text-blue-400' },
  synthesis:     { label: 'Synthesis',     labelFr: '综合', color: 'text-emerald-400' },
}

/** Status badge metadata. */
const STATUS_META: Record<EvalStatus, { Icon: typeof CheckCircle2; label: string; labelFr: string; cls: string }> = {
  pass:    { Icon: CheckCircle2, label: 'Pass',    labelFr: '通过',   cls: 'text-emerald-300 bg-emerald-500/15 border-emerald-500/40' },
  fail:    { Icon: XCircle,      label: 'Fail',    labelFr: '未通过', cls: 'text-red-300 bg-red-500/15 border-red-500/40' },
  pending: { Icon: Clock,        label: 'Pending', labelFr: '待评估', cls: 'text-amber-300 bg-amber-500/15 border-amber-500/40' },
}

type Grade = 'excellent' | 'good' | 'fair' | 'poor' | 'none'

function getGrade(score: number | null | undefined): Grade {
  if (score == null) return 'none'
  if (score >= 0.85) return 'excellent'
  if (score >= 0.7)  return 'good'
  if (score >= 0.5)  return 'fair'
  return 'poor'
}

const GRADE_CLS: Record<Grade, string> = {
  excellent: 'text-emerald-400',
  good:      'text-blue-400',
  fair:      'text-amber-400',
  poor:      'text-red-400',
  none:      'text-zinc-500',
}

// ============================================================
// Props
// ============================================================
interface EvalScoreCardProps {
  /** Persisted evaluation result from Payload. */
  evaluation: EvaluationResult
  /** UI locale ('en' or 'fr' for Chinese). */
  locale?: 'en' | 'fr'
}

// ============================================================
// Component
// ============================================================
export default function EvalScoreCard({ evaluation, locale = 'en' }: EvalScoreCardProps) {
  const isFr = locale === 'fr'
  const [expanded, setExpanded] = useState(true)

  const status = evaluation.status ?? 'pending'
  const statusMeta = STATUS_META[status]
  const overall = evaluation.overallScore

  return (
    <div className="space-y-2">
      {/* ── Header: Overall + Status ── */}
      <div className="flex items-center gap-2">
        <span className={cn(
          'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold border',
          statusMeta.cls,
        )}>
          <statusMeta.Icon className="h-3 w-3" />
          {isFr ? statusMeta.labelFr : statusMeta.label}
        </span>
        {overall != null && (
          <span className={cn('text-sm font-bold tabular-nums', GRADE_CLS[getGrade(overall)])}>
            {(overall * 100).toFixed(0)}%
          </span>
        )}
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => setExpanded(v => !v)}
          className="p-1 rounded hover:bg-secondary transition-colors"
          title={isFr ? '展开详情' : 'Toggle details'}
        >
          <ChevronDown className={cn(
            'h-3 w-3 text-muted-foreground transition-transform duration-200',
            expanded && 'rotate-180',
          )} />
        </button>
      </div>

      {/* ── Summary row: 4 category scores inline ── */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {CATEGORIES.map(cat => {
          const score = cat.scoreKey ? evaluation[cat.scoreKey] : evaluation.questionDepthScore
          const grade = getGrade(score)
          return (
            <div
              key={cat.key}
              className={cn(
                'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5',
                cat.border, cat.accentBg,
              )}
            >
              <cat.Icon className={cn('h-3 w-3', cat.accent)} />
              <span className="text-[9px] font-medium text-muted-foreground">
                {isFr ? cat.labelFr : cat.label}
              </span>
              <span className={cn('text-[10px] font-bold tabular-nums', GRADE_CLS[grade])}>
                {score != null ? (score * 100).toFixed(0) + '%' : '—'}
              </span>
            </div>
          )
        })}
      </div>

      {/* ── Expanded detail: per-dimension bars + question depth ── */}
      {expanded && (
        <div className="grid grid-cols-2 gap-2 animate-in slide-in-from-top-1 fade-in duration-200">
          {CATEGORIES.map(cat => {
            // Question category — special depth display
            if (cat.key === 'question') {
              const depth = evaluation.questionDepth
              const depthMeta = depth ? DEPTH_META[depth] : null
              const normScore = evaluation.questionDepthScore
              return (
                <div
                  key={cat.key}
                  className={cn('rounded-lg border p-2 space-y-1.5', cat.border, 'bg-gradient-to-br', cat.gradient)}
                >
                  <div className="flex items-center gap-1">
                    <cat.Icon className={cn('h-3 w-3', cat.accent)} />
                    <span className="text-[9px] font-semibold text-foreground flex-1">
                      {isFr ? cat.labelFr : cat.label}
                    </span>
                    {normScore != null && (
                      <span className={cn('text-[10px] font-bold tabular-nums', GRADE_CLS[getGrade(normScore)])}>
                        {normScore.toFixed(2)}
                      </span>
                    )}
                  </div>
                  {/* Depth label badge */}
                  {depthMeta && (
                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        'inline-flex px-1.5 py-0.5 rounded-full text-[9px] font-semibold border',
                        depthMeta.color, cat.accentBg, cat.border,
                      )}>
                        {isFr ? depthMeta.labelFr : depthMeta.label}
                      </span>
                    </div>
                  )}
                  {/* Depth score progress bar */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-1">
                      <span className="text-[8px] text-muted-foreground w-24 shrink-0 truncate">
                        {isFr ? '认知深度' : 'Depth'}
                      </span>
                      <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all duration-500', cat.barColor)}
                          style={{ width: `${(normScore ?? 0) * 100}%` }}
                        />
                      </div>
                      <span className={cn('text-[9px] font-bold tabular-nums w-7 text-right', GRADE_CLS[getGrade(normScore)])}>
                        {normScore != null ? normScore.toFixed(2) : '—'}
                      </span>
                    </div>
                  </div>
                </div>
              )
            }

            // RAG / LLM / Answer — score bars
            const aggScore = cat.scoreKey ? evaluation[cat.scoreKey] : null
            return (
              <div
                key={cat.key}
                className={cn('rounded-lg border p-2 space-y-1.5', cat.border, 'bg-gradient-to-br', cat.gradient)}
              >
                <div className="flex items-center gap-1">
                  <cat.Icon className={cn('h-3 w-3', cat.accent)} />
                  <span className="text-[9px] font-semibold text-foreground flex-1">
                    {isFr ? cat.labelFr : cat.label}
                  </span>
                  {aggScore != null && (
                    <span className={cn('text-[10px] font-bold tabular-nums', GRADE_CLS[getGrade(aggScore)])}>
                      {aggScore.toFixed(2)}
                    </span>
                  )}
                </div>
                <div className="space-y-1">
                  {cat.dimensions.map(dim => {
                    const val = (evaluation as any)[dim.key] as number | null
                    return (
                      <div key={dim.key} className="flex items-center gap-1">
                        <span className="text-[8px] text-muted-foreground w-24 shrink-0 truncate">
                          {isFr ? dim.labelFr : dim.label}
                        </span>
                        <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                          <div
                            className={cn('h-full rounded-full transition-all duration-500', cat.barColor)}
                            style={{ width: `${(val ?? 0) * 100}%` }}
                          />
                        </div>
                        <span className={cn('text-[9px] font-bold tabular-nums w-7 text-right', GRADE_CLS[getGrade(val)])}>
                          {val != null ? val.toFixed(2) : '—'}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}

          {/* Retrieval strategy breakdown */}
          {evaluation.retrievalMode && (
            <div className="col-span-2 flex items-center gap-2 px-1 text-[9px] text-muted-foreground">
              <span className="font-medium text-foreground/70">
                {isFr ? '检索策略' : 'Retrieval'}:
              </span>
              <span className="inline-flex items-center gap-0.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500" />
                BM25 {evaluation.bm25Hits ?? 0}
              </span>
              <span className="inline-flex items-center gap-0.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-purple-500" />
                Vector {evaluation.vectorHits ?? 0}
              </span>
              <span className="inline-flex items-center gap-0.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Both {evaluation.bothHits ?? 0}
              </span>
              <span className="ml-auto text-[8px] opacity-60">
                {evaluation.retrievalMode === 'hybrid'
                  ? <><Shuffle className="inline h-2.5 w-2.5 mr-0.5" /> Hybrid</>
                  : <><Grid3X3 className="inline h-2.5 w-2.5 mr-0.5" /> Vector-only</>
                }
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
