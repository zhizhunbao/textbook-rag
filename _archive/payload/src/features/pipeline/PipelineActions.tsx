'use client'

/**
 * PipelineActions — 书本流水线操作按钮组
 *
 * 在 LibraryPage toolbar 中使用，提供：
 *   • Sync Engine → Payload (全量同步)
 *   • Re-ingest selected book (重新处理单本书)
 *   • Rebuild vectors (重建向量索引)
 *
 * Pipeline action buttons for the Library toolbar.
 * Provides: Sync, Re-ingest, Rebuild vectors.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Play,
  RefreshCw,
  Database,
  Loader2,
  ChevronDown,
  CheckCircle2,
  XCircle,
  Zap,
} from 'lucide-react'
import { triggerEngineSync, triggerPipeline, fetchTask } from './api'
import type { PipelineTask, TaskType, SyncResult } from './types'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'

interface PipelineActionsProps {
  /** Currently selected book IDs (from LibraryPage) */
  selectedBookIds?: Set<number>
  /** Callback after a sync/pipeline action completes */
  onComplete?: () => void
  /** Compact mode for toolbar */
  compact?: boolean
}

type ActionState = 'idle' | 'running' | 'success' | 'error'

interface ActionFeedback {
  state: ActionState
  message: string
}

export default function PipelineActions({
  selectedBookIds,
  onComplete,
  compact = false,
}: PipelineActionsProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  const [isOpen, setIsOpen] = useState(false)
  const [feedback, setFeedback] = useState<ActionFeedback>({ state: 'idle', message: '' })
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Poll task progress
  useEffect(() => {
    if (!activeTaskId) return
    const interval = setInterval(async () => {
      const task = await fetchTask(activeTaskId)
      if (!task) return

      if (task.status === 'done') {
        setFeedback({
          state: 'success',
          message: isZh ? `✅ 完成 (${task.progress}%)` : `✅ Done (${task.progress}%)`,
        })
        setActiveTaskId(null)
        clearInterval(interval)
        onComplete?.()
        // Clear feedback after 3s
        setTimeout(() => setFeedback({ state: 'idle', message: '' }), 3000)
      } else if (task.status === 'error') {
        setFeedback({
          state: 'error',
          message: isZh ? `❌ 失败: ${task.error}` : `❌ Error: ${task.error}`,
        })
        setActiveTaskId(null)
        clearInterval(interval)
        setTimeout(() => setFeedback({ state: 'idle', message: '' }), 5000)
      } else {
        setFeedback({
          state: 'running',
          message: isZh
            ? `⏳ ${task.log || '处理中...'} (${task.progress}%)`
            : `⏳ ${task.log || 'Processing...'} (${task.progress}%)`,
        })
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [activeTaskId, isZh, onComplete])

  // ── Action handlers ──────────────────────────────────────────────────────

  const handleSync = useCallback(async () => {
    setIsOpen(false)
    setFeedback({ state: 'running', message: isZh ? '同步中...' : 'Syncing...' })
    try {
      const result: SyncResult = await triggerEngineSync()
      setFeedback({
        state: 'success',
        message: isZh
          ? `✅ 同步完成: ${result.created} 新增, ${result.updated} 更新`
          : `✅ Synced: ${result.created} created, ${result.updated} updated`,
      })
      onComplete?.()
      setTimeout(() => setFeedback({ state: 'idle', message: '' }), 4000)
    } catch (err) {
      setFeedback({
        state: 'error',
        message: isZh ? `❌ 同步失败: ${err}` : `❌ Sync failed: ${err}`,
      })
      setTimeout(() => setFeedback({ state: 'idle', message: '' }), 5000)
    }
  }, [isZh, onComplete])

  const handleIngest = useCallback(async (taskType: TaskType) => {
    if (!selectedBookIds || selectedBookIds.size === 0) return
    setIsOpen(false)

    const bookId = [...selectedBookIds][0] // Process first selected
    setFeedback({
      state: 'running',
      message: isZh ? `正在启动 ${taskType}...` : `Starting ${taskType}...`,
    })

    try {
      const task: PipelineTask = await triggerPipeline({ bookId, taskType })
      setActiveTaskId(task.id)
      setFeedback({
        state: 'running',
        message: isZh ? `任务已创建 (#${task.id})` : `Task created (#${task.id})`,
      })
    } catch (err) {
      setFeedback({
        state: 'error',
        message: isZh ? `❌ 启动失败: ${err}` : `❌ Trigger failed: ${err}`,
      })
      setTimeout(() => setFeedback({ state: 'idle', message: '' }), 5000)
    }
  }, [selectedBookIds, isZh])

  // ── Render ────────────────────────────────────────────────────────────────

  const hasSelection = selectedBookIds && selectedBookIds.size > 0
  const isRunning = feedback.state === 'running'

  const actions = [
    {
      key: 'sync',
      icon: Database,
      label: isZh ? '同步 Engine → CMS' : 'Sync Engine → CMS',
      desc: isZh ? '将 SQLite 数据同步到 Payload' : 'Sync SQLite data to Payload',
      disabled: isRunning,
      onClick: handleSync,
    },
    {
      key: 'divider-1',
      divider: true,
    },
    {
      key: 'ingest',
      icon: Play,
      label: isZh ? '重新处理' : 'Re-ingest',
      desc: isZh ? '重新解析 MinerU 输出并建索引' : 'Re-parse MinerU output and rebuild index',
      disabled: !hasSelection || isRunning,
      onClick: () => handleIngest('ingest'),
    },
    {
      key: 'reindex',
      icon: RefreshCw,
      label: isZh ? '重建索引' : 'Reindex',
      desc: isZh ? '重新构建 FTS + 向量索引' : 'Rebuild FTS + vector index',
      disabled: !hasSelection || isRunning,
      onClick: () => handleIngest('reindex'),
    },
    {
      key: 'full',
      icon: Zap,
      label: isZh ? '完整 Pipeline' : 'Full Pipeline',
      desc: isZh ? '执行完整处理流程' : 'Run all stages end-to-end',
      disabled: !hasSelection || isRunning,
      onClick: () => handleIngest('full'),
    },
  ]

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isRunning}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
          isRunning
            ? 'bg-primary/10 text-primary cursor-wait'
            : 'bg-primary/10 text-primary hover:bg-primary/20',
          compact && 'px-2 py-1',
        )}
      >
        {isRunning ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Zap className="h-3.5 w-3.5" />
        )}
        {!compact && (isZh ? 'Pipeline' : 'Pipeline')}
        <ChevronDown className={cn('h-3 w-3 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {/* Feedback toast */}
      {feedback.state !== 'idle' && (
        <div
          className={cn(
            'absolute top-full right-0 mt-1 z-50 px-3 py-2 rounded-lg text-xs whitespace-nowrap',
            'shadow-lg border animate-in fade-in slide-in-from-top-1 duration-150',
            feedback.state === 'running' && 'bg-blue-500/10 border-blue-500/20 text-blue-400',
            feedback.state === 'success' && 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
            feedback.state === 'error' && 'bg-red-500/10 border-red-500/20 text-red-400',
          )}
        >
          <div className="flex items-center gap-2">
            {feedback.state === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
            {feedback.state === 'success' && <CheckCircle2 className="h-3 w-3" />}
            {feedback.state === 'error' && <XCircle className="h-3 w-3" />}
            <span className="max-w-[300px] truncate">{feedback.message}</span>
          </div>
        </div>
      )}

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute top-full right-0 mt-1 z-50 w-64 rounded-xl border border-border bg-popover shadow-xl animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="p-1">
            {actions.map((action) =>
              'divider' in action ? (
                <div key={action.key} className="my-1 border-t border-border" />
              ) : (
                <button
                  key={action.key}
                  onClick={action.onClick}
                  disabled={action.disabled}
                  className={cn(
                    'flex items-start gap-3 w-full px-3 py-2.5 rounded-lg text-left transition-colors',
                    action.disabled
                      ? 'opacity-40 cursor-not-allowed'
                      : 'hover:bg-secondary/80'
                  )}
                >
                  {'icon' in action && action.icon && (
                    <action.icon className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
                  )}
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-foreground">
                      {action.label}
                    </div>
                    {'desc' in action && (
                      <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
                        {action.desc}
                      </div>
                    )}
                  </div>
                </button>
              )
            )}
          </div>

          {/* Selected books info */}
          {hasSelection && (
            <div className="px-3 py-2 border-t border-border text-[10px] text-muted-foreground">
              {isZh
                ? `已选 ${selectedBookIds!.size} 本书 — 操作将应用于第一本`
                : `${selectedBookIds!.size} book(s) selected — action applies to first`}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
