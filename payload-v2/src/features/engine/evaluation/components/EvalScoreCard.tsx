/**
 * EvalScoreCard — Five-category evaluation score card (EV2-T5-01 / EI-T5-01).
 *
 * Displays RAG / LLM / Answer / Question / IR scores in a compact,
 * color-coded card layout with expandable detail dimensions.
 * IR card only renders when Golden Dataset has a matched record.
 *
 * Usage: <EvalScoreCard evaluation={evalResult} locale="en" />
 */

'use client'

import { useState } from 'react'
import {
  Search, Bot, Sparkles, FileText, BarChart2,
  ChevronDown,
  CheckCircle2, XCircle, Clock,
  Shuffle, Grid3X3,
  CircleCheck, CircleX,
  Info,
  Lightbulb, Settings2,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { EvaluationResult, EvalStatus, EvalSuggestion, SuggestionSeverity } from '../types'

/** Map suggestion severity → visual styles. */
const SEVERITY_STYLES: Record<SuggestionSeverity, { dot: string; text: string }> = {
  high: { dot: 'bg-red-400', text: 'text-red-300' },
  medium: { dot: 'bg-amber-400', text: 'text-amber-300' },
  low: { dot: 'bg-emerald-400', text: 'text-emerald-300' },
  info: { dot: 'bg-blue-400', text: 'text-blue-300' },
}

// ============================================================
// Constants
// ============================================================

/** Core four evaluation categories with display metadata. */
const CORE_CATEGORIES = [
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
      { key: 'correctness',     label: 'Correctness',      labelFr: '正确性' },
      { key: 'completeness',    label: 'Completeness',     labelFr: '完整度' },
      { key: 'clarity',         label: 'Clarity',          labelFr: '清晰度' },
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

/** IR retrieval metrics card metadata (EI-T5-01). */
const IR_CARD = {
  key: 'ir' as const,
  label: 'IR',
  labelFr: '检索指标',
  Icon: BarChart2,
  gradient: 'from-cyan-500/20 to-teal-500/10',
  border: 'border-cyan-500/30',
  accent: 'text-cyan-400',
  accentBg: 'bg-cyan-500/10',
  barColor: 'bg-cyan-500',
  dimensions: [
    { key: 'hitRate',      label: 'Hit Rate',    labelFr: '命中率' },
    { key: 'mrr',          label: 'MRR',         labelFr: 'MRR' },
    { key: 'precisionAtK', label: 'Precision@K', labelFr: '精确率@K' },
    { key: 'recallAtK',    label: 'Recall@K',    labelFr: '召回率@K' },
    { key: 'ndcg',         label: 'NDCG',        labelFr: 'NDCG' },
  ],
}

/** Tooltip text for metric explanations (EI-T5-03). */
const TOOLTIP_MAP: Record<string, { en: string; fr: string }> = {
  contextRelevancy:  { en: 'Quality of retrieved context for the query', fr: '检索到的内容与问题是否相关' },
  relevancy:         { en: 'Are the retrieved sources relevant to the query?', fr: '来源是否与问题相关' },
  faithfulness:      { en: 'Is the answer grounded in context, no hallucination?', fr: '回答是否基于给定上下文，无幻觉' },
  answerRelevancy:   { en: 'How relevant is the answer to the question?', fr: '答案与问题的相关程度' },
  correctness:       { en: 'Factual overlap with the reference answer (F1)', fr: '回答与标准答案的事实重合度 (F1)' },
  completeness:      { en: 'Does the answer cover all question aspects?', fr: '回答是否覆盖问题所有方面' },
  clarity:           { en: 'Is the answer clear, well-structured?', fr: '回答是否清晰、结构良好' },
  hitRate:           { en: 'Did retrieval include the correct chunk? (1=hit, 0=miss)', fr: '检索结果中是否包含正确答案 (1=命中, 0=未命中)' },
  mrr:               { en: 'Reciprocal rank of the first correct result (1=top, 0.5=2nd)', fr: '第一个正确结果的排名倒数 (1=排第一, 0.5=排第二)' },
  precisionAtK:      { en: 'Fraction of top-K results that are correct', fr: 'Top-K 结果中正确的比例' },
  recallAtK:         { en: 'Fraction of correct results retrieved in top-K', fr: '正确答案被检索到的比例' },
  ndcg:              { en: 'Are correct results ranked higher? (considers ranking quality)', fr: '正确结果是否排在前面 (考虑排序质量)' },
  guidelines:        { en: 'Does the answer follow all predefined quality rules?', fr: '回答是否符合预设质量规则' },
}

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
// Sub-components
// ============================================================

/** Info icon with tooltip (EI-T5-03). */
function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <Info className="h-2.5 w-2.5 text-muted-foreground/50 cursor-help" />
      <span className="pointer-events-none absolute left-4 bottom-0 z-50 w-44 rounded-md bg-popover/95 border border-border px-2 py-1 text-[8px] leading-snug text-popover-foreground shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-150">
        {text}
      </span>
    </span>
  )
}

