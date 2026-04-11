'use client'

import {
  CheckCircle2,
  Clock,
  Loader2,
  AlertCircle,
  Check,
} from 'lucide-react'
import type { BookStatus, StageStatus, PipelineStageKey } from './types'
import { PIPELINE_STAGE_CONFIGS } from './types'
import type { PipelineStages } from './types'
import { cn } from '@/features/shared/utils'

/**
 * StatusBadge — 总状态标签 (pending/processing/indexed/error)
 */

const statusConfig: Record<BookStatus, {
  label: string
  labelZh: string
  icon: typeof Clock
  bgClass: string
  textClass: string
  iconClass: string
}> = {
  pending: {
    label: 'Pending',
    labelZh: '待处理',
    icon: Clock,
    bgClass: 'bg-amber-500/10',
    textClass: 'text-amber-600 dark:text-amber-400',
    iconClass: 'text-amber-500',
  },
  processing: {
    label: 'Processing',
    labelZh: '处理中',
    icon: Loader2,
    bgClass: 'bg-blue-500/10',
    textClass: 'text-blue-600 dark:text-blue-400',
    iconClass: 'text-blue-500 animate-spin',
  },
  indexed: {
    label: 'Ready',
    labelZh: '已就绪',
    icon: CheckCircle2,
    bgClass: 'bg-emerald-500/10',
    textClass: 'text-emerald-600 dark:text-emerald-400',
    iconClass: 'text-emerald-500',
  },
  error: {
    label: 'Error',
    labelZh: '失败',
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
 * StageDot — 单个阶段的状态小圆点
 * 用于表格中每个阶段字段
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

/**
 * PipelineProgress — 5 阶段横向进度 (用于卡片视图)
 * 从独立字段读取每个阶段状态
 */
export function PipelineProgress({ pipeline }: { pipeline: PipelineStages }) {
  return (
    <div className="flex items-center gap-1">
      {PIPELINE_STAGE_CONFIGS.map((cfg, idx) => (
        <div key={cfg.key} className="flex items-center">
          {idx > 0 && (
            <div
              className={cn(
                'w-3 h-px mx-0.5',
                pipeline[cfg.key] === 'done' ? 'bg-emerald-500/50' :
                pipeline[cfg.key] === 'error' ? 'bg-red-500/50' :
                'bg-border'
              )}
            />
          )}
          <StageDot value={pipeline[cfg.key]} label={cfg.label} />
        </div>
      ))}
    </div>
  )
}
