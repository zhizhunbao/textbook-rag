/**
 * BookEditDialog � Inline edit form for book metadata (title, authors, category).
 *
 * Renders below the BookCard when activated. Saves via updateBook API.
 */

'use client'

import { useState, useCallback } from 'react'
import { Save, X, Loader2 } from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { updateBook } from '../api'
import type { LibraryBook, BookCategory } from '../types'
import { WELL_KNOWN_CATEGORIES } from '../types'
import { cn } from '@/features/shared/utils'

// ============================================================
// Types
// ============================================================
interface BookEditDialogProps {
  book: LibraryBook
  onSave?: (updated: LibraryBook) => void
  onCancel?: () => void
}

// ============================================================
// Component
// ============================================================
export default function BookEditDialog({ book, onSave, onCancel }: BookEditDialogProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // ==========================================================
  // State
  // ==========================================================
  const [title, setTitle] = useState(book.title)
  const [authors, setAuthors] = useState(book.authors ?? '')
  const [category, setCategory] = useState<BookCategory>(book.category)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ==========================================================
  // Handlers
  // ==========================================================
  const handleSave = useCallback(async () => {
    if (!title.trim()) {
      setError(isZh ? '??????' : 'Title is required')
      return
    }

    setSaving(true)
    setError(null)

    try {
      const updated = await updateBook(book.id, {
        title: title.trim(),
        authors: authors.trim() || null,
        category,
      })
      onSave?.(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }, [book.id, title, authors, category, isZh, onSave])

  // ==========================================================
  // Field style
  // ==========================================================
  const fieldClass = cn(
    'w-full h-8 px-3 rounded-md border border-input bg-background text-xs text-foreground',
    'placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring/30',
    'transition-colors',
  )

  return (
    <div className="rounded-lg border border-border bg-card/80 backdrop-blur-sm p-4 space-y-3 animate-in slide-in-from-top-1 duration-150">
      {/* Title */}
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1">
          {isZh ? '??' : 'Title'}
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={fieldClass}
          placeholder={isZh ? '?????' : 'Enter title'}
        />
      </div>

      {/* Authors */}
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1">
          {isZh ? '??' : 'Authors'}
        </label>
        <input
          type="text"
          value={authors}
          onChange={(e) => setAuthors(e.target.value)}
          className={fieldClass}
          placeholder={isZh ? '?????' : 'Enter authors'}
        />
      </div>

      {/* Category */}
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1">
          {isZh ? '??' : 'Category'}
        </label>
        <input
          type="text"
          list="category-options"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className={fieldClass}
          placeholder={isZh ? '???????' : 'Type or select category'}
        />
        <datalist id="category-options">
          {WELL_KNOWN_CATEGORIES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {isZh ? opt.labelFr : opt.label}
            </option>
          ))}
        </datalist>
      </div>

      {/* Error */}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
        >
          <X className="h-3 w-3" />
          {isZh ? '??' : 'Cancel'}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
          {isZh ? '??' : 'Save'}
        </button>
      </div>
    </div>
  )
}
