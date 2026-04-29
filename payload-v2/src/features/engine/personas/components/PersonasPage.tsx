/**
 * PersonasPage — Admin page for managing consulting personas and their KBs.
 *
 * Features:
 *   - Grid of PersonaCards with live status badges
 *   - Click to expand: shows PersonaIngestPanel
 *   - Refresh button for live stats
 */

'use client'

import { useState, useCallback } from 'react'
import { cn } from '@/features/shared/utils'
import { usePersonaAdmin } from '../usePersonaAdmin'
import PersonaCard from './PersonaCard'
import PersonaCreatePanel from './PersonaCreatePanel'
import PersonaIngestPanel from './PersonaIngestPanel'
import type { PersonaWithStats } from '../types'

// ── Component ──

export default function PersonasPage() {
  const { personas, loading, error, refetch } = usePersonaAdmin()
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const selectedPersona = personas.find((p) => p.slug === selectedSlug)

  const handleRefresh = useCallback(() => {
    void refetch()
  }, [refetch])

  const handleCreated = useCallback((persona: PersonaWithStats) => {
    setSelectedSlug(persona.slug)
    void refetch()
  }, [refetch])

  // ── Loading ──
  if (loading && personas.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary animate-spin mb-3">
          <path d="M21 12a9 9 0 1 1-6.22-8.56" />
        </svg>
        <p className="text-sm text-muted-foreground">Loading personas...</p>
      </div>
    )
  }

  // ── Error ──
  if (error && personas.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-red-400 mb-3">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <p className="text-sm text-red-400 mb-3">{error}</p>
        <button
          type="button"
          onClick={handleRefresh}
          className="text-xs text-primary hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  // ── Stats summary ──
  const readyCount = personas.filter((p) => p.status === 'ready').length
  const totalChunks = personas.reduce((sum, p) => sum + p.chunkCount, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground">
                Consulting Personas
              </h1>
              <p className="text-xs text-muted-foreground">
                {personas.length} persona(s) · {readyCount} with knowledge base · {totalChunks} total chunks
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setCreateOpen((value) => !value)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14" />
              <path d="M12 5v14" />
            </svg>
            New persona
          </button>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border',
              loading
                ? 'opacity-60 cursor-not-allowed border-border text-muted-foreground'
                : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={cn(loading && 'animate-spin')}
            >
              <polyline points="23,4 23,10 17,10" />
              <polyline points="1,20 1,14 7,14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      <PersonaCreatePanel
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={handleCreated}
      />

      {/* Persona grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {personas.map((persona) => (
          <PersonaCard
            key={persona.slug}
            persona={persona}
            selected={selectedSlug === persona.slug}
            onClick={() =>
              setSelectedSlug(
                selectedSlug === persona.slug ? null : persona.slug,
              )
            }
          />
        ))}
      </div>

      {/* Empty state */}
      {personas.length === 0 && (
        <div className="flex flex-col items-center py-16">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground/40 mb-3">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          <p className="text-sm text-muted-foreground">
            No consulting personas defined yet.
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Use New persona to create one and initialize its collection.
          </p>
        </div>
      )}

      {/* Ingest panel (shown when a persona is selected) */}
      {selectedPersona && (
        <PersonaIngestPanel
          persona={selectedPersona}
          onIngestComplete={handleRefresh}
        />
      )}
    </div>
  )
}
