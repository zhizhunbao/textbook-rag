/**
 * BookCard — Single book card with cover, metadata, and pipeline progress.
 *
 * Displays cover image (or gradient placeholder), title, author,
 * category badge, stats row, and PipelineProgress pills.
 */

'use client'

import { BookOpen, User, Hash, Layers } from 'lucide-react'
import type { LibraryBook } from '../types'
import { PipelineProgress } from './StatusBadge'

/**
 * BookCard — 单本教材卡片 (带封面 + 作者)
 *
 * 显示封面、书名、作者、分类、chunk 数量、pipeline 进度、状态
 * 点击触发 onSelect 回调（跳转到 Chat 或展开详情）
 */
interface BookCardProps {
  book: LibraryBook
  onSelect?: (book: LibraryBook) => void
}

const KNOWN_CAT_LABELS: Record<string, { label: string; color: string }> = {
  textbook: { label: 'Textbook', color: 'bg-brand-500/10 text-brand-400' },
  ecdev: { label: 'EC Dev', color: 'bg-purple-500/10 text-purple-400' },
  real_estate: { label: 'Real Estate', color: 'bg-teal-500/10 text-teal-400' },
}

/** Get category badge config — generates one for unknown categories. */
function getCatLabel(category: string): { label: string; color: string } {
  if (KNOWN_CAT_LABELS[category]) return KNOWN_CAT_LABELS[category]
  // Dynamic fallback for LLM-classified categories
  const label = category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  return { label, color: 'bg-violet-500/10 text-violet-400' }
}

/** Generate a consistent gradient from book title for placeholder covers */
function titleToGradient(title: string): string {
  let hash = 0
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash)
  }
  const h1 = Math.abs(hash) % 360
  const h2 = (h1 + 40) % 360
  return `linear-gradient(135deg, hsl(${h1}, 45%, 25%), hsl(${h2}, 55%, 18%))`
}

/** Extract initials from title for placeholder covers */
function titleInitials(title: string): string {
  return title
    .split(/[\s_\-]+/)
    .filter((w) => w.length > 0)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
}

export default function BookCard({ book, onSelect }: BookCardProps) {
  const cat = getCatLabel(book.category)
  const pageCount = book.metadata?.pageCount ?? 0
  const chapterCount = book.metadata?.chapterCount ?? 0
  const coverUrl =
    book.coverImage?.sizes?.card?.url ??
    book.coverImage?.sizes?.thumbnail?.url ??
    book.coverImage?.url ??
    null

  return (
    <button
      type="button"
      onClick={() => onSelect?.(book)}
      className="relative w-full text-left group rounded-xl border border-border bg-card hover:bg-secondary/50
                 transition-all duration-200 hover:shadow-md hover:border-primary/20 overflow-hidden"
    >
      {/* Cover image or gradient placeholder */}
      <div className="relative w-full h-36 overflow-hidden">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={book.title}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div
            className="w-full h-full flex items-center justify-center transition-transform duration-300 group-hover:scale-105"
            style={{ background: titleToGradient(book.title) }}
          >
            <span className="text-3xl font-bold text-white/30 select-none tracking-widest">
              {titleInitials(book.title)}
            </span>
          </div>
        )}
        {/* Gradient overlay for readability */}
        <div className="absolute inset-0 bg-gradient-to-t from-card/90 via-transparent to-transparent" />

        {/* Category badge — overlaid on cover */}
        <span
          className={`absolute top-2 left-2 inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider backdrop-blur-sm ${cat.color}`}
        >
          {cat.label}
        </span>
      </div>

      {/* Content below the cover */}
      <div className="p-4 pt-2">
        {/* Title */}
        <h3 className="text-sm font-semibold text-foreground line-clamp-2 mb-1 group-hover:text-primary transition-colors">
          {book.title}
        </h3>

        {/* Author */}
        <p className="text-xs text-muted-foreground mb-3 truncate">
          <User className="inline h-3 w-3 mr-1 -mt-0.5 opacity-60" />
          {book.authors || 'Unknown Author'}
        </p>

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
              {chapterCount} ch
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
              {book.chunkCount}
            </span>
          )}
        </div>

        {/* Pipeline stage pills */}
        <div className="mt-3 pt-3 border-t border-border">
          <PipelineProgress pipeline={book.pipeline} />
        </div>
      </div>
    </button>
  )
}
