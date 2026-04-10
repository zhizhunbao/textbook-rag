'use client'

/**
 * QuestionCards — renders a grid of clickable AI-generated question cards.
 * 问题卡片网格组件 — 支持 topic hint 标签 + Markdown/KaTeX 渲染。
 *
 * Used by:
 *   - chat/panel/WelcomeScreen → pulls high-quality questions to display
 *   - questions/QuestionsPage  → (future) inline generation preview
 */

import Markdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'
import type { Question } from '../types'

/* ── Color palette for topic hints ── */
const TOPIC_COLORS = [
  'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
]

const CARD_ICONS = [
  // lightbulb
  <svg key="i0" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M9.75 17.25h4.5M12 3v.75m4.243 1.007-.53.53M20.25 12H21m-3.257 4.243.53.53M3.75 12H3m3.257-4.243-.53-.53M7.757 4.757l-.53-.53" />
  </svg>,
  // academic cap
  <svg key="i1" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342" />
  </svg>,
  // book
  <svg key="i2" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
  </svg>,
  // code
  <svg key="i3" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
  </svg>,
  // magnifying glass
  <svg key="i4" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
  </svg>,
  // sparkles
  <svg key="i5" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
  </svg>,
]

/** Either a stored Question or a raw GeneratedQuestion — we normalise here */
interface QuestionItem {
  question: string
  topicHint?: string | null
  topic_hint?: string
  questionCategory?: string | null
  question_category?: string
  scoreOverall?: number | null
}

interface Props {
  /** Questions to display (from Payload or fresh from generation) */
  questions: QuestionItem[]
  /** Click handler — typically submits the question text to the chat */
  onSelect: (questionText: string) => void
  /** Disable clicks (e.g. while chat is loading) */
  disabled?: boolean
  /** Header text above the cards */
  header?: string
}

export default function QuestionCards({
  questions,
  onSelect,
  disabled = false,
  header = 'AI-suggested questions based on your books',
}: Props) {
  if (questions.length === 0) return null

  return (
    <div className="w-full">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <svg className="h-4 w-4 text-primary" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
        </svg>
        <span>{header}</span>
      </div>
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {questions.map((q, index) => {
          const hint = q.topicHint ?? q.topic_hint ?? null

          return (
            <button
              key={`q-${index}`}
              onClick={() => onSelect(q.question)}
              disabled={disabled}
              className="group rounded-xl border border-border bg-card px-3 py-3 text-left shadow-sm transition-all hover:border-primary/30 hover:shadow-md hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 shrink-0 rounded-lg bg-muted p-1.5 text-muted-foreground transition-colors group-hover:bg-primary/10 group-hover:text-primary">
                  {CARD_ICONS[index % CARD_ICONS.length]}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap gap-1 mb-1">
                    {(q.questionCategory ?? q.question_category) && (
                      <span className="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                        {q.questionCategory ?? q.question_category}
                      </span>
                    )}
                    {hint && (
                      <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${TOPIC_COLORS[index % TOPIC_COLORS.length]}`}>
                        {hint}
                      </span>
                    )}
                  </div>
                  <div className="text-sm leading-snug text-muted-foreground group-hover:text-foreground [&_p]:my-0 [&_.katex]:text-[0.85em]">
                    <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {q.question}
                    </Markdown>
                  </div>
                  {q.scoreOverall != null && (
                    <span className="mt-1 inline-block text-[10px] text-muted-foreground/70">
                      ★ {q.scoreOverall}
                    </span>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
