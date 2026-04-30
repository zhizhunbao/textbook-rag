'use client'

/**
 * CountryContext — Global country selection state for multi-country routing.
 *
 * Provides useCountry() hook for components to read/write the active country.
 * Persists selection to localStorage under 'consultrag_country'.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

// ============================================================
// Types
// ============================================================

export interface CountryOption {
  code: string
  label: string
  enabled: boolean
}

export const SUPPORTED_COUNTRIES: CountryOption[] = [
  { code: 'ca', label: 'Canada', enabled: true },
  { code: 'us', label: 'USA', enabled: false },
  { code: 'uk', label: 'UK', enabled: false },
  { code: 'au', label: 'Australia', enabled: false },
]

const STORAGE_KEY = 'consultrag_country'
const DEFAULT_COUNTRY = 'ca'

// ============================================================
// Context
// ============================================================

interface CountryContextValue {
  country: string
  setCountry: (code: string) => void
  countries: CountryOption[]
}

const CountryContext = createContext<CountryContextValue | null>(null)

// ============================================================
// Provider
// ============================================================

export const CountryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [country, setCountryState] = useState(DEFAULT_COUNTRY)

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored && SUPPORTED_COUNTRIES.some((c) => c.code === stored && c.enabled)) {
        setCountryState(stored)
      }
    } catch {
      // SSR or storage unavailable
    }
  }, [])

  const setCountry = useCallback((code: string) => {
    const option = SUPPORTED_COUNTRIES.find((c) => c.code === code)
    if (!option?.enabled) return
    setCountryState(code)
    try {
      localStorage.setItem(STORAGE_KEY, code)
    } catch {
      // storage unavailable
    }
  }, [])

  return (
    <CountryContext.Provider value={{ country, setCountry, countries: SUPPORTED_COUNTRIES }}>
      {children}
    </CountryContext.Provider>
  )
}

// ============================================================
// Hook
// ============================================================

export function useCountry(): CountryContextValue {
  const ctx = useContext(CountryContext)
  if (!ctx) throw new Error('useCountry must be used within CountryProvider')
  return ctx
}
