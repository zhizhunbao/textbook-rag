'use client'

import {
  CheckCircle2,
  Clock,
  Loader2,
  AlertCircle,
  Check,
} from 'lucide-react'
import type { BookStatus, StageStatus, PipelineStageKey } from '../types'
import { PIPELINE_STAGE_CONFIGS } from '../types'
import type { PipelineInfo } from '@/features/shared/books'
import { cn } from '@/features/shared/utils'

/**
 * StatusBadge — 总状态标签 (pending/processing/indexed/error)
 */

const statusConfig: Record<BookStatus, {
  label: string
  labelFr: string
  icon: typeof Clock
  bgClass: string
  textClass: string
  iconClass: string
}> = {
  pending: {
    label: 'Pending',
    labelFr: 'En attente',
    icon: Clock,
    bgClass: 'bg-amber-500/10',
    textClass: 'text-amber-600 dark:text-amber-400',
    iconClass: 'text-amber-500',
  },
  processing: {
    label: 'Processing',
    labelFr: 'En cours',
    icon: Loader2,
    bgClass: 'bg-blue-500/10',
    textClass: 'text-blue-600 dark:text-blue-400',
    iconClass: 'text-blue-500 animate-spin',
  },
  indexed: {
    label: 'Ready',
    labelFr: 'Prêt',
    icon: CheckCircle2,
    bgClass: 'bg-emerald-500/10',
    textClass: 'text-emerald-600 dark:text-emerald-400',
    iconClass: 'text-emerald-500',
  },
  error: {
    label: 'Error',
    labelFr: 'Erreur',
    icon: AlertCircle,
    bgClass: 'bg-red-500/10',
    textClass: 'text-red-600 dark:text-red-400',
    iconClass: 'text-red-500',
  },
}

export default function StatusBadge({ status }: { status: BookStatus }) {
  const config = statusConfig[status] ?? statusConfig.pending
  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium',
        config.bgClass,
        config.textClass,
      )}
    >
      <Icon className={cn('h-3 w-3', config.iconClass)} />
      {config.label}
    </span>
  )
}

/**
 * StageDot — single-stage status dot (for table cells)
 * Shows a colored dot with hover tooltip
 */
export function StageDot({ value, label }: { value: StageStatus; label?: string }) {
  return (
    <div className="relative group/dot flex justify-center">
      {value === 'done' ? (
        <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
          <Check className="h-3 w-3 text-emerald-500" />
        </div>
      ) : value === 'error' ? (
        <div className="w-5 h-5 rounded-full bg-red-500/20 flex items-center justify-center">
          <AlertCircle className="h-3 w-3 text-red-500" />
        </div>
      ) : (
        <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
        </div>
      )}
      {label && (
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap
                       text-[10px] bg-foreground text-background px-1.5 py-0.5 rounded
                       opacity-0 group-hover/dot:opacity-100 transition-opacity pointer-events-none z-10">
          {label}
        </span>
      )}
    </div>
  )
}

/* ── Stage pill style map ────────────────────────────────────────────── */
const stageStyle: Record<StageStatus, {
  bg: string; text: string; icon: typeof Check
}> = {
  done:    { bg: 'bg-emerald-500/10', text: 'text-emerald-500', icon: Check },
  error:   { bg: 'bg-red-500/10',     text: 'text-red-500',     icon: AlertCircle },
  pending: { bg: 'bg-muted',          text: 'text-muted-foreground/50', icon: Clock },
}

/**
 * PipelineProgress — compact inline stage pills
 *
 * Renders: [✓ Chunked] [✓ TOC] [✓ Vector]
 * Each pill is self-descriptive — no hover required.
 */
export function PipelineProgress({ pipeline }: { pipeline: PipelineInfo }) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {PIPELINE_STAGE_CONFIGS.map((cfg) => {
        const status = pipeline[cfg.key] ?? 'pending'
        const style = stageStyle[status] ?? stageStyle.pending
        const Icon = style.icon

        return (
          <span
            key={cfg.key}
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
              style.bg, style.text,
            )}
          >
            <Icon className="h-2.5 w-2.5" />
            {cfg.label}
          </span>
        )
      })}
    </div>
  )
}
