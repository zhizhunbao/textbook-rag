'use client'

import { BookOpen, User, Hash, Layers } from 'lucide-react'
import type { LibraryBook } from './types'
import StatusBadge, { PipelineProgress } from './StatusBadge'

/**
 * BookCard — 单本教材卡片
 *
 * 显示书名、作者、分类、chunk 数量、状态
 * 点击触发 onSelect 回调（跳转到 Chat 或展开详情）
 */
interface BookCardProps {
  book: LibraryBook
  onSelect?: (book: LibraryBook) => void
}

const categoryLabels: Record<string, { label: string; color: string }> = {
  textbook: { label: 'Textbook', color: 'bg-brand-500/10 text-brand-400' },
  ecdev: { label: 'EC Dev', color: 'bg-purple-500/10 text-purple-400' },
  real_estate: { label: 'Real Estate', color: 'bg-teal-500/10 text-teal-400' },
}

export default function BookCard({ book, onSelect }: BookCardProps) {
  const cat = categoryLabels[book.category] ?? categoryLabels.textbook
  const pageCount = book.metadata?.pageCount ?? 0
  const chapterCount = book.metadata?.chapterCount ?? 0

  return (
    <button
      type="button"
      onClick={() => onSelect?.(book)}
      className="relative w-full text-left group p-4 rounded-xl border border-border bg-card hover:bg-secondary/50
                 transition-all duration-200 hover:shadow-md hover:border-primary/20"
    >
      {/* Top row: category badge */}
      <div className="mb-3">
        <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${cat.color}`}>
          {cat.label}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-sm font-semibold text-foreground line-clamp-2 mb-2 group-hover:text-primary transition-colors">
        <BookOpen className="inline h-4 w-4 mr-1.5 -mt-0.5 text-muted-foreground" />
        {book.title}
      </h3>

      {/* Author */}
      {book.authors && (
        <p className="text-xs text-muted-foreground mb-3 truncate">
          <User className="inline h-3 w-3 mr-1 -mt-0.5" />
          {book.authors}
        </p>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
        {pageCount > 0 && (
          <span className="flex items-center gap-1">
            <Hash className="h-3 w-3" />
            {pageCount} pages
          </span>
        )}
        {chapterCount > 0 && (
          <span className="flex items-center gap-1">
            <Layers className="h-3 w-3" />
            {chapterCount} chapters
          </span>
        )}
        {book.chunkCount && book.chunkCount > 0 && (
          <span className="flex items-center gap-1">
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            {book.chunkCount} chunks
          </span>
        )}
      </div>

      {/* Pipeline progress (visible when processing or indexed) */}
      {(book.status === 'processing' || book.status === 'indexed') && (
        <div className="mt-3 pt-3 border-t border-border">
          <PipelineProgress pipeline={book.pipeline} />
        </div>
      )}

      {/* Status badge — bottom-right */}
      <div className="absolute bottom-3 right-3">
        <StatusBadge status={book.status} />
      </div>
    </button>
  )
}
