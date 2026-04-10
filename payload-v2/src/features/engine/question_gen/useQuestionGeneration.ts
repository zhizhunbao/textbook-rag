'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { BookBase } from '@/features/shared/books'
import type { GeneratedQuestion } from './types'
import { generateQuestions, saveQuestionToPayload } from './api'

/* ─────────────────────────────────────────────── */
/* useQuestionGeneration                            */
/* 自包含的问题生成 hook — 封装 generate / save / retry */
/* Questions 页面用来触发新问题生成 + 评分入库          */
/* ─────────────────────────────────────────────── */

export interface UseQuestionGenerationReturn {
  /** AI 生成的问题列表 / Generated question list */
  questions: GeneratedQuestion[]
  /** 是否正在生成 / Whether generation is in progress */
  generating: boolean
  /** 是否已完成过一次生成 / Whether generation has completed at least once */
  generated: boolean
  /** 生成失败 / Whether generation failed */
  failed: boolean
  /** 手动触发（重新）生成 / Trigger (re)generation */
  regenerate: () => void
}

export function useQuestionGeneration(
  sessionBooks: BookBase[],
  count = 3,
): UseQuestionGenerationReturn {
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([])
  const [generating, setGenerating] = useState(true)
  const [generated, setGenerated] = useState(false)
  const [failed, setFailed] = useState(false)

  // Stable ref for sessionBooks to avoid stale closures
  const sessionBooksRef = useRef(sessionBooks)
  sessionBooksRef.current = sessionBooks

  const bookIds = sessionBooks.map((b) => b.book_id)

  const doGenerate = useCallback(() => {
    const currentBookIds = sessionBooksRef.current.map((b) => b.book_id)
    if (currentBookIds.length === 0) return

    setGenerating(true)
    setGenerated(false)
    setFailed(false)

    generateQuestions(currentBookIds, count)
      .then((qs) => {
        setQuestions(qs)
        setGenerating(false)
        setGenerated(true)
        if (qs.length === 0) setFailed(true)

        // Note: engine backend already auto-persists + auto-scores to Payload.
        // The frontend save below is a supplementary path for category/subcategory
        // metadata that only the frontend knows about.
        for (const q of qs) {
          const matchedBook = sessionBooksRef.current.find(
            (b) => b.book_id === q.book_id,
          )
          saveQuestionToPayload({
            question: q.question,
            bookId: q.book_id,
            bookTitle: q.book_title,
            topicHint: q.topic_hint,
            source: 'ai',
            likes: 0,
            category: matchedBook?.category || 'textbooks',
            subcategory: matchedBook?.subcategory || '',
            questionCategory: (q as any).question_category || '',
            sourcePage: (q as any).source_page ?? undefined,
            scoreRelevance: (q as any).score_relevance || undefined,
            scoreClarity: (q as any).score_clarity || undefined,
            scoreDifficulty: (q as any).score_difficulty || undefined,
            scoreOverall: (q as any).score_overall || undefined,
          }).catch(() => { /* silently fail */ })
        }
      })
      .catch(() => {
        setGenerating(false)
        setGenerated(true)
        setFailed(true)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count])

  // Auto-generate when book selection changes
  useEffect(() => {
    if (bookIds.length === 0) return
    doGenerate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookIds.join(',')])

  return {
    questions,
    generating,
    generated,
    failed,
    regenerate: doGenerate,
  }
}
