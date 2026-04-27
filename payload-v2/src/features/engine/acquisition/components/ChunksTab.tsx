/**
 * ChunksTab — Content chunk browser for the selected book (RT-02).
 *
 * Calls Engine GET /books/{book_id}/chunks and renders a scrollable list
 * of text chunks with metadata (page, content type). Supports filtering
 * by TOC entry and pagination via "Load More".
 *
 * Layout: single-column chunk list within the ImportPage content area.
 * The book is selected via the shared SidebarLayout book sidebar.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Layers, Loader2, AlertCircle, FileText,
  Type, Table2, Image, Hash, ChevronDown,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { BookBase } from '@/features/shared/books'
import { fetchChunks, fetchToc, type ChunkEntry, type TocEntry } from '../api'

// ============================================================
// Content type config
// ============================================================
const TYPE_CONFIG: Record<string, { icon: React.ElementType; label: string; color: string }> = {
  text: { icon: Type, label: 'Text', color: 'text-blue-500 bg-blue-500/10' },
  title: { icon: Hash, label: 'Title', color: 'text-purple-500 bg-purple-500/10' },
  table: { icon: Table2, label: 'Table', color: 'text-emerald-500 bg-emerald-500/10' },
  image: { icon: Image, label: 'Image', color: 'text-amber-500 bg-amber-500/10' },
  equation: { icon: Hash, label: 'Equation', color: 'text-cyan-500 bg-cyan-500/10' },
}

const ITEMS_PER_PAGE = 30

// ============================================================
// Props
// ============================================================
interface ChunksTabProps {
  books: BookBase[]
  filter: string
}

// ============================================================
// Component
// ============================================================
export default function ChunksTab({ books, filter }: ChunksTabProps) {
  const [chunks, setChunks] = useState<ChunkEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null)

  // TOC for chapter filter
  const [toc, setToc] = useState<TocEntry[]>([])
  const [selectedTocId, setSelectedTocId] = useState<number | null>(null)
  const [tocLoading, setTocLoading] = useState(false)

  // Pagination
  const [limit, setLimit] = useState(ITEMS_PER_PAGE)

  // Determine selected book
  const selectedBookId = filter.startsWith('book::') ? filter.slice(6) : null
  const selectedBook = selectedBookId
    ? books.find((b) => b.book_id === selectedBookId) ?? null
    : null

  // Load TOC for chapter filter
  useEffect(() => {
    if (!selectedBookId) {
      setToc([])
      return
    }
    setTocLoading(true)
    fetchToc(selectedBookId)
      .then((data) => setToc(data))
      .catch(() => setToc([]))
      .finally(() => setTocLoading(false))
  }, [selectedBookId])

  // Reset state when book changes
  useEffect(() => {
    setSelectedTocId(null)
    setLimit(ITEMS_PER_PAGE)
    setExpandedChunk(null)
  }, [selectedBookId])

  // Load chunks
  const loadChunks = useCallback(async (bookId: string, tocId: number | null, lim: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchChunks(bookId, {
        tocId: tocId ?? undefined,
        limit: lim,
      })
      setChunks(data.chunks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chunks')
      setChunks([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedBookId) {
      loadChunks(selectedBookId, selectedTocId, limit)
    } else {
      setChunks([])
      setError(null)
    }
  }, [selectedBookId, selectedTocId, limit, loadChunks])

  // Load more
  const handleLoadMore = () => {
    setLimit((prev) => prev + ITEMS_PER_PAGE)
  }

  // ── No book selected ──
  if (!selectedBook) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <Layers className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          Select a book from the sidebar to browse its content chunks
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header + Chapter filter */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            Content Chunks
          </span>
          {!loading && (
            <span className="text-xs text-muted-foreground">
              {chunks.length} items
            </span>
          )}
        </div>

        {/* Chapter filter dropdown */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground">Chapter:</label>
          <select
            value={selectedTocId ?? ''}
            onChange={(e) => {
              const val = e.target.value
              setSelectedTocId(val ? Number(val) : null)
              setLimit(ITEMS_PER_PAGE)
            }}
            disabled={tocLoading || toc.length === 0}
            className={cn(
              'h-8 rounded-lg border border-border bg-background px-2 text-xs',
              'text-foreground focus:outline-none focus:ring-1 focus:ring-ring',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'max-w-[280px]',
            )}
          >
            <option value="">All chapters</option>
            {toc.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {'  '.repeat(entry.level - 1)}
                {entry.number ? `${entry.number} ` : ''}
                {entry.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12 gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Loading chunks…</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 inline mr-2" />
          {error}
          <button
            type="button"
            onClick={() => selectedBookId && loadChunks(selectedBookId, selectedTocId, limit)}
            className="ml-3 text-xs underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && chunks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <FileText className="h-10 w-10 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">
            No content chunks found
          </p>
          <p className="text-xs text-muted-foreground/60">
            {selectedTocId ? 'Try selecting a different chapter' : 'This book may not have been processed yet'}
          </p>
        </div>
      )}

      {/* Chunk list */}
      {!loading && !error && chunks.length > 0 && (
        <>
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="divide-y divide-border/30">
              {chunks.map((chunk) => {
                const typeConfig = TYPE_CONFIG[chunk.content_type] || TYPE_CONFIG.text
                const TypeIcon = typeConfig.icon
                const isExpanded = expandedChunk === chunk.id
                const isLong = chunk.text.length > 200

                return (
                  <div
                    key={chunk.id}
                    className="group hover:bg-muted/30 transition-colors"
                  >
                    <button
                      type="button"
                      onClick={() => isLong && setExpandedChunk(isExpanded ? null : chunk.id)}
                      className="flex items-start gap-3 w-full text-left px-4 py-3"
                    >
                      {/* Type badge */}
                      <span className={cn(
                        'flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 mt-0.5',
                        typeConfig.color,
                      )}>
                        <TypeIcon className="h-2.5 w-2.5" />
                        {typeConfig.label}
                      </span>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <p className={cn(
                          'text-sm text-foreground leading-relaxed',
                          !isExpanded && isLong && 'line-clamp-3',
                        )}>
                          {chunk.text}
                        </p>
                        {isLong && (
                          <span className="text-[10px] text-primary mt-1 inline-flex items-center gap-0.5">
                            <ChevronDown className={cn(
                              'h-2.5 w-2.5 transition-transform',
                              isExpanded && 'rotate-180',
                            )} />
                            {isExpanded ? 'Collapse' : 'Show more'}
                          </span>
                        )}
                      </div>

                      {/* Page number */}
                      <span className="text-[10px] text-muted-foreground tabular-nums shrink-0 mt-1">
                        p.{chunk.page_idx}
                      </span>
                    </button>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Load more */}
          {chunks.length >= limit && (
            <div className="flex justify-center pt-2">
              <button
                type="button"
                onClick={handleLoadMore}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium',
                  'border border-border bg-background text-foreground',
                  'hover:bg-muted transition-colors',
                )}
              >
                <ChevronDown className="h-3.5 w-3.5" />
                Load more ({ITEMS_PER_PAGE} items)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
