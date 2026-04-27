/**
 * InlineEvalCard — User-friendly evaluation score card (UEP-T3-01).
 *
 * Compact, non-technical evaluation display for the chat interface.
 * Maps RAG/LLM/Answer terminology to user-friendly labels:
 *   RAG Score      → Source Quality / 来源质量
 *   LLM Score      → Accuracy / 准确度
 *   Answer Score   → Answer Quality / 回答质量
 *   Question Depth → Question Depth / 问题深度
 *   Overall Score  → Overall / 综合评分
 *
 * Usage: <InlineEvalCard evaluation={evalResult} />
 */

'use client'

import { cn } from '@/features/shared/utils'
import type { EvaluationResult } from '@/features/engine/evaluation/types'

// ============================================================
// Constants
// ============================================================

/** Grade thresholds — matches EvalScoreCard for consistency. */
type Grade = 'excellent' | 'good' | 'fair' | 'poor' | 'none'

function getGrade(score: number | null | undefined): Grade {
  if (score == null) return 'none'
  if (score >= 0.85) return 'excellent'
  if (score >= 0.7) return 'good'
  if (score >= 0.5) return 'fair'
  return 'poor'
}

const GRADE_COLORS: Record<Grade, { text: string; bar: string; bg: string }> = {
  excellent: { text: 'text-emerald-400', bar: 'bg-emerald-500', bg: 'bg-emerald-500/10' },
  good:      { text: 'text-blue-400',    bar: 'bg-blue-500',    bg: 'bg-blue-500/10' },
  fair:      { text: 'text-amber-400',   bar: 'bg-amber-500',   bg: 'bg-amber-500/10' },
  poor:      { text: 'text-red-400',     bar: 'bg-red-500',     bg: 'bg-red-500/10' },
  none:      { text: 'text-zinc-500',    bar: 'bg-zinc-600',    bg: 'bg-zinc-500/10' },
}

/** User-friendly status labels (no pass/fail jargon). */
const STATUS_LABEL: Record<string, { en: string; icon: string; cls: string }> = {
  pass: { en: 'Good', icon: '✓', cls: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30' },
  fail: { en: 'Needs Improvement', icon: '!', cls: 'text-amber-400 bg-amber-500/15 border-amber-500/30' },
  pending: { en: 'Pending', icon: '…', cls: 'text-zinc-400 bg-zinc-500/15 border-zinc-500/30' },
}

/** Depth label user-friendly mapping. */
const DEPTH_LABEL: Record<string, string> = {
  surface: 'Surface',
  understanding: 'Understanding',
  synthesis: 'Synthesis',
}

/** Score dimension definitions — user-friendly terminology. */
const DIMENSIONS = [
  { key: 'ragScore',    label: 'Source Quality' },
  { key: 'llmScore',    label: 'Accuracy' },
  { key: 'answerScore', label: 'Answer Quality' },
] as const

// ============================================================
// Sub-components
// ============================================================

/** Single score dimension row with progress bar. */
function ScoreRow({ label, score }: { label: string; score: number | null | undefined }) {
  const grade = getGrade(score)
  const colors = GRADE_COLORS[grade]
  const pct = score != null ? Math.round(score * 100) : null

  return (
    <div className="flex items-center gap-2">
      <span className="w-[100px] shrink-0 text-[10px] text-muted-foreground/80 truncate">
        {label}
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-muted/50 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700 ease-out', colors.bar)}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
      <span className={cn('w-8 text-right text-[10px] font-bold tabular-nums', colors.text)}>
        {pct != null ? `${pct}%` : '—'}
      </span>
    </div>
  )
}

// ============================================================
// Props
// ============================================================
interface InlineEvalCardProps {
  /** Persisted evaluation result from Payload. */
  evaluation: EvaluationResult
}

// ============================================================
// Component
// ============================================================
export default function InlineEvalCard({ evaluation }: InlineEvalCardProps) {
  const overall = evaluation.overallScore
  const overallPct = overall != null ? Math.round(overall * 100) : null
  const overallGrade = getGrade(overall)
  const overallColors = GRADE_COLORS[overallGrade]

  const status = evaluation.status ?? 'pending'
  const statusMeta = STATUS_LABEL[status] ?? STATUS_LABEL.pending

  const depth = evaluation.questionDepth
  const depthLabel = depth ? DEPTH_LABEL[depth] ?? depth : null

  return (
    <div className="space-y-2.5">
      {/* ── Overall score header ── */}
      <div className="flex items-center gap-2.5">
        {overallPct != null && (
          <span className={cn('text-lg font-bold tabular-nums leading-none', overallColors.text)}>
            {overallPct}%
          </span>
        )}
        <span className={cn(
          'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold',
          statusMeta.cls,
        )}>
          <span className="text-[10px]">{statusMeta.icon}</span>
          {statusMeta.en}
        </span>
        {depthLabel && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-md bg-muted/40 px-1.5 py-0.5 text-[10px] text-muted-foreground">
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 7.5 7.5 3m0 0L12 7.5M7.5 3v13.5m13.5-3L16.5 18m0 0L12 13.5m4.5 4.5V6" />
            </svg>
            {depthLabel}
          </span>
        )}
      </div>

      {/* ── Score dimensions ── */}
      <div className="space-y-1.5">
        {DIMENSIONS.map(dim => (
          <ScoreRow
            key={dim.key}
            label={dim.label}
            score={(evaluation as any)[dim.key]}
          />
        ))}
      </div>
    </div>
  )
}
