/**
 * InlineEvalCard — Compact user-friendly evaluation summary for chat bubbles.
 *
 * Matches the new EvalScoreCard visual language (no colored gradients,
 * score-only color coding). Shows 3 core dimensions as compact rows
 * plus overall score and status.
 *
 * Usage: <InlineEvalCard evaluation={evalResult} />
 */

'use client'

import { cn } from '@/features/shared/utils'
import type { EvaluationResult } from '@/features/engine/evaluation/types'

// ============================================================
// Grade system — matches EvalScoreCard
// ============================================================
type Grade = 'excellent' | 'good' | 'fair' | 'poor' | 'none'

function getGrade(score: number | null | undefined): Grade {
  if (score == null) return 'none'
  if (score >= 0.85) return 'excellent'
  if (score >= 0.7) return 'good'
  if (score >= 0.5) return 'fair'
  return 'poor'
}

const GRADE_TEXT: Record<Grade, string> = {
  excellent: 'text-emerald-500 dark:text-emerald-400',
  good:      'text-blue-500 dark:text-blue-400',
  fair:      'text-amber-500 dark:text-amber-400',
  poor:      'text-red-500 dark:text-red-400',
  none:      'text-muted-foreground',
}

const GRADE_BAR: Record<Grade, string> = {
  excellent: 'bg-emerald-500',
  good:      'bg-blue-500',
  fair:      'bg-amber-500',
  poor:      'bg-red-500',
  none:      'bg-muted-foreground/30',
}

/** Status display (user-friendly, no jargon). */
const STATUS_LABEL: Record<string, { label: string; cls: string }> = {
  pass: { label: 'Good', cls: 'text-emerald-500 dark:text-emerald-400' },
  fail: { label: 'Needs Improvement', cls: 'text-amber-500 dark:text-amber-400' },
  pending: { label: 'Pending', cls: 'text-muted-foreground' },
}

/** Depth label mapping. */
const DEPTH_LABEL: Record<string, string> = {
  surface: 'Surface',
  understanding: 'Understanding',
  synthesis: 'Synthesis',
}

/** Score row definitions. */
const ROWS = [
  { key: 'responseQuality', label: 'Response Quality' },
  { key: 'retrievalQuality', label: 'Retrieval Quality' },
] as const

// ============================================================
// Sub-components
// ============================================================

/** Compact metric row with thin progress bar. */
function Row({ label, score }: { label: string; score: number | null | undefined }) {
  const grade = getGrade(score)
  const pct = score != null ? Math.round(score * 100) : 0

  return (
    <div className="flex items-center gap-2">
      <span className="w-[105px] shrink-0 text-[10px] text-muted-foreground truncate">
        {label}
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-muted/50 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700 ease-out', GRADE_BAR[grade])}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn('w-8 text-right text-[10px] font-semibold tabular-nums', GRADE_TEXT[grade])}>
        {score != null ? `${(score * 100).toFixed(0)}%` : '—'}
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
  const overallGrade = getGrade(overall)

  const status = evaluation.status ?? 'pending'
  const statusMeta = STATUS_LABEL[status] ?? STATUS_LABEL.pending

  const depth = evaluation.questionDepth
  const depthLabel = depth ? DEPTH_LABEL[depth] ?? depth : null

  // Compute section averages
  const responseScore = evaluation.answerScore ?? evaluation.llmScore ?? null
  const retrievalScore = evaluation.ragScore ?? null

  return (
    <div className="space-y-2">
      {/* ── Overall header ── */}
      <div className="flex items-center gap-2">
        {overall != null && (
          <span className={cn('text-lg font-bold tabular-nums leading-none', GRADE_TEXT[overallGrade])}>
            {(overall * 100).toFixed(0)}%
          </span>
        )}
        <span className={cn('text-[10px] font-semibold', statusMeta.cls)}>
          {statusMeta.label}
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

      {/* ── Score rows ── */}
      <div className="space-y-1">
        <Row label="Response Quality" score={responseScore} />
        <Row label="Retrieval Quality" score={retrievalScore} />
      </div>
    </div>
  )
}
