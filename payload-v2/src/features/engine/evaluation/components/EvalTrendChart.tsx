/**
 * EvalTrendChart — RAG/LLM/Answer three-line score trend (EV2-T5-03).
 *
 * Pure SVG mini-chart showing score trends across evaluations in a session.
 * Color-coded: RAG=blue, LLM=purple, Answer=green (matches EvalScoreCard).
 * Supports time-range filtering and hover tooltips.
 *
 * Usage: <EvalTrendChart evaluations={evalResults} locale="en" />
 */

'use client'

import { useState, useMemo, useRef } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { EvaluationResult } from '../types'

// ============================================================
// Constants
// ============================================================

const CHART_HEIGHT = 80
const CHART_PADDING = { top: 8, right: 8, bottom: 20, left: 8 }

/** Line color palette — matches EvalScoreCard category colors. */
const LINES = [
  { key: 'ragScore' as const,    label: 'RAG',    labelFr: '检索',  color: '#3b82f6', dotColor: 'bg-blue-500' },
  { key: 'llmScore' as const,    label: 'LLM',    labelFr: '模型',  color: '#a855f7', dotColor: 'bg-purple-500' },
  { key: 'answerScore' as const, label: 'Answer',  labelFr: '回答', color: '#22c55e', dotColor: 'bg-emerald-500' },
] as const

type RangeFilter = 10 | 50 | 100

// ============================================================
// Helpers
// ============================================================

interface TrendInfo {
  direction: 'up' | 'down' | 'flat'
  delta: number
}

function computeTrend(values: (number | null)[]): TrendInfo {
  const valid = values.filter((v): v is number => v != null)
  if (valid.length < 2) return { direction: 'flat', delta: 0 }

  const half = Math.floor(valid.length / 2)
  const firstHalf = valid.slice(0, half)
  const secondHalf = valid.slice(half)

  const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length
  const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length
  const delta = avgSecond - avgFirst

  if (Math.abs(delta) < 0.02) return { direction: 'flat', delta }
  return { direction: delta > 0 ? 'up' : 'down', delta }
}

function buildSvgPath(
  points: { x: number; y: number }[],
): string {
  if (points.length === 0) return ''
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
}

// ============================================================
// Props
// ============================================================
interface EvalTrendChartProps {
  /** Evaluation results to visualize (sorted chronologically). */
  evaluations: EvaluationResult[]
  /** UI locale. */
  locale?: 'en' | 'zh'
}

