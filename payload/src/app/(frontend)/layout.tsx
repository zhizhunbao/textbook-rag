import type { Metadata } from 'next'
import React from 'react'

import { Providers } from '@/features/shared/Providers'

import './globals.css'

/**
 * (app) layout — Payload 官方模板风格
 * 使用 Providers 包裹所有 client-side 状态（Auth 等）
 * 不做 SSR auth guard — 由各页面组件自行检查 auth 状态
 */
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <link href="/favicon.ico" rel="icon" sizes="32x32" />
      </head>
      <body className="h-full bg-surface-950 text-slate-100">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}

export const metadata: Metadata = {
  title: 'Textbook RAG',
  description: 'AI-powered textbook Q&A with deep source tracing',
}
