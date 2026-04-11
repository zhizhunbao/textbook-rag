'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { type Locale, type Messages, messages } from './messages'

/* ── Context shape ── */
interface I18nContextValue {
  locale: Locale
  t: Messages
  setLocale: (l: Locale) => void
  toggleLocale: () => void
}

const I18nContext = createContext<I18nContextValue | null>(null)

/* ── Persistence key ── */
const STORAGE_KEY = 'textbook-rag-locale'

/**
 * I18nProvider — 语言上下文
 *
 * SSR-safe: always starts with 'en' to match server render,
 * then hydrates from localStorage/browser language in useEffect.
 */
export function I18nProvider({ children }: { children: React.ReactNode }) {
  // Always start with 'en' for SSR consistency
  const [locale, setLocaleState] = useState<Locale>('en')

  // Hydrate from localStorage / browser language after mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Locale | null
    if (saved === 'en' || saved === 'zh') {
      setLocaleState(saved)
    } else if (navigator.language.startsWith('zh')) {
      setLocaleState('zh')
    }
  }, [])

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
    localStorage.setItem(STORAGE_KEY, l)
  }, [])

  const toggleLocale = useCallback(() => {
    setLocaleState((prev) => {
      const next = prev === 'en' ? 'zh' : 'en'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  // Sync html lang attribute
  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const value: I18nContextValue = {
    locale,
    t: messages[locale],
    setLocale,
    toggleLocale,
  }

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  )
}

/**
 * useI18n — 获取当前语言和翻译文案
 */
export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within <I18nProvider>')
  return ctx
}
