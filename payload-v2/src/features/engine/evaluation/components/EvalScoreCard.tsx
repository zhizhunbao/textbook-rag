/**
 * EvalScoreCard — Table-based collapsible evaluation score card.
 *
 * Replaces the old 4-colored gradient card layout with 5 logical
 * collapsible sections:
 *   S1 Response Quality  — faithfulness + answerRelevancy + completeness + clarity + guidelines
 *   S2 Retrieval Quality  — contextRelevancy + relevancy + IR metrics
 *   S3 Question Analysis  — depth level + depth score
 *   S4 Retrieval Strategy — BM25/Vector distribution + routing
 *   S5 Suggestions        — improvement suggestions (only when present)
 *
 * Design: single bg-card background, score-only color coding (green/blue/amber/red),
 * compact table rows, each section independently collapsible.
 *
 * Usage: <EvalScoreCard evaluation={evalResult} locale="en" />
 */

'use client'

import { useState } from 'react'
import {
  ChevronRight,
  CheckCircle2, XCircle, Clock,
  CircleCheck, CircleX,
  Info,
  Lightbulb, Settings2,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { EvaluationResult, EvalStatus, EvalSuggestion, SuggestionSeverity } from '../types'
import RetrievalDiagnostics from './RetrievalDiagnostics'

// ============================================================
// Grade system — score → color
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

const GRADE_LABEL: Record<Grade, string> = {
  excellent: 'Excellent',
  good:      'Good',
  fair:      'Fair',
  poor:      'Poor',
  none:      'N/A',
}

// ============================================================
// Status badge
// ============================================================
const STATUS_META: Record<EvalStatus, { Icon: typeof CheckCircle2; label: string; labelFr: string; cls: string }> = {
  pass:    { Icon: CheckCircle2, label: 'Pass',    labelFr: '通过',   cls: 'text-emerald-600 dark:text-emerald-400' },
  fail:    { Icon: XCircle,      label: 'Fail',    labelFr: '未通过', cls: 'text-red-600 dark:text-red-400' },
  pending: { Icon: Clock,        label: 'Pending', labelFr: '待评估', cls: 'text-amber-600 dark:text-amber-400' },
}

// ============================================================
// Tooltip map
// ============================================================
const TOOLTIP: Record<string, { en: string; fr: string }> = {
  faithfulness:      { en: 'Is the answer grounded in context, no hallucination?', fr: '回答是否基于给定上下文，无幻觉' },
  answerRelevancy:   { en: 'How relevant is the answer to the question?', fr: '答案与问题的相关程度' },
  completeness:      { en: 'Does the answer cover all question aspects?', fr: '回答是否覆盖问题所有方面' },
  clarity:           { en: 'Is the answer clear, well-structured?', fr: '回答是否清晰、结构良好' },
  correctness:       { en: 'Factual overlap with the reference answer (F1)', fr: '回答与标准答案的事实重合度 (F1)' },
  contextRelevancy:  { en: 'Quality of retrieved context for the query', fr: '检索到的内容与问题是否相关' },
  relevancy:         { en: 'Are the retrieved sources relevant to the query?', fr: '来源是否与问题相关' },
  hitRate:           { en: 'Did retrieval include the correct chunk?', fr: '检索结果中是否包含正确答案' },
  mrr:               { en: 'Reciprocal rank of the first correct result', fr: '第一个正确结果的排名倒数' },
  precisionAtK:      { en: 'Fraction of top-K results that are correct', fr: 'Top-K 结果中正确的比例' },
  recallAtK:         { en: 'Fraction of correct results retrieved in top-K', fr: '正确答案被检索到的比例' },
  ndcg:              { en: 'Are correct results ranked higher?', fr: '正确结果是否排在前面' },
}

/** Depth level display metadata. */
const DEPTH_META: Record<string, { label: string; labelFr: string }> = {
  surface:       { label: 'Surface',       labelFr: '浅层' },
  understanding: { label: 'Understanding', labelFr: '理解' },
  synthesis:     { label: 'Synthesis',     labelFr: '综合' },
}

/** Suggestion severity styles. */
const SEV_STYLES: Record<SuggestionSeverity, { dot: string }> = {
  high:   { dot: 'bg-red-500' },
  medium: { dot: 'bg-amber-500' },
  low:    { dot: 'bg-emerald-500' },
  info:   { dot: 'bg-blue-500' },
}

// ============================================================
// Sub-components
// ============================================================

/** Info tooltip on hover. */
function Tip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex ml-0.5">
      <Info className="h-2.5 w-2.5 text-muted-foreground/40 cursor-help" />
      <span className="pointer-events-none absolute left-4 bottom-0 z-50 w-44 rounded-md bg-popover border border-border px-2 py-1 text-[9px] leading-snug text-popover-foreground shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-150">
        {text}
      </span>
    </span>
  )
}

