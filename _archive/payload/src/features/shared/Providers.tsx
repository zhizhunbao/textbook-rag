'use client'

import { AuthProvider } from './AuthProvider'
import { I18nProvider } from './i18n'
import { ThemeProvider } from './theme'
import React from 'react'

/**
 * Root Providers — 组合所有 client-side Provider
 * 在 (frontend)/layout.tsx 中使用
 * 顺序：Theme → I18n → Auth
 */
export const Providers: React.FC<{
  children: React.ReactNode
}> = ({ children }) => {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AuthProvider>
          {children}
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
