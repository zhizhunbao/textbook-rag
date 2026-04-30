'use client'

/**
 * CountrySelector — Dropdown for switching the active service country.
 *
 * V1: Only Canada is enabled. Other countries show "Coming soon" and are disabled.
 * Uses useCountry() context for state management.
 */

import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
import { useCountry } from '../CountryContext'

// ============================================================
// Country flag SVGs (inline to avoid emoji cross-platform issues)
// ============================================================

const FLAG_MAP: Record<string, string> = {
  ca: '🇨🇦',
  us: '🇺🇸',
  uk: '🇬🇧',
  au: '🇦🇺',
}

// ============================================================
// Component
// ============================================================

export default function CountrySelector({ className = '' }: { className?: string }) {
  const { country, setCountry, countries } = useCountry()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const active = countries.find((c) => c.code === country) ?? countries[0]

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-foreground transition-colors hover:bg-accent"
        aria-label="Select country"
      >
        <span className="text-sm leading-none">{FLAG_MAP[active.code] ?? ''}</span>
        <span className="hidden sm:inline">{active.label}</span>
        <ChevronDown className="h-3 w-3 text-muted-foreground" aria-hidden />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 min-w-[160px] overflow-hidden rounded-lg border border-border bg-card shadow-lg">
          {countries.map((opt) => (
            <button
              key={opt.code}
              type="button"
              disabled={!opt.enabled}
              onClick={() => {
                if (opt.enabled) {
                  setCountry(opt.code)
                  setOpen(false)
                }
              }}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors ${
                opt.code === country
                  ? 'bg-primary/10 font-bold text-primary'
                  : opt.enabled
                    ? 'text-foreground hover:bg-accent'
                    : 'cursor-not-allowed text-muted-foreground/50'
              }`}
            >
              <span className="text-sm leading-none">{FLAG_MAP[opt.code] ?? ''}</span>
              <span className="flex-1">{opt.label}</span>
              {!opt.enabled && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  Soon
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