/** Single metric row: label | progress bar | score | grade. */
function MetricRow({
  label, value, tipKey, isFr,
}: {
  label: string
  value: number | null | undefined
  tipKey?: string
  isFr: boolean
}) {
  const grade = getGrade(value)
  const pct = value != null ? Math.round(value * 100) : 0
  const tip = tipKey ? TOOLTIP[tipKey] : null

  return (
    <div className="flex items-center gap-2 py-0.5">
      <span className="w-[110px] shrink-0 text-[10px] text-muted-foreground truncate inline-flex items-center">
        {label}
        {tip && <Tip text={isFr ? tip.fr : tip.en} />}
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-muted/60 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', GRADE_BAR[grade])}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn(
        'w-[32px] text-right text-[10px] font-semibold tabular-nums',
        GRADE_TEXT[grade],
      )}>
        {value != null ? value.toFixed(2) : '—'}
      </span>
    </div>
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

/** Guidelines pass/fail row with expandable feedback. */
function GuidelinesRow({
  pass: guidelinesPass,
  feedback,
  isFr,
}: {
  pass: boolean
  feedback: string | null | undefined
  isFr: boolean
}) {
  const [showFeedback, setShowFeedback] = useState(false)
  const hasFeedback = !!feedback?.trim()

  return (
    <div className="py-0.5 space-y-1">
      <div className="flex items-center gap-2">
        <span className="w-[110px] shrink-0 text-[10px] text-muted-foreground inline-flex items-center">
          {isFr ? '质量规则' : 'Guidelines'}
          <Tip text={isFr ? '回答是否符合预设质量规则' : 'Does the answer follow all predefined quality rules?'} />
        </span>
        <button
          type="button"
          onClick={() => hasFeedback && setShowFeedback(v => !v)}
          className={cn(
            'inline-flex items-center gap-1 text-[10px] font-semibold',
            hasFeedback && 'cursor-pointer hover:opacity-80',
            guidelinesPass ? 'text-emerald-500 dark:text-emerald-400' : 'text-red-500 dark:text-red-400',
          )}
        >
          {guidelinesPass
            ? <><CircleCheck className="h-3 w-3" />{isFr ? '通过' : 'Pass'}</>
            : <><CircleX className="h-3 w-3" />{isFr ? '未通过' : 'Fail'}</>
          }
          {hasFeedback && (
            <ChevronRight className={cn(
              'h-2.5 w-2.5 transition-transform duration-150',
              showFeedback && 'rotate-90',
            )} />
          )}
        </button>
      </div>
      {showFeedback && feedback && (
        <div className="ml-[110px] rounded-md border border-border/40 bg-muted/20 px-2 py-1 text-[9px] leading-snug text-muted-foreground animate-in slide-in-from-top-1 fade-in duration-150">
          {feedback}
        </div>
      )}
    </div>
  )
}

// ============================================================
// Helpers
// ============================================================

