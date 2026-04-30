/**
 * PersonaCreatePanel - Admin form for creating consulting personas.
 *
 * Creates the Payload persona record and relies on the collection hook to
 * ensure the persona ChromaDB collection exists.
 */

'use client'

import { useMemo, useState, type FormEvent } from 'react'
import {
  BriefcaseBusiness,
  ClipboardCheck,
  Plus,
  Scale,
  ShieldCheck,
  X,
} from 'lucide-react'

import { cn } from '@/features/shared/utils'
import { createPersona, initPersonaCollection } from '../api'
import type { CreatePersonaInput, PersonaWithStats } from '../types'

const ICON_OPTIONS = [
  { value: 'briefcase-business', label: 'Briefcase', icon: BriefcaseBusiness },
  { value: 'scale', label: 'Legal', icon: Scale },
  { value: 'shield-check', label: 'Compliance', icon: ShieldCheck },
  { value: 'clipboard-check', label: 'Audit', icon: ClipboardCheck },
]

const DEFAULT_PROMPT = `You are a specialist consulting persona.

Use the provided context to answer the user's question with precise, evidence-based reasoning.
If the context is insufficient, say what is missing and avoid guessing.

Context:
{context_str}

Question:
{query_str}`

interface PersonaCreatePanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (persona: PersonaWithStats) => void
}

export default function PersonaCreatePanel({
  open,
  onOpenChange,
  onCreated,
}: PersonaCreatePanelProps) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [icon, setIcon] = useState(ICON_OPTIONS[0]?.value ?? '')
  const [description, setDescription] = useState('')
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_PROMPT)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const derivedSlug = useMemo(() => slugify(name), [name])
  const effectiveSlug = slug || derivedSlug
  const chromaCollection = effectiveSlug ? `ca_${effectiveSlug}` : ''
  const canSubmit = Boolean(name.trim() && effectiveSlug && systemPrompt.trim())

  if (!open) return null

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit || submitting) return

    setSubmitting(true)
    setError(null)

    const payload: CreatePersonaInput = {
      name: name.trim(),
      slug: effectiveSlug,
      icon,
      description: description.trim(),
      systemPrompt: systemPrompt.trim(),
      chromaCollection,
      mineruCategory: 'consulting',
      isEnabled: true,
    }

    try {
      const created = await createPersona(payload)
      await initPersonaCollection(created.slug)
      onCreated(created)
      onOpenChange(false)
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create persona')
    } finally {
      setSubmitting(false)
    }
  }

  function resetForm() {
    setName('')
    setSlug('')
    setIcon(ICON_OPTIONS[0]?.value ?? '')
    setDescription('')
    setSystemPrompt(DEFAULT_PROMPT)
    setError(null)
  }

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold text-foreground">Create persona</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Add a consulting role and initialize its knowledge base collection.
          </p>
        </div>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Close create persona form"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-xs font-semibold text-foreground">Name</span>
            <input
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                if (!slug) setError(null)
              }}
              placeholder="Strategy Advisor"
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </label>

          <label className="space-y-2">
            <span className="text-xs font-semibold text-foreground">Slug</span>
            <input
              value={slug}
              onChange={(event) => setSlug(slugify(event.target.value))}
              placeholder={derivedSlug || 'strategy-advisor'}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
          <div className="space-y-2">
            <span className="text-xs font-semibold text-foreground">Icon</span>
            <div className="grid grid-cols-2 gap-2">
              {ICON_OPTIONS.map((option) => {
                const Icon = option.icon
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setIcon(option.value)}
                    className={cn(
                      'flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors',
                      icon === option.value
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground',
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {option.label}
                  </button>
                )
              })}
            </div>
          </div>

          <label className="space-y-2">
            <span className="text-xs font-semibold text-foreground">Chroma collection</span>
            <input
              value={chromaCollection}
              readOnly
              className="w-full rounded-lg border border-input bg-muted px-3 py-2 font-mono text-xs text-muted-foreground"
            />
          </label>
        </div>

        <label className="space-y-2 block">
          <span className="text-xs font-semibold text-foreground">Description</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={2}
            placeholder="Advises on market, operations, and implementation tradeoffs."
            className="w-full resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary"
          />
        </label>

        <label className="space-y-2 block">
          <span className="text-xs font-semibold text-foreground">System prompt</span>
          <textarea
            value={systemPrompt}
            onChange={(event) => setSystemPrompt(event.target.value)}
            rows={9}
            className="w-full resize-y rounded-lg border border-input bg-background px-3 py-2 font-mono text-xs leading-5 outline-none focus:border-primary"
          />
        </label>

        {error && (
          <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            {error}
          </p>
        )}

        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-lg border border-border px-4 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canSubmit || submitting}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Plus className="h-4 w-4" aria-hidden />
            {submitting ? 'Creating...' : 'Create persona'}
          </button>
        </div>
      </form>
    </section>
  )
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}
