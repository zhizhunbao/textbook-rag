'use client'
/**
 * QuestionPicker — Reusable question selector component (QD-07).
 *
 * Used by RetrieverTestPage, QueryEnginePage, and EvaluationPage.
 * Supports single/multi select, book/dataset filtering, and fuzzy search.
 *
 * Aligned with: collections/Questions + collections/QuestionSets
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react'
import type { Question, QuestionSet } from '@/features/engine/question_gen/types'
import { fetchQuestions, fetchQuestionSets, fetchQuestionsByDataset } from '@/features/engine/question_gen/api'

// ── Component Props ─────────────────────────────────────────────────────────
interface QuestionPickerProps {
  bookFilter?: string[]
  datasetFilter?: number
  maxItems?: number
  onSelect?: (question: Question) => void
  onSelectMulti?: (questions: Question[]) => void
  mode?: 'single' | 'multi'
}

// ── Styles ──────────────────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  container: {
    border: '1px solid var(--border-color, rgba(255,255,255,0.12))',
    borderRadius: 10,
    backgroundColor: 'var(--card-bg, rgba(30,32,44,0.85))',
    overflow: 'hidden',
    fontSize: 13,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 14px',
    borderBottom: '1px solid var(--border-color, rgba(255,255,255,0.08))',
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontWeight: 600,
    color: 'var(--text-primary, #e0e0e0)',
  },
  datasetSelect: {
    padding: '4px 8px',
    borderRadius: 6,
    border: '1px solid var(--border-color, rgba(255,255,255,0.15))',
    backgroundColor: 'var(--input-bg, rgba(255,255,255,0.06))',
    color: 'var(--text-primary, #e0e0e0)',
    fontSize: 12,
    outline: 'none',
  },
  searchBox: {
    padding: '8px 14px',
    borderBottom: '1px solid var(--border-color, rgba(255,255,255,0.06))',
  },
  searchInput: {
    width: '100%',
    padding: '6px 10px',
    borderRadius: 6,
    border: '1px solid var(--border-color, rgba(255,255,255,0.12))',
    backgroundColor: 'var(--input-bg, rgba(255,255,255,0.06))',
    color: 'var(--text-primary, #e0e0e0)',
    fontSize: 12,
    outline: 'none',
  },
  list: {
    maxHeight: 280,
    overflowY: 'auto' as const,
    padding: '4px 0',
  },
  bookGroup: {
    padding: '6px 14px 2px',
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted, #888)',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '7px 14px',
    cursor: 'pointer',
    transition: 'background 0.15s',
    borderLeft: '3px solid transparent',
  },
  itemHover: {
    backgroundColor: 'var(--hover-bg, rgba(255,255,255,0.06))',
  },
  itemSelected: {
    borderLeftColor: 'var(--accent-color, #6c8aff)',
    backgroundColor: 'var(--selected-bg, rgba(108,138,255,0.08))',
  },
  scoreBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 28,
    height: 20,
    borderRadius: 4,
    fontSize: 10,
    fontWeight: 700,
    flexShrink: 0,
  },
  questionText: {
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    color: 'var(--text-primary, #e0e0e0)',
    fontSize: 12,
  },
  bookTag: {
    fontSize: 10,
    color: 'var(--text-muted, #888)',
    flexShrink: 0,
  },
  empty: {
    padding: '20px 14px',
    textAlign: 'center' as const,
    color: 'var(--text-muted, #888)',
    fontSize: 12,
  },
  chevron: {
    fontSize: 14,
    transition: 'transform 0.2s',
  },
}

// ── Score color helper ──────────────────────────────────────────────────────
function getScoreColor(score: number | null): string {
  if (!score) return 'rgba(255,255,255,0.1)'
  if (score >= 4) return 'rgba(76,175,80,0.25)'
  if (score >= 3) return 'rgba(255,193,7,0.25)'
  return 'rgba(244,67,54,0.2)'
}

function getScoreTextColor(score: number | null): string {
  if (!score) return '#888'
  if (score >= 4) return '#4caf50'
  if (score >= 3) return '#ffc107'
  return '#f44336'
}

// ── Component ───────────────────────────────────────────────────────────────
export default function QuestionPicker({
  bookFilter,
  datasetFilter,
  maxItems = 20,
  onSelect,
  onSelectMulti,
  mode = 'single',
}: QuestionPickerProps) {
  const [questions, setQuestions] = useState<Question[]>([])
  const [datasets, setDatasets] = useState<QuestionSet[]>([])
  const [selectedDataset, setSelectedDataset] = useState<number | null>(datasetFilter ?? null)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [hoveredId, setHoveredId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  // Load datasets on mount
  useEffect(() => {
    fetchQuestionSets().then(setDatasets).catch(() => {})
  }, [])

  // Load questions when dataset or book filter changes
  useEffect(() => {
    setLoading(true)
    const load = async () => {
      try {
        let qs: Question[]
        if (selectedDataset) {
          qs = await fetchQuestionsByDataset(selectedDataset)
        } else {
          qs = await fetchQuestions(500)
        }
        // Apply book filter
        if (bookFilter?.length) {
          qs = qs.filter((q) => bookFilter.includes(q.bookId))
        }
        setQuestions(qs.slice(0, maxItems))
      } catch {
        setQuestions([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [selectedDataset, bookFilter, maxItems])

  // Group by book
  const grouped = useMemo(() => {
    const filtered = search
      ? questions.filter((q) =>
          q.question.toLowerCase().includes(search.toLowerCase()),
        )
      : questions

    const groups: Record<string, Question[]> = {}
    for (const q of filtered) {
      const key = q.bookTitle || q.bookId || 'Unknown'
      ;(groups[key] ??= []).push(q)
    }
    return groups
  }, [questions, search])

  const handleSelect = useCallback(
    (q: Question) => {
      if (mode === 'multi') {
        setSelectedIds((prev) => {
          const next = new Set(prev)
          if (next.has(q.id)) {
            next.delete(q.id)
          } else {
            next.add(q.id)
          }
          const selected = questions.filter((qq) => next.has(qq.id))
          onSelectMulti?.(selected)
          return next
        })
      } else {
        setSelectedIds(new Set([q.id]))
        onSelect?.(q)
      }
    },
    [mode, onSelect, onSelectMulti, questions],
  )

  return (
    <div style={styles.container} id="question-picker">
      {/* Header — collapsible */}
      <div style={styles.header} onClick={() => setExpanded(!expanded)}>
        <div style={styles.headerLeft}>
          <span>📋</span>
          <span>Select a test question</span>
          {selectedIds.size > 0 && (
            <span style={{ fontSize: 11, color: '#6c8aff' }}>
              ({selectedIds.size} selected)
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Dataset dropdown */}
          <select
            id="question-picker-dataset-select"
            style={styles.datasetSelect}
            value={selectedDataset ?? ''}
            onChange={(e) => {
              e.stopPropagation()
              const val = e.target.value
              setSelectedDataset(val ? Number(val) : null)
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <option value="">All Questions</option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.name} ({ds.questionCount})
              </option>
            ))}
          </select>
          <span
            style={{
              ...styles.chevron,
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          >
            ▼
          </span>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <>
          {/* Search box */}
          <div style={styles.searchBox}>
            <input
              id="question-picker-search"
              style={styles.searchInput}
              placeholder="🔍 Search questions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Question list */}
          <div style={styles.list}>
            {loading && (
              <div style={styles.empty}>Loading questions...</div>
            )}
            {!loading && Object.keys(grouped).length === 0 && (
              <div style={styles.empty}>
                No questions — run Question Gen to create some
              </div>
            )}
            {!loading &&
              Object.entries(grouped).map(([book, qs]) => (
                <div key={book}>
                  <div style={styles.bookGroup}>📖 {book}</div>
                  {qs.map((q) => {
                    const isSelected = selectedIds.has(q.id)
                    const isHovered = hoveredId === q.id
                    return (
                      <div
                        key={q.id}
                        id={`question-picker-item-${q.id}`}
                        style={{
                          ...styles.item,
                          ...(isHovered ? styles.itemHover : {}),
                          ...(isSelected ? styles.itemSelected : {}),
                        }}
                        onClick={() => handleSelect(q)}
                        onMouseEnter={() => setHoveredId(q.id)}
                        onMouseLeave={() => setHoveredId(null)}
                      >
                        {/* Score badge */}
                        <span
                          style={{
                            ...styles.scoreBadge,
                            backgroundColor: getScoreColor(q.scoreOverall),
                            color: getScoreTextColor(q.scoreOverall),
                          }}
                        >
                          {q.scoreOverall ? `★${q.scoreOverall}` : '—'}
                        </span>
                        {/* Question text */}
                        <span style={styles.questionText} title={q.question}>
                          {q.question}
                        </span>
                        {/* Source tag */}
                        {q.sourcePage != null && (
                          <span style={styles.bookTag}>p.{q.sourcePage}</span>
                        )}
                      </div>
                    )
                  })}
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  )
}
