/**
 * VectorCheckTab — ChromaDB vector inspection for the selected book.
 *
 * Displays:
 *   - Collection-level total vector count
 *   - Book-scoped vector count (with chunk_count mismatch warning)
 *   - Embedding dimensions
 *   - Random chunk samples with text + metadata + vector preview
 *
 * Data source: Engine API → GET /engine/vectors/stats?book_id={id}
 *
 * Ref: AQ-09 — Vector Check Tab + Engine API
 */

'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Database,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Layers,
  Hash,
  Ruler,
  BookOpen,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import type { BookBase } from '@/features/shared/books'
import { fetchVectorStats } from '../api'
import type { VectorStats } from '../types'

// ============================================================
// Props
// ============================================================
interface VectorCheckTabProps {
  books: BookBase[]
  filter: string
}

// ============================================================
// Component
// ============================================================
export default function VectorCheckTab({ books, filter }: VectorCheckTabProps) {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  const [stats, setStats] = useState<VectorStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Selected book from sidebar
  const selectedBook = useMemo(() => {
    if (!filter.startsWith('book::')) return null
    const bookId = filter.slice(6)
    return books.find((b) => b.book_id === bookId) ?? null
  }, [filter, books])

  // Fetch vector stats
  const loadStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchVectorStats(selectedBook?.book_id)
      setStats(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setStats(null)
    } finally {
      setLoading(false)
    }
  }, [selectedBook?.book_id])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  // Chunk count vs vector count mismatch
  const chunkCount = selectedBook?.chunk_count ?? 0
  const vectorCount = stats?.bookVectors ?? 0
  const hasMismatch = selectedBook && stats && chunkCount > 0 && vectorCount > 0 && chunkCount !== vectorCount

  // ── No book selected → collection overview ──
  if (!selectedBook) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">
              {isFr ? '向量数据库总览' : 'Vector Database Overview'}
            </h3>
          </div>
          <button
            onClick={loadStats}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border
                       text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
          >
            <RefreshCw className={cn('h-3 w-3', loading && 'animate-spin')} />
            {isFr ? '刷新' : 'Refresh'}
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          </div>
        )}

        {stats && !loading && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <StatCard
              icon={<Layers className="h-4 w-4" />}
              label={isFr ? '总向量数' : 'Total Vectors'}
              value={stats.totalVectors.toLocaleString()}
              color="text-blue-400"
            />
            <StatCard
              icon={<Ruler className="h-4 w-4" />}
              label={isFr ? '嵌入维度' : 'Dimensions'}
              value={stats.dimensions > 0 ? String(stats.dimensions) : '—'}
              color="text-emerald-400"
            />
            <StatCard
              icon={<Database className="h-4 w-4" />}
              label={isFr ? 'Collection' : 'Collection'}
              value={stats.collectionName}
              color="text-violet-400"
              mono
            />
          </div>
        )}

        <p className="text-xs text-muted-foreground/60 text-center pt-4">
          {isFr
            ? '在左侧选择一本书查看其向量详情和随机采样'
            : 'Select a book from the sidebar to view its vector details and samples'}
        </p>
      </div>
    )
  }

  // ── Book selected → detailed view ──
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">
            {isFr ? '向量检查' : 'Vector Check'}
          </h3>
          <span className="text-xs text-muted-foreground">
            — {selectedBook.title}
          </span>
        </div>
        <button
          onClick={loadStats}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border
                     text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
        >
          <RefreshCw className={cn('h-3 w-3', loading && 'animate-spin')} />
          {isFr ? '刷新' : 'Refresh'}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        </div>
      )}

      {/* Stats */}
      {stats && !loading && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard
              icon={<Layers className="h-4 w-4" />}
              label={isFr ? '集合总向量' : 'Collection Total'}
              value={stats.totalVectors.toLocaleString()}
              color="text-blue-400"
            />
            <StatCard
              icon={<BookOpen className="h-4 w-4" />}
              label={isFr ? '本书向量' : 'Book Vectors'}
              value={stats.bookVectors.toLocaleString()}
              color={hasMismatch ? 'text-amber-400' : 'text-emerald-400'}
              warning={hasMismatch
                ? (isFr
                  ? `Chunk 数 ${chunkCount} ≠ 向量数 ${vectorCount}`
                  : `Chunks ${chunkCount} ≠ vectors ${vectorCount}`)
                : undefined}
            />
            <StatCard
              icon={<Ruler className="h-4 w-4" />}
              label={isFr ? '嵌入维度' : 'Dimensions'}
              value={stats.dimensions > 0 ? String(stats.dimensions) : '—'}
              color="text-violet-400"
            />
            <StatCard
              icon={<Hash className="h-4 w-4" />}
              label={isFr ? 'Payload Chunks' : 'Payload Chunks'}
              value={chunkCount > 0 ? chunkCount.toLocaleString() : '—'}
              color={hasMismatch ? 'text-amber-400' : 'text-muted-foreground'}
            />
          </div>

          {/* Samples table */}
          {stats.samples.length > 0 && (
            <div className="rounded-lg border border-border overflow-hidden">
              <div className="px-3 py-2 bg-muted/30 border-b border-border">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {isFr ? `随机采样 (${stats.samples.length} 条)` : `Random Samples (${stats.samples.length})`}
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border bg-muted/10">
                      <th className="px-3 py-2 text-left text-muted-foreground font-medium w-8">#</th>
                      <th className="px-3 py-2 text-left text-muted-foreground font-medium min-w-[200px]">
                        {isFr ? '文本' : 'Text'}
                      </th>
                      <th className="px-3 py-2 text-left text-muted-foreground font-medium w-20">
                        {isFr ? '类型' : 'Type'}
                      </th>
                      <th className="px-3 py-2 text-left text-muted-foreground font-medium w-16">
                        {isFr ? '页码' : 'Page'}
                      </th>
                      <th className="px-3 py-2 text-left text-muted-foreground font-medium min-w-[180px]">
                        {isFr ? '向量预览' : 'Vector Preview'}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.samples.map((sample, idx) => (
                      <tr key={sample.chunkId} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                        <td className="px-3 py-2 text-muted-foreground/50 tabular-nums">{idx + 1}</td>
                        <td className="px-3 py-2">
                          <div className="max-w-md">
                            <p className="text-foreground/80 leading-relaxed line-clamp-2">
                              {sample.text || <span className="text-muted-foreground italic">(empty)</span>}
                            </p>
                            <p className="text-[10px] text-muted-foreground/50 font-mono mt-0.5 truncate">
                              {sample.chunkId}
                            </p>
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <span className={cn(
                            'inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium',
                            sample.metadata.content_type === 'text' ? 'bg-blue-500/10 text-blue-400' :
                            sample.metadata.content_type === 'table' ? 'bg-amber-500/10 text-amber-400' :
                            sample.metadata.content_type === 'image' ? 'bg-violet-500/10 text-violet-400' :
                            'bg-muted text-muted-foreground',
                          )}>
                            {sample.metadata.content_type || '—'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-muted-foreground tabular-nums">
                          {sample.metadata.page_idx ?? '—'}
                        </td>
                        <td className="px-3 py-2">
                          {sample.vectorPreview ? (
                            <code className="text-[10px] text-muted-foreground/60 font-mono leading-tight block">
                              [{sample.vectorPreview.map((v) => v.toFixed(4)).join(', ')}…]
                            </code>
                          ) : (
                            <span className="text-muted-foreground/30 text-[10px]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Empty state */}
          {stats.bookVectors === 0 && (
            <div className="rounded-lg border border-border bg-muted/10 p-8 text-center">
              <Database className="h-8 w-8 mx-auto mb-3 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">
                {isFr
                  ? '此书尚未生成向量。请先运行 Pipeline 的 Ingest 阶段。'
                  : 'No vectors found for this book. Run the Pipeline Ingest stage first.'}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ============================================================
// StatCard — reusable metric display
// ============================================================
function StatCard({
  icon,
  label,
  value,
  color,
  mono,
  warning,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: string
  mono?: boolean
  warning?: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3 space-y-1">
      <div className="flex items-center gap-1.5">
        <span className={cn('shrink-0', color)}>{icon}</span>
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium truncate">
          {label}
        </span>
      </div>
      <p className={cn(
        'text-lg font-semibold text-foreground leading-tight truncate',
        mono && 'text-sm font-mono',
      )}>
        {value}
      </p>
      {warning && (
        <div className="flex items-center gap-1 mt-1">
          <AlertTriangle className="h-3 w-3 text-amber-400 shrink-0" />
          <span className="text-[10px] text-amber-400 leading-tight">{warning}</span>
        </div>
      )}
    </div>
  )
}
