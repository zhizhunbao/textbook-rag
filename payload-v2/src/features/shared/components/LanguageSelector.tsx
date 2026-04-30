'use client'

/**
 * LanguageSelector — Dropdown for switching the AI response language.
 *
 * V1: Chinese (default) and English. Other languages disabled with "Coming soon".
 * Stores selection in localStorage under 'consultrag_language'.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { ChevronDown, Languages } from 'lucide-react'

// ============================================================
// Types
// ============================================================

interface LanguageOption {
  code: string
  label: string
  enabled: boolean
}

const LANGUAGES: LanguageOption[] = [
  { code: 'zh', label: '中文', enabled: true },
  { code: 'en', label: 'English', enabled: true },
  { code: 'fr', label: 'Français', enabled: false },
  { code: 'es', label: 'Español', enabled: false },
]

const STORAGE_KEY = 'consultrag_language'
const DEFAULT_LANG = 'zh'

// ============================================================
// Component
// ============================================================

export default function LanguageSelector({
  className = '',
  value,
  onChange,
}: {
  className?: string
  value?: string | null
  onChange?: (lang: string) => void
}) {
  const [internalLang, setInternalLang] = useState(DEFAULT_LANG)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored && LANGUAGES.some((l) => l.code === stored && l.enabled)) {
        setInternalLang(stored)
      }
    } catch {
      // SSR or storage unavailable
    }
  }, [])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const activeLang = value ?? internalLang
  const active = LANGUAGES.find((l) => l.code === activeLang) ?? LANGUAGES[0]

  const handleSelect = useCallback(
    (code: string) => {
      setInternalLang(code)
      try {
        localStorage.setItem(STORAGE_KEY, code)
      } catch {
        // storage unavailable
      }
      onChange?.(code)
      setOpen(false)
    },
    [onChange],
  )

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-semibold text-foreground transition-colors hover:bg-accent"
        aria-label="Select response language"
      >
        <Languages className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        <span>{active.label}</span>
        <ChevronDown className="h-3 w-3 text-muted-foreground" aria-hidden />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 min-w-[140px] overflow-hidden rounded-lg border border-border bg-card shadow-lg">
          {LANGUAGES.map((opt) => (
            <button
              key={opt.code}
              type="button"
              disabled={!opt.enabled}
              onClick={() => opt.enabled && handleSelect(opt.code)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors ${
                opt.code === activeLang
                  ? 'bg-primary/10 font-bold text-primary'
                  : opt.enabled
                    ? 'text-foreground hover:bg-accent'
                    : 'cursor-not-allowed text-muted-foreground/50'
              }`}
            >
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
