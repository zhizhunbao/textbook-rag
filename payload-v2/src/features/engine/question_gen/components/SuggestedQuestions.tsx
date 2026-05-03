/**
 * SuggestedQuestions — Horizontal card row of recommended questions.
 *
 * Consumed by chat WelcomeScreen. Clicking a card triggers onSelect
 * which auto-fills the chat input with the question text.
 */

'use client'

import { Sparkles, Loader2, MessageCircleQuestion } from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import type { Question } from '../types'
import { cn } from '@/features/shared/utils'

// ============================================================
// Types
// ============================================================
interface SuggestedQuestionsProps {
  questions: Question[]
  loading?: boolean
  onSelect?: (question: string) => void
  className?: string
}

// ============================================================
// Difficulty badge color
// ============================================================
function difficultyColor(score: number | null): string {
  if (!score) return 'text-muted-foreground'
  if (score <= 2) return 'text-emerald-500'
  if (score <= 3) return 'text-amber-500'
  return 'text-rose-500'
}

function difficultyLabel(score: number | null, isZh: boolean): string {
  if (!score) return ''
  if (score <= 2) return isZh ? '基础' : 'Basic'
  if (score <= 3) return isZh ? '中等' : 'Medium'
  return isZh ? '进阶' : 'Advanced'
}

// ============================================================
// Component
// ============================================================
export default function SuggestedQuestions({
  questions,
  loading = false,
  onSelect,
  className,
}: SuggestedQuestionsProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center py-6', className)}>
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mr-2" />
        <span className="text-xs text-muted-foreground">
          {isZh ? '加载推荐问题...' : 'Loading suggestions...'}
        </span>
      </div>
    )
  }

  if (questions.length === 0) return null

  return (
    <div className={cn('space-y-2', className)}>
      {/* Header */}
      <div className="flex items-center gap-1.5 px-1">
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-medium text-muted-foreground">
          {isZh ? '推荐问题' : 'Suggested Questions'}
        </span>
      </div>

      {/* Cards row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {questions.map((q) => (
          <button
            key={q.id}
            type="button"
            onClick={() => onSelect?.(q.question)}
            className={cn(
              'group text-left rounded-lg border border-border bg-card/50 p-3',
              'hover:bg-secondary/60 hover:border-primary/20 hover:shadow-sm',
              'transition-all duration-150 cursor-pointer',
            )}
          >
            {/* Question text */}
            <div className="flex items-start gap-2">
              <MessageCircleQuestion className="h-3.5 w-3.5 mt-0.5 text-primary/60 shrink-0 group-hover:text-primary transition-colors" />
              <p className="text-xs text-foreground line-clamp-2 leading-relaxed">
                {q.question}
              </p>
            </div>

            {/* Meta row */}
            <div className="flex items-center gap-2 mt-2 pl-5.5">
              {q.bookTitle && (
                <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                  {q.bookTitle}
                </span>
              )}
              {q.scoreDifficulty && (
                <span className={cn('text-[10px] font-medium', difficultyColor(q.scoreDifficulty))}>
                  {difficultyLabel(q.scoreDifficulty, isZh)}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