/** Single dimension progress bar row. */
function DimBar({
  label, labelFr, value, barColor, isFr, dimKey,
}: {
  label: string
  labelFr: string
  value: number | null | undefined
  barColor: string
  isFr: boolean
  dimKey?: string
}) {
  const tip = dimKey ? TOOLTIP_MAP[dimKey] : null
  return (
    <div className="flex items-center gap-1">
      <span className="text-[8px] text-muted-foreground w-24 shrink-0 truncate inline-flex items-center gap-0.5">
        {isFr ? labelFr : label}
        {tip && <InfoTooltip text={isFr ? tip.fr : tip.en} />}
      </span>
      <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${(value ?? 0) * 100}%` }}
        />
      </div>
      <span className={cn('text-[9px] font-bold tabular-nums w-7 text-right', GRADE_CLS[getGrade(value)])}>
        {value != null ? value.toFixed(2) : '—'}
      </span>
    </div>
  )
}

/** Guidelines Pass/Fail row with expandable feedback (EI-T5-02). */
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
  const tip = TOOLTIP_MAP.guidelines
  const hasFeedback = !!feedback?.trim()

  return (
    <div className="pt-0.5 space-y-0.5">
      <div className="flex items-center gap-1">
        <span className="text-[8px] text-muted-foreground w-24 shrink-0 inline-flex items-center gap-0.5">
          {isFr ? '质量规则' : 'Guidelines'}
          {tip && <InfoTooltip text={isFr ? tip.fr : tip.en} />}
        </span>
        <button
          type="button"
          onClick={() => hasFeedback && setShowFeedback(v => !v)}
          className={cn(
            'inline-flex items-center gap-0.5 text-[9px] font-semibold',
            hasFeedback && 'cursor-pointer hover:opacity-80',
            guidelinesPass ? 'text-emerald-400' : 'text-red-400',
          )}
        >
          {guidelinesPass
            ? <><CircleCheck className="h-3 w-3" />{isFr ? '通过' : 'Pass'}</>
            : <><CircleX className="h-3 w-3" />{isFr ? '未通过' : 'Fail'}</>
          }
          {hasFeedback && (
            <ChevronDown className={cn(
              'h-2.5 w-2.5 transition-transform duration-150',
              showFeedback && 'rotate-180',
            )} />
          )}
        </button>
      </div>
      {showFeedback && feedback && (
        <div className={cn(
          'rounded-md border px-2 py-1 text-[8px] leading-snug animate-in slide-in-from-top-1 fade-in duration-150',
          guidelinesPass
            ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-300/80'
            : 'border-red-500/20 bg-red-500/5 text-red-300/80',
        )}>
          {feedback}
        </div>
      )}
    </div>
  )
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

  // Determine if IR metrics are available
  const hasIR = evaluation.irScore != null || evaluation.hitRate != null

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

      {/* ── Summary row: category score chips ── */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {CORE_CATEGORIES.map(cat => {
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

        {/* IR chip — only shown when data available */}
        {hasIR && (
          <div className={cn(
            'inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5',
            IR_CARD.border, IR_CARD.accentBg,
          )}>
            <IR_CARD.Icon className={cn('h-3 w-3', IR_CARD.accent)} />
            <span className="text-[9px] font-medium text-muted-foreground">
              {isFr ? IR_CARD.labelFr : IR_CARD.label}
            </span>
            <span className={cn('text-[10px] font-bold tabular-nums', GRADE_CLS[getGrade(evaluation.irScore)])}>
              {evaluation.irScore != null ? (evaluation.irScore * 100).toFixed(0) + '%' : '—'}
            </span>
          </div>
        )}
      </div>

      {/* ── Expanded detail ── */}
      {expanded && (
        <div className="grid grid-cols-2 gap-2 animate-in slide-in-from-top-1 fade-in duration-200">
          {CORE_CATEGORIES.map(cat => {
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
                  <div className="space-y-1">
                    <DimBar
                      label="Depth" labelFr="认知深度"
                      value={normScore} barColor={cat.barColor} isFr={isFr}
                    />
                  </div>
                </div>
              )
            }

            // Answer category — includes guidelinesPass + correctness
            if (cat.key === 'answer') {
              const aggScore = evaluation[cat.scoreKey]
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
                        <DimBar
                          key={dim.key}
                          label={dim.label} labelFr={dim.labelFr}
                          value={val} barColor={cat.barColor} isFr={isFr}
                          dimKey={dim.key}
                        />
                      )
                    })}
                    {/* Guidelines Pass/Fail badge + expandable feedback (EI-T5-02) */}
                    {evaluation.guidelinesPass != null && (
                      <GuidelinesRow
                        pass={evaluation.guidelinesPass}
                        feedback={evaluation.guidelinesFeedback}
                        isFr={isFr}
                      />
                    )}
                  </div>
                </div>
              )
            }

            // RAG / LLM — standard score bars
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
                      <DimBar
                        key={dim.key}
                        label={dim.label} labelFr={dim.labelFr}
                        value={val} barColor={cat.barColor} isFr={isFr}
                        dimKey={dim.key}
                      />
                    )
                  })}
                </div>
              </div>
            )
          })}

          {/* ── 5th card: IR Retrieval Metrics (EI-T5-01) ── */}
          {hasIR ? (
            <div className={cn(
              'col-span-2 rounded-lg border p-2 space-y-1.5',
              IR_CARD.border, 'bg-gradient-to-br', IR_CARD.gradient,
            )}>
              <div className="flex items-center gap-1">
                <IR_CARD.Icon className={cn('h-3 w-3', IR_CARD.accent)} />
                <span className="text-[9px] font-semibold text-foreground flex-1">
                  {isFr ? IR_CARD.labelFr : IR_CARD.label}
                  <span className="ml-1 text-[8px] font-normal text-muted-foreground">
                    {isFr ? '(需 Golden Dataset)' : '(requires Golden Dataset)'}
                  </span>
                </span>
                {evaluation.irScore != null && (
                  <span className={cn('text-[10px] font-bold tabular-nums', GRADE_CLS[getGrade(evaluation.irScore)])}>
                    {evaluation.irScore.toFixed(2)}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                {IR_CARD.dimensions.map(dim => {
                  const val = (evaluation as any)[dim.key] as number | null
                  return (
                    <DimBar
                      key={dim.key}
                      label={dim.label} labelFr={dim.labelFr}
                      value={val} barColor={IR_CARD.barColor} isFr={isFr}
                      dimKey={dim.key}
                    />
                  )
                })}
              </div>
            </div>
          ) : (
            <div className={cn(
              'col-span-2 rounded-lg border p-2',
              IR_CARD.border, IR_CARD.accentBg,
            )}>
              <div className="flex items-center gap-1.5 text-[9px] text-muted-foreground">
                <IR_CARD.Icon className={cn('h-3 w-3 shrink-0', IR_CARD.accent)} />
                <span>
                  {isFr
                    ? 'IR 指标不可用 — 需先生成 Golden Dataset 并标记 verified'
                    : 'IR metrics unavailable — generate & verify Golden Dataset records first'}
                </span>
              </div>
            </div>
          )}

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

          {/* ── 💡 Improvement suggestions (EUX-T3-03) ── */}
          {evaluation.suggestions && evaluation.suggestions.length > 0 && (
            <div className="col-span-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-2">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Lightbulb className="h-3 w-3 text-amber-400" />
                <span className="text-[10px] font-medium text-amber-300">
                  {isFr ? `改进建议 (${evaluation.suggestions.length})` : `Suggestions (${evaluation.suggestions.length})`}
                </span>
              </div>
              <div className="space-y-1">
                {evaluation.suggestions.map((s: EvalSuggestion, i: number) => {
                  const style = SEVERITY_STYLES[s.severity] || SEVERITY_STYLES.medium
                  return (
                    <div key={i} className="flex items-start gap-1.5 text-[9px] text-muted-foreground">
                      <span className={cn('mt-1 inline-block w-1.5 h-1.5 rounded-full shrink-0', style.dot)} />
                      <span className={style.text}>
                        {isFr ? s.message_zh : s.message_en}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* ── ⚙ Evaluation metadata (EUX-T2-03) ── */}
          {(evaluation.judgeModel || evaluation.answerModel || evaluation.llmCalls) && (
            <div className="col-span-2 flex flex-wrap items-center gap-x-3 gap-y-0.5 px-1 text-[8px] text-muted-foreground/60">
              <Settings2 className="h-2.5 w-2.5 shrink-0" />
              {evaluation.judgeModel && (
                <span>
                  {isFr ? '评审' : 'Judge'}: <span className="text-foreground/50">{evaluation.judgeModel}</span>
                </span>
              )}
              {evaluation.answerModel && (
                <span>
                  {isFr ? '回答' : 'Answer'}: <span className="text-foreground/50">{evaluation.answerModel}</span>
                </span>
              )}
              {evaluation.llmCalls != null && evaluation.llmCalls > 0 && (
                <span className="ml-auto tabular-nums">
                  {evaluation.llmCalls} {isFr ? '次调用' : 'calls'}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
