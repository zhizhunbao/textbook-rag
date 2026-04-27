/**
 * PromptSelector — Prompt mode selector for chat sessions.
 *
 * Usage: <PromptSelector selectedSlug={slug} onSelect={handleSelect} />
 *
 * Replaces ModeToggle (answer/trace). Fetches prompt modes from
 * response_synthesizers/usePromptModes and displays a dropdown.
 */

'use client'

import { useState, useRef, useEffect } from 'react'
import { Sparkles, ChevronDown, Check } from 'lucide-react'
import { cn } from '@/features/shared/utils'
import { usePromptModes } from '@/features/engine/response_synthesizers/usePromptModes'

// ============================================================
// Types
// ============================================================
interface PromptSelectorProps {
  selectedSlug: string | null
  onSelect: (slug: string, systemPrompt: string) => void
  className?: string
}

// ============================================================
// Component
// ============================================================
export default function PromptSelector({
  selectedSlug,
  onSelect,
  className,
}: PromptSelectorProps) {
  const { promptModes, loading } = usePromptModes()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // ==========================================================
  // Derived state
  // ==========================================================
  const selected = promptModes.find((m) => m.slug === selectedSlug)
    ?? promptModes.find((m) => m.isDefault)
    ?? promptModes[0]

  // ==========================================================
  // Auto-select default on load
  // ==========================================================
  useEffect(() => {
    if (!selectedSlug && promptModes.length > 0) {
      const defaultMode = promptModes.find((m) => m.isDefault) ?? promptModes[0]
      if (defaultMode) {
        onSelect(defaultMode.slug, defaultMode.systemPrompt)
      }
    }
  }, [promptModes, selectedSlug, onSelect])

  // ==========================================================
  // Click outside to close
  // ==========================================================
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // ==========================================================
  // Render
  // ==========================================================
  if (loading || promptModes.length === 0) {
    return (
      <div className={cn('inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1.5 text-[11px] text-muted-foreground', className)}>
        <Sparkles className="h-3 w-3" />
        {loading ? '…' : 'No modes'}
      </div>
    )
  }

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1.5 text-[12px] font-medium text-foreground outline-none transition',
          'hover:bg-accent focus:border-primary',
          open && 'border-primary bg-accent'
        )}
      >
        <Sparkles className="h-3 w-3 text-primary" />
        <span className="max-w-[120px] truncate">{selected?.name ?? 'Prompt'}</span>
        <ChevronDown className={cn('h-3 w-3 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 w-48 max-h-64 overflow-y-auto rounded-lg border border-border bg-card shadow-lg animate-in fade-in-0 zoom-in-95">
          {promptModes.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => {
                onSelect(mode.slug, mode.systemPrompt)
                setOpen(false)
              }}
              className={cn(
                'w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors',
                'hover:bg-secondary/50',
                mode.slug === selected?.slug && 'bg-primary/5'
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-medium text-foreground">{mode.name}</span>
                  {mode.isDefault && (
                    <span className="text-[9px] font-semibold rounded-full px-1.5 py-0.5 bg-primary/10 text-primary">
                      default
                    </span>
                  )}
                </div>
                {mode.description && (
                  <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
                    {mode.description}
                  </p>
                )}
              </div>
              {mode.slug === selected?.slug && (
                <Check className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
