'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { LibraryBook, BookCategory } from './types'
import { fetchLibraryBooks } from './api'

/**
 * useLibraryBooks — 带搜索、分类筛选、自动轮询的书籍列表 hook
 *
 * 参考 Ottawa document-list.tsx 的 auto-poll 模式:
 * 当有 processing 状态的书时自动轮询刷新
 */
export function useLibraryBooks() {
  const [books, setBooks] = useState<LibraryBook[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<BookCategory | 'all'>('all')

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isFirstLoad = useRef(true)

  const load = useCallback(async () => {
    try {
      if (isFirstLoad.current) setLoading(true)

      const { books: data, total: t } = await fetchLibraryBooks({
        category: category === 'all' ? undefined : category,
        search: search.trim() || undefined,
      })

      setBooks(data)
      setTotal(t)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
      isFirstLoad.current = false
    }
  }, [category, search])

  // Initial load & filter change
  useEffect(() => {
    isFirstLoad.current = true
    load()
  }, [load])

  // Auto-poll when any book is processing
  useEffect(() => {
    const hasProcessing = books.some(
      (b) => b.status === 'processing' || b.status === 'pending'
    )

    if (hasProcessing) {
      pollTimerRef.current = setTimeout(load, 5000)
    }

    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [books, load])

  return {
    books,
    total,
    loading,
    error,
    search,
    setSearch,
    category,
    setCategory,
    refresh: load,
  }
}
