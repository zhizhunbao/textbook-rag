/**
 * /consulting — Consulting Chat Route
 *
 * Entry point for the consulting chat experience.
 * Loads the user's selected persona and renders ConsultingChatPage.
 * Redirects to /onboarding if no persona is selected.
 */

'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'
import ConsultingChatPage from '@/features/consulting/ConsultingChatPage'
import { fetchConsultingPersonas, type PersonaInfo } from '@/features/consulting/api'

export default function ConsultingRoute() {
  const { user, status } = useAuth()
  const [persona, setPersona] = useState<PersonaInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'loggedOut') {
      window.location.href = '/login'
    }
  }, [status])

  // Load the user's selected persona
  useEffect(() => {
    if (!user) return

    const selectedPersona = user.selectedPersona
    if (!selectedPersona) {
      // Not onboarded — redirect
      window.location.href = '/onboarding'
      return
    }

    // Resolve persona slug from the selectedPersona field
    const slug = typeof selectedPersona === 'object'
      ? selectedPersona.slug
      : null

    if (!slug) {
      // selectedPersona is just an ID — fetch from Engine to get full data
      fetchConsultingPersonas()
        .then((personas) => {
          const match = typeof selectedPersona === 'number'
            ? personas.find((p) => p.slug) // fallback: first persona
            : personas.find((p) => p.slug === slug)

          if (match) {
            setPersona(match)
          } else if (personas.length > 0) {
            setPersona(personas[0])
          } else {
            setError('No consulting personas available')
          }
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false))
      return
    }

    // Have slug — fetch persona info from Engine
    fetchConsultingPersonas()
      .then((personas) => {
        const match = personas.find((p) => p.slug === slug)
        if (match) {
          setPersona(match)
        } else {
          setError(`Persona "${slug}" not found`)
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [user])

  // Auth loading
  if (status === undefined || loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-primary" />
          <span className="text-sm">Loading consultant…</span>
        </div>
      </div>
    )
  }

  if (status === 'loggedOut') return null

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-sm text-destructive">{error}</p>
          <a href="/onboarding" className="text-xs text-primary hover:underline">
            Select a role →
          </a>
        </div>
      </div>
    )
  }

  if (!persona) return null

  return <ConsultingChatPage persona={persona} />
}
