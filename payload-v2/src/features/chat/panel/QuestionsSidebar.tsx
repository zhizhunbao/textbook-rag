/**
 * chat/QuestionsSidebar — Right-side collapsible panel for suggested questions
 *
 * Data source priority:
 *   1. Persona-scoped questions (from consulting-personas DB via personaSlug)
 *   2. CMS questions scoped to session bookIds (via useSuggestedQuestions)
 *   3. Ottawa EcDev defaults from data/suggested_questions.json (fallback)
 *
 * Layout:
 *  ┌─────────────────────┐
 *  │ 💡 Questions  [X]   │  ← header
 *  │ 🔍 Search...        │  ← filter
 *  │ 📖 Category         │  ← group (expandable)
 *  │    question text     │
 *  └─────────────────────┘
 */
'use client'

import { useState, useMemo, useEffect } from 'react'
import {
  Lightbulb,
  X,
  Search,
  ChevronRight,
  MessageCircleQuestion,
  Loader2,
  BookOpen,
  UserCircle,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import { useSuggestedQuestions } from '@/features/engine/question_gen'

// ============================================================
// Types
// ============================================================
interface QuestionsSidebarProps {
  /** Active session book IDs (engine book_id strings) to query questions for */
  bookIds: string[]
  /** Whether a specific book scope is active (false = "all docs" mode) */
  isScoped?: boolean
  /** Active consulting persona slug — triggers persona-scoped questions */
  personaSlug?: string | null
  /** Called when user clicks a question */
  onSelect: (question: string) => void
  /** Close this panel */
  onClose: () => void
  className?: string
  /** Inline style — used for dynamic resizable width */
  style?: React.CSSProperties
}

// ============================================================
// Default Ottawa EcDev questions (fallback when no CMS questions)
// ============================================================
import suggestedQuestionsData from '../../../../../data/suggested_questions.json'

type QuestionCategory = { id: string; label: string; icon: string; questions: string[] }
const DEFAULT_CATEGORIES: QuestionCategory[] = suggestedQuestionsData.categories

// ============================================================
// Hook: fetch persona-scoped suggested questions from DB
// ============================================================
function usePersonaQuestions(personaSlug: string | null | undefined) {
  const [categories, setCategories] = useState<QuestionCategory[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!personaSlug) {
      setCategories([])
      return
    }

    let cancelled = false
    setLoading(true)

    fetch(`/api/consulting-personas?where[slug][equals]=${personaSlug}&limit=1`)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return
        const persona = data?.docs?.[0]
        if (persona?.suggestedQuestions && Array.isArray(persona.suggestedQuestions)) {
          setCategories(persona.suggestedQuestions)
        } else {
          setCategories([])
        }
      })
      .catch(() => {
        if (!cancelled) setCategories([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [personaSlug])

  return { categories, loading }
}

// ============================================================
// Helpers
// ============================================================

/** Group CMS questions by questionCategory (preferred) or bookTitle (fallback). */
function groupByCategory(questions: Array<{ question: string; bookTitle: string | null; questionCategory: string | null }>) {
  const map = new Map<string, string[]>()
  for (const q of questions) {
    const key = q.questionCategory || q.bookTitle || 'Untitled'
    const arr = map.get(key) ?? []
    arr.push(q.question)
    map.set(key, arr)
  }
  return [...map.entries()].map(([label, qs]) => ({ label, questions: qs }))
}

// ============================================================
// Component
// ============================================================
export default function QuestionsSidebar({
  bookIds,
  isScoped = false,
  personaSlug,
  onSelect,
  onClose,
  className,
  style,
}: QuestionsSidebarProps) {
  // Only fetch CMS questions when scoped to specific books
  const { questions: cmsQuestions, loading: cmsLoading } = useSuggestedQuestions(isScoped ? bookIds : [], 50)
  // Fetch persona-scoped questions if a consulting persona is active
  const { categories: personaCategories, loading: personaLoading } = usePersonaQuestions(personaSlug)
  const [search, setSearch] = useState('')
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)

  const loading = cmsLoading || personaLoading

  // Decide data source: persona questions > CMS questions > defaults
  const hasPersonaQuestions = personaCategories.length > 0
  const hasCmsQuestions = cmsQuestions.length > 0

  // Build display groups from persona / CMS / defaults (priority order)
  const displayGroups = useMemo(() => {
    let groups: Array<{ label: string; icon?: string; questions: string[] }>

    if (hasPersonaQuestions) {
      groups = personaCategories.map((cat) => ({
        label: cat.label,
        icon: cat.icon,
        questions: cat.questions,
      }))
    } else if (hasCmsQuestions) {
      groups = groupByCategory(cmsQuestions).map((g) => ({
        label: g.label,
        icon: '🏷️',
        questions: g.questions,
      }))
    } else {
      groups = DEFAULT_CATEGORIES.map((cat) => ({
        label: cat.label,
        icon: cat.icon,
        questions: cat.questions,
      }))
    }

    // Apply search filter
    if (search.trim()) {
      const lower = search.toLowerCase()
      groups = groups
        .map((g) => ({
          ...g,
          questions: g.questions.filter((q) => q.toLowerCase().includes(lower)),
        }))
        .filter((g) => g.questions.length > 0)
    }

    return groups
  }, [hasPersonaQuestions, personaCategories, hasCmsQuestions, cmsQuestions, search])

  const totalQuestions = displayGroups.reduce((s, g) => s + g.questions.length, 0)

  // Auto-expand first group if only one
  const effectiveExpanded = expandedGroup ?? (displayGroups.length === 1 ? displayGroups[0].label : null)

  // Source label
  const sourceLabel = hasPersonaQuestions
    ? `Persona questions`
    : hasCmsQuestions
      ? `Scoped to ${bookIds.length} book${bookIds.length > 1 ? 's' : ''} · grouped by topic`
      : null

  return (
    <aside
      className={cn(
        'flex flex-col h-full shrink-0 bg-card border-l border-border',
        className,
      )}
      style={style}
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <Lightbulb size={16} className="text-amber-500" />
          <span className="text-sm font-semibold text-foreground">Questions</span>
          <span className="text-[10px] text-muted-foreground bg-muted rounded-full px-1.5 py-0.5">
            {totalQuestions}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex items-center justify-center h-7 w-7 rounded-md text-muted-foreground hover:bg-muted transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      {/* ── Search ── */}
      <div className="px-3 py-2 border-b border-border shrink-0">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search questions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-border bg-background pl-8 pr-8 py-1.5 text-xs outline-none focus:border-primary transition-colors"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* ── Source label ── */}
      {sourceLabel && (
        <div className="px-3 py-1.5 border-b border-border/50 shrink-0">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            {hasPersonaQuestions ? <UserCircle size={10} /> : <BookOpen size={10} />}
            <span>{sourceLabel}</span>
          </div>
        </div>
      )}

      {/* ── Question List ── */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <Loader2 size={20} className="animate-spin text-muted-foreground" />
            <span className="text-xs text-muted-foreground">Loading questions…</span>
          </div>
        ) : displayGroups.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2 px-4 text-center">
            <MessageCircleQuestion size={28} className="text-muted-foreground/40" />
            <p className="text-xs text-muted-foreground">No results found</p>
          </div>
        ) : (
          displayGroups.map((group) => {
            const isExpanded = effectiveExpanded === group.label
            return (
              <div key={group.label} className="border-b border-border/50 last:border-b-0">
                <button
                  type="button"
                  onClick={() => setExpandedGroup(isExpanded ? null : group.label)}
                  className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs">{group.icon}</span>
                    <span className="text-xs font-medium text-foreground truncate">
                      {group.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] font-medium text-primary bg-primary/10 rounded-full px-1.5 py-0.5">
                      {group.questions.length}
                    </span>
                    <ChevronRight
                      size={14}
                      className={cn(
                        'text-muted-foreground transition-transform duration-200',
                        isExpanded && 'rotate-90',
                      )}
                    />
                  </div>
                </button>
                {isExpanded && (
                  <div className="pb-1">
                    {group.questions.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => onSelect(question)}
                        className="w-full text-left px-3 py-2 hover:bg-secondary/60 transition-colors group"
                      >
                        <div className="flex items-start gap-2">
                          <MessageCircleQuestion
                            size={13}
                            className="mt-0.5 text-primary/50 group-hover:text-primary shrink-0 transition-colors"
                          />
                          <p className="text-[11px] text-foreground leading-relaxed line-clamp-3">
                            {question}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* ── Footer ── */}
      <div className="shrink-0 px-3 py-2 border-t border-border">
        <p className="text-center text-[10px] text-muted-foreground">
          {totalQuestions} suggested questions
          {hasPersonaQuestions && ' (persona)'}
          {!hasPersonaQuestions && !hasCmsQuestions && ' (defaults)'}
        </p>
      </div>
    </aside>
  )
}
