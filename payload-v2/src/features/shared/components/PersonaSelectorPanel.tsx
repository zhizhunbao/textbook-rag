/**
 * PersonaSelectorPanel — Reusable persona selector dropdown.
 *
 * Displays enabled personas in a dropdown, updates user's selectedPersona
 * via PATCH /api/users/{id}. Used in sidebar and settings.
 */

'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'
import { cn } from '@/features/shared/utils'

// ── Types ──

interface PersonaOption {
  id: number
  name: string
  slug: string
  icon?: string
}

interface PersonaSelectorPanelProps {
  className?: string
  onPersonaChange?: (persona: PersonaOption) => void
}

// ── Component ──

export default function PersonaSelectorPanel({
  className,
  onPersonaChange,
}: PersonaSelectorPanelProps) {
  const { user, setUser } = useAuth()
  const [personas, setPersonas] = useState<PersonaOption[]>([])
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  // Current persona
  const current =
    user?.selectedPersona && typeof user.selectedPersona === 'object'
      ? (user.selectedPersona as PersonaOption)
      : null

  // Fetch personas from Payload CMS
  useEffect(() => {
    fetch(
      '/api/consulting-personas?where[isEnabled][equals]=true&sort=sortOrder&limit=20',
      { credentials: 'include' },
    )
      .then((res) => res.json())
      .then((json) => setPersonas(json.docs ?? []))
      .catch(() => setPersonas([]))
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Select persona
  const handleSelect = useCallback(
    async (persona: PersonaOption) => {
      if (!user) return
      setSaving(true)
      try {
        const res = await fetch(`/api/users/${user.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ selectedPersona: persona.id }),
        })
        if (res.ok) {
          // Re-fetch current user to update auth context
          const meRes = await fetch('/api/users/me', {
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
          })
          if (meRes.ok) {
            const { user: freshUser } = await meRes.json()
            if (freshUser) setUser(freshUser)
          }
          onPersonaChange?.(persona)
        }
      } catch {
        // silent fail
      }
      setSaving(false)
      setOpen(false)
    },
    [user, setUser, onPersonaChange],
  )

  if (personas.length === 0) return null

  return (
    <div ref={panelRef} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        disabled={saving}
        className={cn(
          'flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors border',
          'border-border bg-card hover:bg-muted text-foreground',
          saving && 'opacity-60 cursor-not-allowed',
        )}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-primary shrink-0"
        >
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        <span className="flex-1 text-left truncate">
          {current ? current.name : 'Select persona...'}
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className={cn(
            'text-muted-foreground shrink-0 transition-transform',
            open && 'rotate-180',
          )}
        >
          <polyline points="6,9 12,15 18,9" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 z-50 rounded-lg border border-border bg-card shadow-lg overflow-hidden">
          {personas.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => void handleSelect(p)}
              className={cn(
                'flex items-center gap-2 w-full px-3 py-2 text-sm text-left transition-colors',
                'hover:bg-muted',
                current?.id === p.id && 'bg-primary/5 text-primary',
              )}
            >
              <span className="flex-1 truncate">{p.name}</span>
              {current?.id === p.id && (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-primary shrink-0"
                >
                  <polyline points="20,6 9,17 4,12" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
