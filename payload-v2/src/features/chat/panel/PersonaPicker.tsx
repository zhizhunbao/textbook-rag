/**
 * PersonaPicker — Grouped dropdown panel for switching consulting personas.
 *
 * Replaces the native <select> with a popover that groups personas by category,
 * supports keyboard search, and shows description on hover.
 *
 * Usage:
 *   <PersonaPicker
 *     personas={personas}
 *     selectedSlug={slug}
 *     disabled={loading || modeLocked}
 *     onSelect={setSelectedPersonaSlug}
 *   />
 */

'use client'

import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { ChevronDown, Search, X } from 'lucide-react'
import type { PersonaInfo } from '@/features/shared/consultingApi'

// ── Category metadata ──────────────────────────────────────────
const CATEGORY_META: Record<string, { label: string; emoji: string; order: number }> = {
  education:   { label: 'Education',   emoji: '🎓', order: 0 },
  immigration: { label: 'Immigration', emoji: '🛂', order: 1 },
  settlement:  { label: 'Settlement',  emoji: '🏠', order: 2 },
  healthcare:  { label: 'Healthcare',  emoji: '🏥', order: 3 },
  finance:     { label: 'Finance',     emoji: '💰', order: 4 },
  career:      { label: 'Career',      emoji: '💼', order: 5 },
  legal:       { label: 'Legal',       emoji: '⚖️', order: 6 },
  analysis:    { label: 'Analysis',    emoji: '📊', order: 7 },
}

interface PersonaPickerProps {
  personas: PersonaInfo[]
  selectedSlug: string | null
  disabled?: boolean
  disabledTitle?: string
  onSelect: (slug: string) => void
}

export default function PersonaPicker({
  personas,
  selectedSlug,
  disabled,
  disabledTitle,
  onSelect,
}: PersonaPickerProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const selected = personas.find((p) => p.slug === selectedSlug)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  // Focus search when opened
  useEffect(() => {
    if (open) {
      // Small delay so the element is rendered
      requestAnimationFrame(() => searchRef.current?.focus())
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open])

  // Filter + group personas
  const grouped = useMemo(() => {
    const lowerSearch = search.toLowerCase()
    const filtered = search
      ? personas.filter(
          (p) =>
            p.name.toLowerCase().includes(lowerSearch) ||
            (p.description ?? '').toLowerCase().includes(lowerSearch) ||
            (p.category ?? '').toLowerCase().includes(lowerSearch),
        )
      : personas

    const groups: Record<string, PersonaInfo[]> = {}
    for (const p of filtered) {
      const cat = p.category ?? 'other'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(p)
    }

    // Sort groups by predefined order
    return Object.entries(groups).sort(([a], [b]) => {
      const orderA = CATEGORY_META[a]?.order ?? 99
      const orderB = CATEGORY_META[b]?.order ?? 99
      return orderA - orderB
    })
  }, [personas, search])

  const handleSelect = useCallback(
    (slug: string) => {
      onSelect(slug)
      setOpen(false)
      setSearch('')
    },
    [onSelect],
  )

  const totalFiltered = grouped.reduce((sum, [, items]) => sum + items.length, 0)

  return (
    <div ref={containerRef} className="relative">
      {/* ── Trigger button ── */}
      <button
        type="button"
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled}
        title={disabled ? (disabledTitle ?? 'Persona locked') : 'Switch persona'}
        className={`flex items-center gap-1.5 h-7 max-w-[200px] rounded-md border border-border bg-background px-2.5 text-[11px] font-medium text-foreground outline-none transition hover:border-primary/50 focus:border-primary ${
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
        } ${open ? 'border-primary ring-1 ring-primary/20' : ''}`}
      >
        <span className="truncate flex-1 text-left">{selected?.name ?? 'Select persona'}</span>
        <ChevronDown
          size={12}
          className={`shrink-0 text-muted-foreground transition-transform duration-200 ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* ── Dropdown panel ── */}
      {open && (
        <div className="absolute right-0 top-[calc(100%+4px)] z-50 w-[320px] overflow-hidden rounded-xl border border-border bg-card shadow-xl shadow-black/15 animate-in fade-in slide-in-from-top-1 duration-150">
          {/* Search bar */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search size={13} className="shrink-0 text-muted-foreground" />
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search personas…"
              className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground outline-none"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={12} />
              </button>
            )}
            <span className="text-[10px] tabular-nums text-muted-foreground">
              {totalFiltered}
            </span>
          </div>

          {/* Scrollable list */}
          <div className="max-h-[380px] overflow-y-auto overscroll-contain py-1">
            {grouped.length === 0 ? (
              <div className="px-4 py-6 text-center text-xs text-muted-foreground">
                No personas found
              </div>
            ) : (
              grouped.map(([category, items]) => {
                const meta = CATEGORY_META[category]
                return (
                  <div key={category}>
                    {/* Category header */}
                    <div className="sticky top-0 z-10 flex items-center gap-2 bg-card/95 backdrop-blur-sm px-3 py-1.5 border-b border-border/50">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        {meta?.label ?? category}
                      </span>
                      <span className="text-[10px] tabular-nums text-muted-foreground/60">
                        {items.length}
                      </span>
                    </div>

                    {/* Persona items */}
                    {items.map((persona) => {
                      const isActive = persona.slug === selectedSlug
                      return (
                        <button
                          key={persona.slug}
                          type="button"
                          onClick={() => handleSelect(persona.slug)}
                          className={`group flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors ${
                            isActive
                              ? 'bg-primary/8 text-foreground'
                              : 'text-foreground/90 hover:bg-muted/60'
                          }`}
                        >
                          {/* Active indicator */}
                          <div className="mt-1 flex h-4 w-4 shrink-0 items-center justify-center">
                            {isActive && (
                              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                            )}
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="text-[11px] font-semibold leading-tight truncate">
                              {persona.name}
                            </div>
                            {persona.description && (
                              <div className="mt-0.5 text-[10px] leading-snug text-muted-foreground truncate">
                                {persona.description}
                              </div>
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
