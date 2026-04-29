/**
 * OnboardingPage — Full-screen role selection for first-time users.
 *
 * Displays a card grid of enabled consulting personas.
 * On confirm, PATCHes the user's selectedPersona + isOnboarded, then redirects.
 */

'use client'

import { useState } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n'
import { usePersonas, type Persona } from './usePersonas'
import { cn } from '@/features/shared/utils'

// ── Lucide icon map — maps icon name string to inline SVG paths ──

const ICON_MAP: Record<string, React.ReactNode> = {
  scale: (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v17" /><path d="M5 7l7-4 7 4" />
      <path d="M3 13l2-6 4 6a4 4 0 0 1-6 0z" /><path d="M15 13l2-6 4 6a4 4 0 0 1-6 0z" />
    </svg>
  ),
  'shield-check': (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  ),
  'clipboard-check': (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <path d="M9 14l2 2 4-4" />
    </svg>
  ),
}

/** Fallback icon when icon name not in map */
function FallbackIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
    </svg>
  )
}

// ── Persona Card ──

function PersonaCard({
  persona,
  selected,
  onSelect,
}: {
  persona: Persona
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'group relative flex flex-col items-center gap-4 p-8 rounded-2xl border-2 transition-all duration-300',
        'bg-card/80 backdrop-blur-sm hover:shadow-lg hover:-translate-y-1',
        selected
          ? 'border-primary shadow-[0_0_0_4px_rgba(37,99,235,0.15)] bg-primary/5'
          : 'border-border hover:border-primary/40',
      )}
    >
      {/* Selected indicator */}
      {selected && (
        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )}

      {/* Icon */}
      <div className={cn(
        'w-16 h-16 rounded-2xl flex items-center justify-center transition-colors duration-300',
        selected ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary',
      )}>
        {persona.icon && ICON_MAP[persona.icon] ? ICON_MAP[persona.icon] : <FallbackIcon />}
      </div>

      {/* Name */}
      <h3 className={cn(
        'text-lg font-bold transition-colors',
        selected ? 'text-primary' : 'text-foreground',
      )}>
        {persona.name}
      </h3>

      {/* Description */}
      {persona.description && (
        <p className="text-sm text-muted-foreground text-center leading-relaxed">
          {persona.description}
        </p>
      )}
    </button>
  )
}

// ── Main Page ──

export default function OnboardingPage() {
  const { user, setUser } = useAuth()
  const { t } = useI18n()
  const { personas, loading, error, refetch } = usePersonas()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const handleSeedPersonas = async () => {
    try {
      setSeeding(true)
      setSaveError(null)
      const res = await fetch('/api/seed', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collections: ['consulting-personas'] }),
      })
      if (!res.ok) throw new Error(`Seed failed: ${res.status}`)
      await refetch()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSeeding(false)
    }
  }

  const handleConfirm = async () => {
    if (!selectedId || !user) return
    try {
      setSaving(true)
      setSaveError(null)
      const res = await fetch(`/api/users/${user.id}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selectedPersona: selectedId,
          isOnboarded: true,
        }),
      })
      if (!res.ok) throw new Error(`Save failed: ${res.status}`)
      const { doc } = await res.json()
      setUser({ ...user, isOnboarded: true, selectedPersona: doc.selectedPersona ?? selectedId })
      window.location.href = '/consulting'
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden
      bg-[linear-gradient(135deg,#004890_0%,#0066cc_50%,#004890_100%)]
      dark:bg-[linear-gradient(135deg,#0a1628_0%,#0d2240_40%,#1a3a5c_70%,#0d2240_100%)]"
    >
      {/* Background orbs */}
      <div className="absolute inset-0 z-0 opacity-10 pointer-events-none">
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-white rounded-full blur-[150px] -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-white rounded-full blur-[120px] translate-y-1/3 -translate-x-1/4" />
      </div>

      {/* Content card */}
      <div className="relative z-10 w-full max-w-3xl backdrop-blur-xl rounded-3xl shadow-[0_32px_64px_rgba(0,0,0,0.3)]
        bg-card/95 text-card-foreground border border-border/50 p-10
        animate-[slideUp_0.8s_cubic-bezier(0.34,1.56,0.64,1)]"
      >
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-extrabold text-primary mb-2">{t.onboardingTitle}</h1>
          <p className="text-sm text-muted-foreground">{t.onboardingSubtitle}</p>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="text-center py-8 text-destructive text-sm">{error}</div>
        )}

        {/* Persona grid */}
        {!loading && !error && personas.length > 0 && (
          <div className={cn(
            'grid gap-6 mb-8',
            personas.length <= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
          )}>
            {personas.map((p) => (
              <PersonaCard
                key={p.id}
                persona={p}
                selected={selectedId === p.id}
                onSelect={() => setSelectedId(p.id)}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && personas.length === 0 && (
          <div className="mb-8 rounded-2xl border border-border bg-muted/30 p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v18" />
                <path d="M5 7l7-4 7 4" />
                <path d="M3 13l2-6 4 6a4 4 0 0 1-6 0Z" />
                <path d="M15 13l2-6 4 6a4 4 0 0 1-6 0Z" />
              </svg>
            </div>
            <h2 className="mb-1 text-sm font-semibold text-foreground">
              No consulting roles found
            </h2>
            <p className="mx-auto mb-4 max-w-sm text-xs text-muted-foreground">
              Initialize the default consulting roles to continue onboarding.
            </p>
            <button
              type="button"
              onClick={() => void handleSeedPersonas()}
              disabled={seeding}
              className="inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {seeding ? (
                <span className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14" />
                  <path d="M5 12h14" />
                </svg>
              )}
              {seeding ? 'Initializing...' : 'Initialize default roles'}
            </button>
          </div>
        )}

        {/* Save error */}
        {saveError && (
          <div className="text-center text-destructive text-sm mb-4">{saveError}</div>
        )}

        {/* Confirm button */}
        <div className="text-center">
          <button
            type="button"
            disabled={!selectedId || saving}
            onClick={handleConfirm}
            className="inline-flex items-center gap-2.5 px-8 py-4 rounded-xl text-base font-semibold text-white
              bg-[linear-gradient(135deg,#003d7a,#004890)] shadow-[0_8px_30px_rgba(0,72,144,0.3)]
              hover:translate-y-[-2px] hover:shadow-[0_12px_40px_rgba(0,72,144,0.4)]
              active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed disabled:translate-y-0
              transition-all duration-300"
          >
            {saving ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t.onboardingSaving}
              </>
            ) : (
              <>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                {t.onboardingConfirm}
              </>
            )}
          </button>
          {!selectedId && !loading && personas.length > 0 && (
            <p className="text-xs text-muted-foreground mt-3">{t.onboardingNoPersona}</p>
          )}
        </div>
      </div>
    </div>
  )
}
