/**
 * TocTab — Table of Contents browser for the selected book (RT-01).
 *
 * Calls Engine GET /books/{book_id}/toc and renders a hierarchical tree
 * with level-based indentation. Clicking a TOC entry navigates to
 * the Chunks tab filtered by that chapter.
 *
 * Layout: single-column tree list within the ImportPage content area.
 * The book is selected via the shared SidebarLayout book sidebar.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  BookOpen, Loader2, AlertCircle, ChevronRight, ChevronDown,
  List, FileText,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { BookBase } from '@/features/shared/books'
import { fetchToc, type TocEntry } from '../api'

// ============================================================
// Props
// ============================================================
interface TocTabProps {
  books: BookBase[]
  filter: string
}

// ============================================================
// Component
// ============================================================
export default function TocTab({ books, filter }: TocTabProps) {
  const [entries, setEntries] = useState<TocEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  // Determine selected book from filter
  const selectedBookId = filter.startsWith('book::') ? filter.slice(6) : null
  const selectedBook = selectedBookId
    ? books.find((b) => b.book_id === selectedBookId) ?? null
    : null

  // Fetch TOC when book changes
  const loadToc = useCallback(async (bookId: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchToc(bookId)
      setEntries(data)
      // Auto-expand level-1 entries
      const level1Ids = new Set(data.filter((e) => e.level === 1).map((e) => e.id))
      setExpandedIds(level1Ids)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load TOC')
      setEntries([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedBookId) {
      loadToc(selectedBookId)
    } else {
      setEntries([])
      setError(null)
    }
  }, [selectedBookId, loadToc])

  // Toggle expand/collapse
  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // ── No book selected ──
  if (!selectedBook) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <List className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          Select a book from the sidebar to view its table of contents
        </p>
      </div>
    )
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading TOC…</span>
      </div>
    )
  }

  // ── Error ──
  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4 inline mr-2" />
        {error}
        <button
          type="button"
          onClick={() => selectedBookId && loadToc(selectedBookId)}
          className="ml-3 text-xs underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    )
  }

  // ── Empty TOC ──
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
        <BookOpen className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          No table of contents found for this book
        </p>
        <p className="text-xs text-muted-foreground/60">
          The book may not have structured headings
        </p>
      </div>
    )
  }

  // ── Build tree structure ──
  // Group entries by parent for rendering with expand/collapse
  const renderEntry = (entry: TocEntry, index: number) => {
    const indent = (entry.level - 1) * 20
    const isExpanded = expandedIds.has(entry.id)
    // Check if this entry has children (next entry has higher level)
    const hasChildren = index < entries.length - 1 && entries[index + 1].level > entry.level
    // Check if this entry should be visible
    // An entry is visible if all its ancestors are expanded
    // Simple approach: check if any ancestor at a lower level is collapsed
    let visible = true
    for (let i = index - 1; i >= 0; i--) {
      if (entries[i].level < entry.level) {
        if (!expandedIds.has(entries[i].id)) {
          visible = false
          break
        }
        if (entries[i].level === 1) break
      }
    }
    if (!visible) return null

    return (
      <button
        key={entry.id}
        type="button"
        onClick={() => hasChildren && toggleExpand(entry.id)}
        className={cn(
          'flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg transition-colors text-sm',
          'hover:bg-muted/50',
          entry.level === 1 && 'font-semibold text-foreground',
          entry.level === 2 && 'font-medium text-foreground/90',
          entry.level >= 3 && 'text-muted-foreground',
        )}
        style={{ paddingLeft: `${12 + indent}px` }}
      >
        {/* Expand/collapse icon */}
        <span className="w-4 shrink-0">
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )
          ) : (
            <FileText className="h-3 w-3 text-muted-foreground/50" />
          )}
        </span>

        {/* Number badge */}
        {entry.number && (
          <span className="text-[10px] font-mono text-muted-foreground bg-muted rounded px-1.5 py-0.5 shrink-0">
            {entry.number}
          </span>
        )}

        {/* Title */}
        <span className="truncate flex-1">{entry.title}</span>

        {/* Page number */}
        <span className="text-[10px] text-muted-foreground tabular-nums shrink-0">
          p.{entry.pdf_page}
        </span>
      </button>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <List className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            Table of Contents
          </span>
          <span className="text-xs text-muted-foreground">
            {entries.length} entries
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setExpandedIds(new Set(entries.map((e) => e.id)))}
            className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Expand all
          </button>
          <span className="text-muted-foreground/30">|</span>
          <button
            type="button"
            onClick={() => setExpandedIds(new Set())}
            className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Collapse all
          </button>
        </div>
      </div>

      {/* TOC tree */}
      <div className="rounded-xl border border-border bg-card overflow-hidden divide-y divide-border/30">
        {entries.map((entry, i) => renderEntry(entry, i))}
      </div>
    </div>
  )
}
