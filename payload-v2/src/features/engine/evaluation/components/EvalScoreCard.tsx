/**
 * EvalScoreCard — Table-based evaluation score card.
 *
 * Each section is a compact table with columns:
 *   Metric | Score (5-pt) | Description | Judge Model
 *
 * Null scores are hidden. Scores are on a 5-point scale.
 *
 * Usage: <EvalScoreCard evaluation={evalResult} locale="en" />
 */

'use client'

import { useState } from 'react'
import {
  ChevronRight,
  CheckCircle2, XCircle, Clock,
  CircleCheck, CircleX,
  Settings2,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { EvaluationResult, EvalStatus, EvalSuggestion, SuggestionSeverity } from '../types'

// ============================================================
// Grade system — 5-point scale → color
// ============================================================
type Grade = 'excellent' | 'good' | 'fair' | 'poor' | 'none'

function getGrade5(score: number | null | undefined): Grade {
  if (score == null) return 'none'
  // score is on 0-1, mapped to 5-pt
  const s5 = score * 5
  if (s5 >= 4.25) return 'excellent'
  if (s5 >= 3.5) return 'good'
  if (s5 >= 2.5) return 'fair'
  return 'poor'
}

const GRADE_TEXT: Record<Grade, string> = {
  excellent: 'text-emerald-500 dark:text-emerald-400',
  good:      'text-blue-500 dark:text-blue-400',
  fair:      'text-amber-500 dark:text-amber-400',
  poor:      'text-red-500 dark:text-red-400',
  none:      'text-muted-foreground',
}

// ============================================================
// Status badge
// ============================================================
const STATUS_META: Record<EvalStatus, { Icon: typeof CheckCircle2; label: string; cls: string }> = {
  pass:    { Icon: CheckCircle2, label: 'Pass',    cls: 'text-emerald-600 dark:text-emerald-400' },
  fail:    { Icon: XCircle,      label: 'Fail',    cls: 'text-red-600 dark:text-red-400' },
  pending: { Icon: Clock,        label: 'Pending', cls: 'text-amber-600 dark:text-amber-400' },
}

// ============================================================
// Metric definitions with descriptions
// ============================================================
interface MetricDef {
  key: string
  label: string
  desc: string
}

const RESPONSE_METRICS: MetricDef[] = [
  { key: 'faithfulness',    label: 'Faithfulness',      desc: 'Is the answer grounded in context, no hallucination?' },
  { key: 'answerRelevancy', label: 'Answer Relevancy',  desc: 'How relevant is the answer to the question?' },
  { key: 'completeness',    label: 'Completeness',      desc: 'Does the answer cover all question aspects?' },
  { key: 'clarity',         label: 'Clarity',           desc: 'Is the answer clear and well-structured?' },
  { key: 'correctness',     label: 'Correctness',       desc: 'Factual overlap with the reference answer (F1)' },
]

const RETRIEVAL_METRICS: MetricDef[] = [
  { key: 'contextRelevancy', label: 'Context Relevancy', desc: 'Quality of retrieved context for the query' },
  { key: 'relevancy',        label: 'Source Relevancy',  desc: 'Are the retrieved sources relevant to the query?' },
]

const IR_METRICS: MetricDef[] = [
  { key: 'hitRate',      label: 'Hit Rate',      desc: 'Did retrieval include the correct chunk?' },
  { key: 'mrr',          label: 'MRR',           desc: 'Reciprocal rank of the first correct result' },
  { key: 'precisionAtK', label: 'Precision@K',   desc: 'Fraction of top-K results that are correct' },
  { key: 'recallAtK',    label: 'Recall@K',      desc: 'Fraction of correct results retrieved in top-K' },
  { key: 'ndcg',         label: 'NDCG',          desc: 'Are correct results ranked higher?' },
]

/** Suggestion severity styles. */
const SEV_STYLES: Record<SuggestionSeverity, { dot: string; label: string }> = {
  high:   { dot: 'bg-red-500',     label: 'High' },
  medium: { dot: 'bg-amber-500',   label: 'Medium' },
  low:    { dot: 'bg-emerald-500', label: 'Low' },
  info:   { dot: 'bg-blue-500',    label: 'Info' },
}

// ============================================================
// Sub-components
// ============================================================

/** Format a 0-1 score to 5-point scale with color. */
function Score5({ value }: { value: number }) {
  const s5 = value * 5
  const grade = getGrade5(value)
  return (
    <span className={cn('font-semibold tabular-nums', GRADE_TEXT[grade])}>
      {s5.toFixed(2)}
    </span>
  )
}

/** Summary score for collapsed section header (5-pt scale). */
function scoreSummary5(score: number | null | undefined): React.ReactNode {
  if (score == null) return <span className="text-muted-foreground/50">—</span>
  const s5 = score * 5
  const grade = getGrade5(score)
  return (
    <span className={cn('font-semibold', GRADE_TEXT[grade])}>
      {s5.toFixed(1)} / 5
    </span>
  )
}

/** Metric table — renders a table with columns: Metric | Score | Description | Judge */
function MetricTable({
  metrics,
  data,
  judgeModel,
}: {
  metrics: MetricDef[]
  data: Record<string, any>
  judgeModel: string
}) {
  // Filter out null metrics
  const rows = metrics.filter((m) => data[m.key] != null)
  if (rows.length === 0) {
    return <div className="text-[10px] text-muted-foreground/50 py-1">No data available</div>
  }

  return (
    <table className="w-full text-[10px]">
      <thead>
        <tr className="text-muted-foreground/60 border-b border-border/20">
          <th className="text-left font-medium py-1 pr-2">Metric</th>
          <th className="text-right font-medium py-1 px-2 w-[60px]">Score</th>
          <th className="text-left font-medium py-1 px-2">Description</th>
          <th className="text-right font-medium py-1 pl-2 w-[100px]">Judge</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((m) => (
          <tr key={m.key} className="border-b border-border/10 last:border-b-0">
            <td className="py-1.5 pr-2 text-foreground/80">{m.label}</td>
            <td className="py-1.5 px-2 text-right">
              <Score5 value={data[m.key]} />
            </td>
            <td className="py-1.5 px-2 text-muted-foreground/60">{m.desc}</td>
            <td className="py-1.5 pl-2 text-right text-muted-foreground/50 truncate max-w-[100px]" title={judgeModel}>
              {judgeModel || '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Collapsible section wrapper. */
function Section({
  title,
  summary,
  defaultOpen = false,
  children,
}: {
  title: string
  summary: React.ReactNode
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border-b border-border/30 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-left transition-colors hover:bg-muted/30"
      >
        <ChevronRight className={cn(
          'h-3 w-3 shrink-0 text-muted-foreground/60 transition-transform duration-150',
          open && 'rotate-90',
        )} />
        <span className="text-[11px] font-medium text-foreground flex-1">
          {title}
        </span>
        <span className="text-[10px] text-muted-foreground tabular-nums">
          {summary}
        </span>
      </button>
      {open && (
        <div className="px-3 pb-2.5 pt-0.5 animate-in slide-in-from-top-1 fade-in duration-150">
          {children}
        </div>
      )}
    </div>
  )
}

// ============================================================
// Helpers
// ============================================================

/** Compute average of non-null values. */
function avg(...values: (number | null | undefined)[]): number | null {
  const valid = values.filter((v): v is number => v != null)
  if (valid.length === 0) return null
  return valid.reduce((a, b) => a + b, 0) / valid.length
}

// ============================================================
// Props
// ============================================================
interface EvalScoreCardProps {
  /** Persisted evaluation result from Payload. */
  evaluation: EvaluationResult
  /** UI locale ('en' or 'fr' for Chinese). */
  locale?: 'en' | 'zh'
}

// ============================================================
// Component
// ============================================================
export default function EvalScoreCard({ evaluation, locale = 'en' }: EvalScoreCardProps) {
  const status = evaluation.status ?? 'pending'
  const statusMeta = STATUS_META[status]
  const overall = evaluation.overallScore
  const judgeModel = evaluation.judgeModel ?? ''

  // Section averages for collapsed summary
  const responseAvg = avg(
    evaluation.faithfulness,
    evaluation.answerRelevancy,
    evaluation.completeness,
    evaluation.clarity,
    evaluation.correctness,
  ) ?? evaluation.answerScore ?? evaluation.llmScore
  const retrievalAvg = avg(
    evaluation.contextRelevancy,
    evaluation.relevancy,
  ) ?? evaluation.ragScore

  // IR metrics availability
  const hasIR = evaluation.irScore != null || evaluation.hitRate != null

  // Question depth
  const depth = evaluation.questionDepth
  const depthScore = evaluation.questionDepthScore

  // Retrieval strategy
  const hasRetrievalStrategy = evaluation.retrievalMode != null

  // Suggestions
  const hasSuggestions = evaluation.suggestions && evaluation.suggestions.length > 0

  // Build flat data object for table lookups
  const data: Record<string, any> = {
    faithfulness: evaluation.faithfulness,
    answerRelevancy: evaluation.answerRelevancy,
    completeness: evaluation.completeness,
    clarity: evaluation.clarity,
    correctness: evaluation.correctness,
    contextRelevancy: evaluation.contextRelevancy,
    relevancy: evaluation.relevancy,
    hitRate: evaluation.hitRate,
    mrr: evaluation.mrr,
    precisionAtK: evaluation.precisionAtK,
    recallAtK: evaluation.recallAtK,
    ndcg: evaluation.ndcg,
  }

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      {/* ── Overall summary header ── */}
      <div className="flex items-center gap-2 border-b border-border/30 px-3 py-2">
        <span className={cn('inline-flex items-center gap-1 text-[11px] font-semibold', statusMeta.cls)}>
          <statusMeta.Icon className="h-3.5 w-3.5" />
          {statusMeta.label}
        </span>
        {overall != null && (
          <span className={cn('text-sm font-bold tabular-nums', GRADE_TEXT[getGrade5(overall)])}>
            {(overall * 5).toFixed(1)} / 5
          </span>
        )}
        <div className="flex-1" />
        {/* Evaluation metadata */}
        {(judgeModel || evaluation.llmCalls) && (
          <div className="flex items-center gap-1.5 text-[9px] text-muted-foreground/50">
            <Settings2 className="h-2.5 w-2.5" />
            {judgeModel && <span>{judgeModel}</span>}
            {evaluation.llmCalls != null && evaluation.llmCalls > 0 && (
              <span className="tabular-nums">{evaluation.llmCalls} calls</span>
            )}
          </div>
        )}
      </div>

      {/* ── Section 1: Response Quality ── */}
      <Section
        title="Response Quality"
        summary={scoreSummary5(responseAvg)}
        defaultOpen
      >
        <MetricTable metrics={RESPONSE_METRICS} data={data} judgeModel={judgeModel} />
        {/* Guidelines row */}
        {evaluation.guidelinesPass != null && (
          <div className="mt-2 border-t border-border/20 pt-2">
            <GuidelinesRow pass={evaluation.guidelinesPass} feedback={evaluation.guidelinesFeedback} />
          </div>
        )}
      </Section>

      {/* ── Section 2: Retrieval Quality ── */}
      <Section
        title="Retrieval Quality"
        summary={scoreSummary5(retrievalAvg)}
      >
        <MetricTable metrics={RETRIEVAL_METRICS} data={data} judgeModel={judgeModel} />
        {hasIR && (
          <div className="mt-2 border-t border-border/20 pt-2">
            <div className="mb-1 text-[9px] font-medium text-muted-foreground/60 uppercase tracking-wider">
              IR Metrics
            </div>
            <MetricTable metrics={IR_METRICS} data={data} judgeModel={judgeModel} />
          </div>
        )}
      </Section>

      {/* ── Section 3: Question Analysis ── */}
      {(depth || depthScore != null) && (
        <Section
          title="Question Analysis"
          summary={
            depth
              ? <span className={cn('font-medium capitalize', GRADE_TEXT[getGrade5(depthScore)])}>{depth}</span>
              : <span className="text-muted-foreground/50">—</span>
          }
        >
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-muted-foreground/60 border-b border-border/20">
                <th className="text-left font-medium py-1 pr-2">Metric</th>
                <th className="text-right font-medium py-1 px-2 w-[80px]">Value</th>
                <th className="text-left font-medium py-1 px-2">Description</th>
              </tr>
            </thead>
            <tbody>
              {depth && (
                <tr className="border-b border-border/10">
                  <td className="py-1.5 pr-2 text-foreground/80">Depth Level</td>
                  <td className="py-1.5 px-2 text-right">
                    <span className={cn('font-semibold capitalize', GRADE_TEXT[getGrade5(depthScore)])}>{depth}</span>
                  </td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Cognitive complexity: surface → understanding → synthesis</td>
                </tr>
              )}
              {depthScore != null && (
                <tr className="border-b border-border/10 last:border-b-0">
                  <td className="py-1.5 pr-2 text-foreground/80">Depth Score</td>
                  <td className="py-1.5 px-2 text-right">
                    <Score5 value={depthScore} />
                  </td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Normalised depth score (0–5 scale)</td>
                </tr>
              )}
            </tbody>
          </table>
        </Section>
      )}

      {/* ── Section 4: Retrieval Strategy ── */}
      {hasRetrievalStrategy && (
        <Section
          title="Retrieval Strategy"
          summary={
            <span className="text-[10px] font-medium text-muted-foreground">
              {evaluation.retrievalMode === 'hybrid' ? 'Hybrid' : 'Vector-only'}
            </span>
          }
        >
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-muted-foreground/60 border-b border-border/20">
                <th className="text-left font-medium py-1 pr-2">Metric</th>
                <th className="text-right font-medium py-1 px-2 w-[60px]">Value</th>
                <th className="text-left font-medium py-1 px-2">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/10">
                <td className="py-1.5 pr-2 text-foreground/80">Mode</td>
                <td className="py-1.5 px-2 text-right font-semibold text-foreground/80">
                  {evaluation.retrievalMode === 'hybrid' ? 'Hybrid' : 'Vector'}
                </td>
                <td className="py-1.5 px-2 text-muted-foreground/60">Retrieval strategy used</td>
              </tr>
              {evaluation.bm25Hits != null && (
                <tr className="border-b border-border/10">
                  <td className="py-1.5 pr-2 text-foreground/80">BM25 Hits</td>
                  <td className="py-1.5 px-2 text-right font-semibold tabular-nums text-foreground/80">{evaluation.bm25Hits}</td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Sources from BM25 keyword retriever</td>
                </tr>
              )}
              {evaluation.vectorHits != null && (
                <tr className="border-b border-border/10">
                  <td className="py-1.5 pr-2 text-foreground/80">Vector Hits</td>
                  <td className="py-1.5 px-2 text-right font-semibold tabular-nums text-foreground/80">{evaluation.vectorHits}</td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Sources from vector retriever</td>
                </tr>
              )}
              {evaluation.bothHits != null && (
                <tr className="border-b border-border/10">
                  <td className="py-1.5 pr-2 text-foreground/80">Both Hits</td>
                  <td className="py-1.5 px-2 text-right font-semibold tabular-nums text-foreground/80">{evaluation.bothHits}</td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Sources matched by both retrievers</td>
                </tr>
              )}
              {evaluation.routingDecision && (
                <tr className="border-b border-border/10">
                  <td className="py-1.5 pr-2 text-foreground/80">Routing</td>
                  <td className="py-1.5 px-2 text-right font-semibold capitalize text-foreground/80">{evaluation.routingDecision}</td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Router decision: standard / smart / deep</td>
                </tr>
              )}
              {evaluation.routingCorrect != null && (
                <tr className="border-b border-border/10 last:border-b-0">
                  <td className="py-1.5 pr-2 text-foreground/80">Routing Correct</td>
                  <td className="py-1.5 px-2 text-right">
                    {evaluation.routingCorrect
                      ? <CircleCheck className="inline h-3.5 w-3.5 text-emerald-500" />
                      : <CircleX className="inline h-3.5 w-3.5 text-red-500" />}
                  </td>
                  <td className="py-1.5 px-2 text-muted-foreground/60">Was the routing decision appropriate?</td>
                </tr>
              )}
            </tbody>
          </table>
        </Section>
      )}

      {hasSuggestions && (
        <Section
          title="Suggestions"
          summary={
            <span className="text-[10px] text-muted-foreground">
              {evaluation.suggestions!.length}
            </span>
          }
        >
          <div className="space-y-1.5">
            {evaluation.suggestions!.map((s: EvalSuggestion, i: number) => {
              const style = SEV_STYLES[s.severity] || SEV_STYLES.medium
              return (
                <div key={i} className="flex items-start gap-2 text-[10px] text-muted-foreground">
                  <span className={cn('mt-1 inline-block w-1.5 h-1.5 rounded-full shrink-0', style.dot)} />
                  <span>{s.message_en}</span>
                </div>
              )
            })}
          </div>
        </Section>
      )}
    </div>
  )
}

// ============================================================
// Guidelines row (kept as standalone since it has expand logic)
// ============================================================
function GuidelinesRow({
  pass: guidelinesPass,
  feedback,
}: {
  pass: boolean
  feedback: string | null | undefined
}) {
  const [showFeedback, setShowFeedback] = useState(false)
  const hasFeedback = !!feedback?.trim()

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-[10px]">
        <span className="text-muted-foreground/70">Guidelines</span>
        <button
          type="button"
          onClick={() => hasFeedback && setShowFeedback(v => !v)}
          className={cn(
            'inline-flex items-center gap-1 font-medium',
            hasFeedback && 'cursor-pointer hover:opacity-80',
            guidelinesPass ? 'text-emerald-500/70 dark:text-emerald-400/70' : 'text-amber-500/70 dark:text-amber-400/70',
          )}
        >
          {guidelinesPass
            ? <><CircleCheck className="h-3 w-3" /> OK</>
            : <><Settings2 className="h-3 w-3" /> Note</>}
          {hasFeedback && (
            <ChevronRight className={cn(
              'h-2.5 w-2.5 transition-transform duration-150',
              showFeedback && 'rotate-90',
            )} />
          )}
        </button>
      </div>
      {showFeedback && feedback && (
        <div className="ml-2 rounded-md border border-border/40 bg-muted/20 px-2 py-1 text-[9px] leading-snug text-muted-foreground animate-in slide-in-from-top-1 fade-in duration-150">
          {feedback}
        </div>
      )}
    </div>
  )
}
