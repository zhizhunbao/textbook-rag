'use client'

import { AuthProvider } from './AuthProvider'
import { CountryProvider } from './CountryContext'
import { I18nProvider } from './i18n'
import { ThemeProvider } from './theme'
import React from 'react'

/**
 * Root Providers — 组合所有 client-side Provider
 * 在 (frontend)/layout.tsx 中使用
 * 顺序：Theme → I18n → Auth → Country
 */
export const Providers: React.FC<{
  children: React.ReactNode
}> = ({ children }) => {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AuthProvider>
          <CountryProvider>
            {children}
          </CountryProvider>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}

