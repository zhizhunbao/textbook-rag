/**
 * ChapterSidebar — reusable TOC chapter navigation sidebar.
 *
 * Usage:
 *   <ChapterSidebar
 *     bookId="intro_algorithms"
 *     selectedKeys={selectedChapterKeys}
 *     onToggle={toggleChapter}
 *   />
 *
 * Fetches TOC from Engine API and renders a scrollable chapter list
 * with checkboxes. Supports multi-level indentation based on TOC level.
 * Reusable across Question Gen, Retrievers, Query Engine, etc.
 */

'use client'

import { useState, useEffect } from 'react'
import { Loader2, Check } from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'

// ============================================================
// Types
// ============================================================

export interface TocEntry {
  id: string
  title: string
  level: number
  number?: string
  pdf_page?: number
}

interface ChapterSidebarProps {
  /** The book_id to fetch TOC for */
  bookId: string
  /** Currently selected chapter keys */
  selectedKeys: Set<string>
  /** Toggle a chapter key on/off */
  onToggle: (key: string) => void
  /** Width in pixels (default 200) */
  width?: number
  /** Max height CSS value (default '60vh') */
  maxHeight?: string
  /** Hint text shown at the bottom */
  hint?: string
}

// ============================================================
// Constants
// ============================================================

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Component
// ============================================================

export function ChapterSidebar({
  bookId,
  selectedKeys,
  onToggle,
  width = 200,
  maxHeight = '60vh',
  hint,
}: ChapterSidebarProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // ==========================================================
  // State
  // ==========================================================
  const [chapters, setChapters] = useState<TocEntry[]>([])
  const [loading, setLoading] = useState(true)

  // ==========================================================
  // Effects
  // ==========================================================
  useEffect(() => {
    setChapters([])
    setLoading(true)

    fetch(`${ENGINE}/engine/books/${bookId}/toc`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data: TocEntry[]) => setChapters(data))
      .catch(() => setChapters([]))
      .finally(() => setLoading(false))
  }, [bookId])

  // ==========================================================
  // Render
  // ==========================================================
  if (loading) {
    return (
      <div
        className="shrink-0 border-r border-border bg-muted/20 flex items-center justify-center"
        style={{ width }}
      >
        <div className="flex items-center gap-2 text-xs text-muted-foreground p-3">
          <Loader2 className="h-3 w-3 animate-spin" />
          {isZh ? '加载目录…' : 'Loading…'}
        </div>
      </div>
    )
  }

  if (chapters.length === 0) return null

  return (
    <div
      className="shrink-0 border-r border-border bg-muted/20 rounded-l-lg flex flex-col"
      style={{ width }}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-border">
        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
          {isZh ? '章节' : 'Chapters'}
        </span>
        {selectedKeys.size > 0 && (
          <span className="text-[10px] text-primary ml-1">({selectedKeys.size})</span>
        )}
      </div>

      {/* Chapter list */}
      <div className="flex-1 overflow-y-auto" style={{ maxHeight }}>
        <div className="py-1">
          {chapters.map((ch) => {
            const isSelected = selectedKeys.has(ch.id)
            return (
              <button
                key={ch.id}
                onClick={() => onToggle(ch.id)}
                className={cn(
                  'flex items-center gap-1.5 w-full text-left px-2 py-1.5 transition-colors',
                  'hover:bg-secondary/50',
                  isSelected && 'bg-primary/5',
                )}
                style={{ paddingLeft: `${8 + (ch.level - 1) * 10}px` }}
              >
                <div className={cn(
                  'w-3.5 h-3.5 rounded border shrink-0 flex items-center justify-center transition-colors',
                  isSelected ? 'border-primary bg-primary' : 'border-muted-foreground/30',
                )}>
                  {isSelected && <Check className="h-2.5 w-2.5 text-primary-foreground" strokeWidth={3} />}
                </div>
                <span className={cn(
                  'text-[10px] truncate',
                  isSelected ? 'text-primary font-medium' : 'text-muted-foreground',
                )}>
                  {ch.number ? `${ch.number} ` : ''}{ch.title}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Footer hint */}
      <div className="px-3 py-1.5 border-t border-border">
        <p className="text-[9px] text-muted-foreground/60">
          {hint ?? (isZh ? '不选=全书' : 'None = whole book')}
        </p>
      </div>
    </div>
  )
}
