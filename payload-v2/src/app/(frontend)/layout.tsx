import type { Metadata } from 'next'
import React from 'react'

import { Providers } from '@/features/shared/Providers'
import AppLayout from '@/features/layout/AppLayout'
import AuthGuard from '@/features/layout/AuthGuard'
import { ChatHistoryProvider } from '@/features/chat/history/ChatHistoryContext'

import 'katex/dist/katex.min.css'
import './globals.css'

/**
 * (frontend) root layout
 * - <html>/<body> + dark-mode FOUC prevention
 * - Providers (Auth, theme, etc.)
 * - AppLayout (sidebar + header) + ChatHistoryProvider
 * - AuthGuard (login/onboarding route guard)
 */
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <link href="/favicon.ico" rel="icon" sizes="32x32" />
        {/* Blocking script: set dark class BEFORE first paint to prevent FOUC */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var t = localStorage.getItem('theme');
                  var isDark = t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches);
                  if (isDark) document.documentElement.classList.add('dark');
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="h-full">
        <Providers>
          <ChatHistoryProvider>
            <AppLayout>
              <AuthGuard>
                {children}
              </AuthGuard>
            </AppLayout>
          </ChatHistoryProvider>
        </Providers>
      </body>
    </html>
  )
}

export const metadata: Metadata = {
  title: 'EcDev Research',
  description: 'AI-powered research assistant for City of Ottawa economic reports',
}