/** Format a score as a colored summary string. */
function scoreSummary(score: number | null | undefined): React.ReactNode {
  if (score == null) return <span className="text-muted-foreground/50">—</span>
  const grade = getGrade(score)
  return (
    <span className={cn('font-semibold', GRADE_TEXT[grade])}>
      {(score * 100).toFixed(0)}%
    </span>
  )
}

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
  locale?: 'en' | 'fr'
}

// ============================================================
// Component
// ============================================================
export default function EvalScoreCard({ evaluation, locale = 'en' }: EvalScoreCardProps) {
  const isFr = locale === 'fr'

  const status = evaluation.status ?? 'pending'
  const statusMeta = STATUS_META[status]
  const overall = evaluation.overallScore

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
  const depthMeta = depth ? DEPTH_META[depth] : null
  const depthScore = evaluation.questionDepthScore

  // Retrieval strategy
  const hasRetrievalStrategy = evaluation.retrievalMode != null

  // Suggestions
  const hasSuggestions = evaluation.suggestions && evaluation.suggestions.length > 0

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      {/* ── Overall summary header ── */}
      <div className="flex items-center gap-2 border-b border-border/30 px-3 py-2">
        <span className={cn('inline-flex items-center gap-1 text-[11px] font-semibold', statusMeta.cls)}>
          <statusMeta.Icon className="h-3.5 w-3.5" />
          {isFr ? statusMeta.labelFr : statusMeta.label}
        </span>
        {overall != null && (
          <span className={cn('text-sm font-bold tabular-nums', GRADE_TEXT[getGrade(overall)])}>
            {(overall * 100).toFixed(0)}%
          </span>
        )}
        <div className="flex-1" />
        {/* Evaluation metadata */}
        {(evaluation.judgeModel || evaluation.llmCalls) && (
          <div className="flex items-center gap-1.5 text-[9px] text-muted-foreground/50">
            <Settings2 className="h-2.5 w-2.5" />
            {evaluation.judgeModel && (
              <span>{evaluation.judgeModel}</span>
            )}
            {evaluation.llmCalls != null && evaluation.llmCalls > 0 && (
              <span className="tabular-nums">{evaluation.llmCalls} {isFr ? '调用' : 'calls'}</span>
            )}
          </div>
        )}
      </div>

      {/* ── Section 1: Response Quality ── */}
      <Section
        title={isFr ? '回答质量' : 'Response Quality'}
        summary={scoreSummary(responseAvg)}
        defaultOpen
      >
        <div className="space-y-0.5">
          <MetricRow label={isFr ? '忠实度' : 'Faithfulness'} value={evaluation.faithfulness} tipKey="faithfulness" isFr={isFr} />
          <MetricRow label={isFr ? '答案相关性' : 'Answer Relevancy'} value={evaluation.answerRelevancy} tipKey="answerRelevancy" isFr={isFr} />
          <MetricRow label={isFr ? '完整度' : 'Completeness'} value={evaluation.completeness} tipKey="completeness" isFr={isFr} />
          <MetricRow label={isFr ? '清晰度' : 'Clarity'} value={evaluation.clarity} tipKey="clarity" isFr={isFr} />
          <MetricRow label={isFr ? '正确性' : 'Correctness'} value={evaluation.correctness} tipKey="correctness" isFr={isFr} />
          {evaluation.guidelinesPass != null && (
            <GuidelinesRow pass={evaluation.guidelinesPass} feedback={evaluation.guidelinesFeedback} isFr={isFr} />
          )}
        </div>
      </Section>

      {/* ── Section 2: Retrieval Quality ── */}
      <Section
        title={isFr ? '检索质量' : 'Retrieval Quality'}
        summary={scoreSummary(retrievalAvg)}
      >
        <div className="space-y-0.5">
          <MetricRow label={isFr ? '上下文相关性' : 'Context Relevancy'} value={evaluation.contextRelevancy} tipKey="contextRelevancy" isFr={isFr} />
          <MetricRow label={isFr ? '来源相关性' : 'Source Relevancy'} value={evaluation.relevancy} tipKey="relevancy" isFr={isFr} />

          {/* IR Metrics sub-group */}
          {hasIR ? (
            <>
              <div className="mt-2 mb-1 text-[9px] font-medium text-muted-foreground/60 uppercase tracking-wider">
                {isFr ? 'IR 检索指标' : 'IR Metrics'}
              </div>
              <MetricRow label="Hit Rate" value={evaluation.hitRate} tipKey="hitRate" isFr={isFr} />
              <MetricRow label="MRR" value={evaluation.mrr} tipKey="mrr" isFr={isFr} />
              <MetricRow label="Precision@K" value={evaluation.precisionAtK} tipKey="precisionAtK" isFr={isFr} />
              <MetricRow label="Recall@K" value={evaluation.recallAtK} tipKey="recallAtK" isFr={isFr} />
              <MetricRow label="NDCG" value={evaluation.ndcg} tipKey="ndcg" isFr={isFr} />
            </>
          ) : (
            <div className="mt-1.5 flex items-center gap-1.5 rounded-md bg-muted/30 px-2 py-1.5 text-[9px] text-muted-foreground/60">
              <Info className="h-3 w-3 shrink-0" />
              {isFr ? 'IR 指标不可用 — 需先生成 Golden Dataset' : 'IR metrics unavailable — generate Golden Dataset first'}
            </div>
          )}
        </div>
      </Section>

      {/* ── Section 3: Question Analysis ── */}
      <Section
        title={isFr ? '问题分析' : 'Question Analysis'}
        summary={
          depthMeta
            ? <span className={cn('font-medium', GRADE_TEXT[getGrade(depthScore)])}>{isFr ? depthMeta.labelFr : depthMeta.label}</span>
            : <span className="text-muted-foreground/50">—</span>
        }
      >
        {depthMeta ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground">
                {isFr ? '认知深度' : 'Depth Level'}:
              </span>
              <span className={cn('text-[10px] font-semibold', GRADE_TEXT[getGrade(depthScore)])}>
                {isFr ? depthMeta.labelFr : depthMeta.label}
              </span>
              {depthScore != null && (
                <span className={cn('text-[10px] tabular-nums', GRADE_TEXT[getGrade(depthScore)])}>
                  ({depthScore.toFixed(2)})
                </span>
              )}
            </div>
            <MetricRow label={isFr ? '深度分数' : 'Depth Score'} value={depthScore} isFr={isFr} />
            {/* Visual scale */}
            <div className="flex items-center gap-1 text-[8px] text-muted-foreground/50">
              <span className={depth === 'surface' ? 'font-semibold text-muted-foreground' : ''}>
                Surface
              </span>
              <span>{'<'}</span>
              <span className={depth === 'understanding' ? 'font-semibold text-muted-foreground' : ''}>
                Understanding
              </span>
              <span>{'<'}</span>
              <span className={depth === 'synthesis' ? 'font-semibold text-muted-foreground' : ''}>
                Synthesis
              </span>
            </div>
          </div>
        ) : (
          <div className="text-[10px] text-muted-foreground/50 py-1">
            {isFr ? '无问题深度数据' : 'No question depth data'}
          </div>
        )}
      </Section>

      {/* ── Section 4: Retrieval Strategy ── */}
      {hasRetrievalStrategy && (
        <Section
          title={isFr ? '检索策略' : 'Retrieval Strategy'}
          summary={
            <span className="text-[10px] font-medium text-muted-foreground">
              {evaluation.retrievalMode === 'hybrid' ? 'Hybrid' : 'Vector-only'}
            </span>
          }
        >
          <RetrievalDiagnostics evaluation={evaluation} locale={locale} />
        </Section>
      )}

      {/* ── Section 5: Suggestions ── */}
      {hasSuggestions && (
        <Section
          title={isFr ? '改进建议' : 'Suggestions'}
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
                  <span>{isFr ? s.message_zh : s.message_en}</span>
                </div>
              )
            })}
          </div>
        </Section>
      )}
    </div>
  )
}