// ============================================================
// Component
// ============================================================
export default function EvalTrendChart({ evaluations, locale = 'en' }: EvalTrendChartProps) {
  const isZh = locale === 'zh'
  const svgRef = useRef<SVGSVGElement>(null)
  const [range, setRange] = useState<RangeFilter>(50)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  // Filter and sort evaluations
  const data = useMemo(() => {
    const sorted = [...evaluations]
      .filter(e => e.ragScore != null || e.llmScore != null || e.answerScore != null)
      .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
    return sorted.slice(-range)
  }, [evaluations, range])

  // Compute trends for each line
  const trends = useMemo(() => {
    return LINES.map(line => ({
      ...line,
      trend: computeTrend(data.map(d => d[line.key])),
    }))
  }, [data])

  // SVG dimensions
  const containerWidth = 320  // Will be overridden by parent via CSS
  const plotW = containerWidth - CHART_PADDING.left - CHART_PADDING.right
  const plotH = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom

  // Calculate points for each line
  const linePoints = useMemo(() => {
    if (data.length === 0) return {}

    const xStep = data.length > 1 ? plotW / (data.length - 1) : plotW / 2
    const result: Record<string, { x: number; y: number; value: number | null }[]> = {}

    for (const line of LINES) {
      result[line.key] = data.map((d, i) => {
        const val = d[line.key]
        return {
          x: CHART_PADDING.left + i * xStep,
          y: val != null
            ? CHART_PADDING.top + plotH * (1 - val)
            : CHART_PADDING.top + plotH,
          value: val,
        }
      })
    }

    return result
  }, [data, plotW, plotH])

  if (data.length < 2) {
    return (
      <div className="rounded-lg border border-border/30 bg-card/30 px-3 py-2 text-center">
        <span className="text-[9px] text-muted-foreground">
          {isZh ? '需要至少 2 条评估数据才能显示趋势' : 'Need at least 2 evaluations to show trends'}
        </span>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border/40 bg-gradient-to-br from-card/80 to-card/50 p-3 space-y-2">
      {/* Header */}
      <div className="flex items-center gap-2">
        <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
        <span className="text-[10px] font-semibold text-foreground flex-1">
          {isZh ? '评分趋势' : 'Score Trends'}
        </span>

        {/* Range selector */}
        <div className="flex items-center gap-0.5 rounded-md border border-border/30 p-0.5">
          {([10, 50, 100] as RangeFilter[]).map(r => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              className={cn(
                'px-1.5 py-0.5 rounded text-[8px] font-medium transition-colors',
                range === r
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Chart */}
      <div className="relative w-full" style={{ height: CHART_HEIGHT }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${containerWidth} ${CHART_HEIGHT}`}
          className="w-full h-full"
          preserveAspectRatio="none"
          onMouseLeave={() => setHoveredIdx(null)}
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(v => {
            const y = CHART_PADDING.top + plotH * (1 - v)
            return (
              <line
                key={v}
                x1={CHART_PADDING.left}
                y1={y}
                x2={containerWidth - CHART_PADDING.right}
                y2={y}
                stroke="currentColor"
                strokeOpacity={0.06}
                strokeDasharray="2 2"
              />
            )
          })}

          {/* Lines */}
          {LINES.map(line => {
            const pts = linePoints[line.key]
            if (!pts) return null
            const validPts = pts.filter(p => p.value != null)
            if (validPts.length < 2) return null

            return (
              <g key={line.key}>
                {/* Gradient fill below line */}
                <defs>
                  <linearGradient id={`grad-${line.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={line.color} stopOpacity="0.15" />
                    <stop offset="100%" stopColor={line.color} stopOpacity="0" />
                  </linearGradient>
                </defs>

                {/* Area fill */}
                <path
                  d={`${buildSvgPath(validPts)} L ${validPts[validPts.length - 1].x} ${CHART_PADDING.top + plotH} L ${validPts[0].x} ${CHART_PADDING.top + plotH} Z`}
                  fill={`url(#grad-${line.key})`}
                />

                {/* Line */}
                <path
                  d={buildSvgPath(validPts)}
                  fill="none"
                  stroke={line.color}
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Dots */}
                {validPts.map((p, i) => (
                  <circle
                    key={i}
                    cx={p.x}
                    cy={p.y}
                    r={hoveredIdx === pts.indexOf(p) ? 3 : 1.5}
                    fill={line.color}
                    fillOpacity={hoveredIdx === pts.indexOf(p) ? 1 : 0.7}
                    className="transition-all duration-150"
                  />
                ))}
              </g>
            )
          })}

          {/* Invisible hover targets */}
          {data.map((_, i) => {
            const xStep = data.length > 1 ? plotW / (data.length - 1) : plotW / 2
            const x = CHART_PADDING.left + i * xStep
            return (
              <rect
                key={i}
                x={x - (xStep / 2)}
                y={CHART_PADDING.top}
                width={xStep}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHoveredIdx(i)}
              />
            )
          })}

          {/* Hover vertical line */}
          {hoveredIdx != null && (
            <line
              x1={CHART_PADDING.left + hoveredIdx * (data.length > 1 ? plotW / (data.length - 1) : plotW / 2)}
              y1={CHART_PADDING.top}
              x2={CHART_PADDING.left + hoveredIdx * (data.length > 1 ? plotW / (data.length - 1) : plotW / 2)}
              y2={CHART_PADDING.top + plotH}
              stroke="currentColor"
              strokeOpacity={0.15}
              strokeDasharray="2 2"
            />
          )}

          {/* Y-axis labels */}
          {[0, 0.5, 1].map(v => (
            <text
              key={v}
              x={CHART_PADDING.left - 2}
              y={CHART_PADDING.top + plotH * (1 - v) + 3}
              textAnchor="end"
              className="text-[7px] fill-muted-foreground/40"
            >
              {(v * 100).toFixed(0)}
            </text>
          ))}
        </svg>

        {/* Hover tooltip */}
        {hoveredIdx != null && data[hoveredIdx] && (
          <div
            className="absolute z-10 pointer-events-none rounded-lg border border-border bg-popover/95 px-2.5 py-1.5 shadow-lg backdrop-blur-sm"
            style={{
              left: `${((CHART_PADDING.left + hoveredIdx * (data.length > 1 ? plotW / (data.length - 1) : plotW / 2)) / containerWidth) * 100}%`,
              top: -8,
              transform: 'translateX(-50%)',
            }}
          >
            <div className="text-[8px] text-muted-foreground mb-1">
              {new Date(data[hoveredIdx].createdAt).toLocaleDateString()}
            </div>
            {LINES.map(line => {
              const val = data[hoveredIdx][line.key]
              return (
                <div key={line.key} className="flex items-center gap-1.5 text-[9px]">
                  <span className={cn('inline-block w-1.5 h-1.5 rounded-full', line.dotColor)} />
                  <span className="text-muted-foreground w-10">{isZh ? line.labelFr : line.label}</span>
                  <span className="font-bold tabular-nums text-foreground">
                    {val != null ? (val * 100).toFixed(0) + '%' : '—'}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Legend + trend indicators */}
      <div className="flex items-center gap-3">
        {trends.map(({ key, label, labelFr, dotColor, trend }) => {
          const TIcon = trend.direction === 'up' ? TrendingUp
            : trend.direction === 'down' ? TrendingDown
            : Minus
          const trendCls = trend.direction === 'up' ? 'text-emerald-400'
            : trend.direction === 'down' ? 'text-red-400'
            : 'text-muted-foreground'

          return (
            <div key={key} className="flex items-center gap-1">
              <span className={cn('inline-block w-2 h-2 rounded-full', dotColor)} />
              <span className="text-[9px] text-muted-foreground">{isZh ? labelFr : label}</span>
              <TIcon className={cn('h-3 w-3', trendCls)} />
              <span className={cn('text-[8px] tabular-nums', trendCls)}>
                {trend.delta > 0 ? '+' : ''}{(trend.delta * 100).toFixed(0)}%
              </span>
            </div>
          )
        })}
        <span className="ml-auto text-[8px] text-muted-foreground/50">
          n={data.length}
        </span>
      </div>
    </div>
  )
}
