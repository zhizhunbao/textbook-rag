/**
 * useBookSidebar — builds SidebarItem[] from a book list.
 *
 * Two modes:
 *   'by-book'     — each sidebar item = one book, count from external countMap
 *   'by-category'  — each sidebar item = one category/subcategory, count = books in that group
 *
 * Usage:
 *   const { sidebarItems, filterItems } = useBookSidebar(books, { mode: 'by-book', countMap })
 *   const { sidebarItems, filterItems } = useBookSidebar(books, { mode: 'by-category' })
 */

'use client'

import { useMemo, type ReactNode } from 'react'
import type { SidebarItem } from '@/features/shared/components/SidebarLayout'
import type { BookBase } from './types'
import { CATEGORY_CONFIGS, getCategoryConfig } from './types'

// ============================================================
// Types
// ============================================================

interface ByBookOptions {
  mode: 'by-book'
  /** Map of book_id → count for the sidebar badge. */
  countMap?: Map<string, number>
  /** Whether to use Chinese labels. Default: false. */
  isFr?: boolean
  /** "All" label. Default: 'All'. */
  allLabel?: string
  /** Icon for each book item. */
  bookIcon?: ReactNode
  /** Icon for "All" item. */
  allIcon?: ReactNode
  /** Map of category key → icon ReactNode (for category headers). */
  categoryIcons?: Record<string, ReactNode>
}

interface ByCategoryOptions {
  mode: 'by-category'
  /** Whether to use Chinese labels. Default: false. */
  isFr?: boolean
  /** "All" label. Default: 'All Books'. */
  allLabel?: string
  /** Icon for "All" item. */
  allIcon?: ReactNode
  /** Map of category key → icon ReactNode. */
  categoryIcons?: Record<string, ReactNode>
}

export type UseBookSidebarOptions = ByBookOptions | ByCategoryOptions

// ============================================================
// Hook
// ============================================================

export function useBookSidebar(
  books: BookBase[],
  options: UseBookSidebarOptions,
) {

  // ==========================================================
  // Build sidebar items
  // ==========================================================
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    if (options.mode === 'by-book') {
      return buildByBook(books, options)
    }
    return buildByCategory(books, options)
  }, [books, options])

  // ==========================================================
  // Filter helper
  // ==========================================================

  /** Filter a list of items by the current sidebar filter key. */
  function filterItems<T extends { bookId?: string; category?: string; subcategory?: string }>(
    items: T[],
    filter: string,
  ): T[] {
    if (filter === 'all') return items

    // by-book mode: filter = "book::<book_id>"
    if (filter.startsWith('book::')) {
      const bookId = filter.slice(6)
      return items.filter((item) => item.bookId === bookId)
    }

    // by-category mode: filter = "category::subcategory" or just "category"
    if (filter.includes('::')) {
      const sub = filter.split('::')[1]
      return items.filter((item) => item.subcategory === sub)
    }

    // plain category key
    return items.filter((item) => (item.category || 'textbooks') === filter)
  }

  /** Filter books by the current sidebar filter key. */
  function filterBooks(filter: string): BookBase[] {
    if (filter === 'all') return books

    if (filter.startsWith('book::')) {
      const bookId = filter.slice(6)
      return books.filter((b) => b.book_id === bookId)
    }

    if (filter.includes('::')) {
      const [cat, sub] = filter.split('::')
      return books.filter((b) => (b.category || 'textbooks') === cat && b.subcategory === sub)
    }

    return books.filter((b) => (b.category || 'textbooks') === filter)
  }

  // ==========================================================
  // Return
  // ==========================================================
  return { sidebarItems, filterItems, filterBooks }
}

// ============================================================
// Internal builders
// ============================================================

