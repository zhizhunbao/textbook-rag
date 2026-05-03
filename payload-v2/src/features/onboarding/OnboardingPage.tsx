/**
 * OnboardingPage — Full-screen role selection for first-time users.
 *
 * Reuses the shared CATEGORIES + AVATAR_MAP from consultingRoles.ts
 * and the PublicNav header for consistent branding.
 *
 * On confirm, PATCHes the user's selectedPersona + isOnboarded, then redirects.
 */

'use client'

import { useState, useMemo } from 'react'
import Image from 'next/image'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n'
import { usePersonas, type Persona } from './usePersonas'
import { cn } from '@/features/shared/utils'
import PublicNav from '@/features/layout/PublicNav'
import { CATEGORIES, AVATAR_MAP, type CategoryDef } from '@/features/shared/consultingRoles'
import AdvisorCard from '@/features/home/AdvisorCard'

// ── Category Section ──

function CategorySection({
  cat,
  personas,
  selectedId,
  onSelect,
}: {
  cat: CategoryDef
  personas: Persona[]
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  if (personas.length === 0) return null

  return (
    <div>
      <h3 className={cn('mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider', cat.textColor)}>
        <span className={cn('inline-block h-1.5 w-1.5 rounded-full bg-gradient-to-r', cat.color)} />
        {cat.label}
        <span className="text-[10px] font-medium text-muted-foreground">({personas.length})</span>
      </h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {personas.map((p) => (
          <AdvisorCard
            key={p.id}
            slug={p.slug}
            name={p.nameEn || p.name}
            description={p.description}
            avatar={p.avatar || AVATAR_MAP[p.slug]}
            cat={cat}
            mode="select"
            selected={selectedId === p.id}
            onSelect={() => onSelect(p.id)}
          />
        ))}
      </div>
    </div>
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

  // Group personas by category using shared CATEGORIES
  const grouped = useMemo(() => {
    return CATEGORIES.map((cat) => ({
      cat,
      roles: personas.filter((p) => p.category === cat.value),
    })).filter((g) => g.roles.length > 0)
  }, [personas])

  const selectedPersona = personas.find((p) => p.id === selectedId)

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

  const selectedAvatarSrc = selectedPersona
    ? (selectedPersona.avatar || AVATAR_MAP[selectedPersona.slug])
    : undefined

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/50 to-indigo-50/30 dark:from-[#0a1628] dark:via-[#0d2240] dark:to-[#0a1628]">
      {/* Background effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(59,130,246,0.12),transparent)] dark:bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(59,130,246,0.08),transparent)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.02)_1px,transparent_1px)] bg-[size:64px_64px] dark:bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)]" />
      </div>

      {/* Reuse existing PublicNav */}
      <PublicNav page="onboarding" />

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-6xl px-6 pb-32 pt-24">
        {/* Header */}
        <div className="mb-10 text-center">
          <div className="mx-auto mb-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-primary backdrop-blur dark:border-primary/30 dark:bg-primary/10">
            Expert Center
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground md:text-4xl">
            {t.onboardingTitle}
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-base text-muted-foreground">
            {t.onboardingSubtitle}
          </p>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 rounded-full border-[3px] border-primary/20 border-t-primary animate-spin" />
              <span className="text-sm text-muted-foreground">Loading expert roles...</span>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="mx-auto max-w-md rounded-xl border border-destructive/20 bg-destructive/5 px-6 py-4 text-center text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Empty state — seed button */}
        {!loading && !error && personas.length === 0 && (
          <div className="mx-auto max-w-md rounded-2xl border border-border bg-card p-8 text-center shadow-lg">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v18" /><path d="M5 7l7-4 7 4" />
                <path d="M3 13l2-6 4 6a4 4 0 0 1-6 0Z" /><path d="M15 13l2-6 4 6a4 4 0 0 1-6 0Z" />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-bold text-foreground">No consulting roles found</h2>
            <p className="mb-6 text-sm text-muted-foreground">
              Initialize the default consulting roles to continue.
            </p>
            <button
              type="button"
              onClick={() => void handleSeedPersonas()}
              disabled={seeding}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {seeding ? (
                <span className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14" /><path d="M5 12h14" />
                </svg>
              )}
              {seeding ? 'Initializing...' : 'Initialize default roles'}
            </button>
          </div>
        )}

        {/* Categorized persona grid */}
        {!loading && !error && personas.length > 0 && (
          <div className="space-y-8">
            {grouped.map(({ cat, roles }) => (
              <CategorySection
                key={cat.value}
                cat={cat}
                personas={roles}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            ))}
          </div>
        )}

        {/* Save error */}
        {saveError && (
          <div className="mx-auto mt-6 max-w-md rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-center text-sm text-destructive">
            {saveError}
          </div>
        )}
      </div>

      {/* Sticky bottom bar */}
      {!loading && personas.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-200/60 bg-white/90 backdrop-blur-xl dark:border-white/8 dark:bg-slate-950/90">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            {/* Left — selection summary */}
            <div className="flex items-center gap-3">
              {selectedPersona ? (
                <>
                  {selectedAvatarSrc && (
                    <div className="h-9 w-9 shrink-0 overflow-hidden rounded-full ring-2 ring-primary/40">
                      <Image src={selectedAvatarSrc} alt="" width={36} height={36} className="h-full w-full object-cover" />
                    </div>
                  )}
                  <div>
                    <div className="text-sm font-bold text-foreground">
                      {selectedPersona.nameEn || selectedPersona.name}
                    </div>
                    <div className="text-xs text-muted-foreground">Selected role</div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">{t.onboardingNoPersona}</p>
              )}
            </div>

            {/* Right — confirm button */}
            <button
              type="button"
              disabled={!selectedId || saving}
              onClick={handleConfirm}
              className={cn(
                'inline-flex items-center gap-2.5 rounded-xl px-7 py-3 text-sm font-bold transition-all duration-300',
                selectedId
                  ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-primary/30 active:translate-y-0'
                  : 'cursor-not-allowed bg-muted text-muted-foreground opacity-60',
              )}
            >
              {saving ? (
                <>
                  <div className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                  {t.onboardingSaving}
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  {t.onboardingConfirm}
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </main>
  )
}
