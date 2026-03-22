'use client'

import { AuthProvider } from './AuthProvider'
import React from 'react'

/**
 * Root Providers — 组合所有 client-side Provider
 * 在 (frontend)/layout.tsx 中使用
 */
export const Providers: React.FC<{
  children: React.ReactNode
}> = ({ children }) => {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  )
}