function buildByBook(books: BookBase[], opts: ByBookOptions): SidebarItem[] {
  const countMap = opts.countMap ?? new Map()
  const isFr = opts.isFr ?? false

  const items: SidebarItem[] = [
    {
      key: 'all',
      label: opts.allLabel ?? 'All',
      count: books.length,
      icon: opts.allIcon,
    },
  ]

  // Group books by category → subcategory
  const grouped: Record<string, Record<string, BookBase[]>> = {}
  for (const book of books) {
    const cat = book.category || 'textbooks'
    const sub = book.subcategory || ''
    if (!grouped[cat]) grouped[cat] = {}
    if (!grouped[cat][sub]) grouped[cat][sub] = []
    grouped[cat][sub].push(book)
  }

  // Build category → subcategory → book hierarchy
  // Iterate over ALL categories found in data (not just CATEGORY_CONFIGS keys)
  const catKeys = Object.keys(grouped).sort((a, b) => {
    // Known categories first, then alphabetical
    const aKnown = a in CATEGORY_CONFIGS ? 0 : 1
    const bKnown = b in CATEGORY_CONFIGS ? 0 : 1
    if (aKnown !== bKnown) return aKnown - bKnown
    return a.localeCompare(b)
  })

  for (const catKey of catKeys) {
    const cfg = getCategoryConfig(catKey)
    const catSubs = grouped[catKey]
    if (!catSubs) continue

    const allCatBooks = Object.values(catSubs).flat()
    if (allCatBooks.length === 0) continue

    // Category shows book count (always visible)
    items.push({
      key: catKey,
      label: isFr ? cfg.labelFr : cfg.label,
      count: allCatBooks.length,
      icon: opts.categoryIcons?.[catKey],
      collapsible: true,
    })

    // Sort subcategory keys (empty string = no subcategory, goes first)
    const subKeys = Object.keys(catSubs).sort((a, b) => {
      if (a === '') return -1
      if (b === '') return 1
      return a.localeCompare(b)
    })

    for (const subKey of subKeys) {
      const subBooks = catSubs[subKey]

      if (subKey) {
        // Subcategory shows book count (always visible)
        items.push({
          key: `${catKey}::${subKey}`,
          label: subKey,
          count: subBooks.length,
          indentLevel: 1,
          collapsible: true,
        })
      }

      // Sort books: newest first (by year+quarter or year+month), then by count, then alphabetical
      const MONTH_MAP: Record<string, number> = {
        january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
        july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
      }
      const sorted = [...subBooks].sort((a, b) => {
        // Extract a comparable date value from the title
        const dateVal = (title: string): number => {
          // Quarterly: "Q4 2024" → 2024*100 + 4*8 = 202432
          const qm = title.match(/Q(\d)\s+(\d{4})/i)
          if (qm) return parseInt(qm[2]) * 100 + parseInt(qm[1]) * 8

          // Monthly with 2-digit year: "May25", "January26"
          const mm2 = title.match(/(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{2})(?:\b|$)/i)
          if (mm2) {
            const yr = parseInt(mm2[2])
            const fullYear = yr < 50 ? 2000 + yr : 1900 + yr
            return fullYear * 100 + (MONTH_MAP[mm2[1].toLowerCase()] || 0)
          }

          // Monthly with 4-digit year: "July 2014", "March 2013"
          const mm4 = title.match(/(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})/i)
          if (mm4) return parseInt(mm4[2]) * 100 + (MONTH_MAP[mm4[1].toLowerCase()] || 0)

          return 0
        }
        const da = dateVal(a.title)
        const db = dateVal(b.title)
        if (da !== db) return db - da  // newest first

        const ca = countMap.get(a.book_id) || 0
        const cb = countMap.get(b.book_id) || 0
        if (cb !== ca) return cb - ca
        return a.title.localeCompare(b.title)
      })

      for (const book of sorted) {
        items.push({
          key: `book::${book.book_id}`,
          label: book.title,
          count: countMap.get(book.book_id) || 0,
          icon: opts.bookIcon,
          indentLevel: subKey ? 2 : 1,
        })
      }
    }
  }

  return items
}

function buildByCategory(books: BookBase[], opts: ByCategoryOptions): SidebarItem[] {
  const isFr = opts.isFr ?? false

  // Count per category and subcategory
  const counts: Record<string, number> = { all: books.length }
  const subMap: Record<string, Set<string>> = {}

  for (const b of books) {
    const cat = b.category || 'textbooks'
    counts[cat] = (counts[cat] || 0) + 1
    if (b.subcategory) {
      const subKey = `${cat}::${b.subcategory}`
      counts[subKey] = (counts[subKey] || 0) + 1
      if (!subMap[cat]) subMap[cat] = new Set()
      subMap[cat].add(b.subcategory)
    }
  }

  const items: SidebarItem[] = [
    {
      key: 'all',
      label: opts.allLabel ?? (isFr ? '全部' : 'All Books'),
      count: counts.all || 0,
      icon: opts.allIcon,
    },
  ]

  // Iterate over ALL categories found in data
  const catKeys = Object.keys(counts)
    .filter((k) => k !== 'all' && !k.includes('::'))
    .sort((a, b) => {
      const aKnown = a in CATEGORY_CONFIGS ? 0 : 1
      const bKnown = b in CATEGORY_CONFIGS ? 0 : 1
      if (aKnown !== bKnown) return aKnown - bKnown
      return a.localeCompare(b)
    })

  for (const catKey of catKeys) {
    const cfg = getCategoryConfig(catKey)
    const count = counts[catKey] || 0
    if (count === 0) continue

    items.push({
      key: catKey,
      label: isFr ? cfg.labelFr : cfg.label,
      count,
      icon: opts.categoryIcons?.[catKey],
      collapsible: !!subMap[catKey],
    })

    // Subcategories
    const subs = subMap[catKey]
    if (subs) {
      for (const sub of [...subs].sort()) {
        items.push({
          key: `${catKey}::${sub}`,
          label: sub,
          count: counts[`${catKey}::${sub}`] || 0,
          indent: true,
        })
      }
    }
  }

  return items
}
