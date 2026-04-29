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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Product',
              name: 'ConsultRAG',
              description: 'AI-powered multi-role consulting with private document RAG and source tracing.',
              brand: { '@type': 'Brand', name: 'ConsultRAG' },
              offers: {
                '@type': 'Offer',
                price: '19',
                priceCurrency: 'USD',
                availability: 'https://schema.org/InStock',
                url: 'https://consultrag.com/pricing',
              },
            }),
          }}
        />
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
  title: {
    default: 'ConsultRAG — AI Consulting & RAG Assistant',
    template: '%s | ConsultRAG',
  },
  description: 'AI-powered multi-role consulting with private document RAG and deep source tracing.',
  openGraph: {
    title: 'ConsultRAG — AI Consulting & RAG Assistant',
    description: 'AI-powered multi-role consulting with private document RAG and deep source tracing.',
    type: 'website',
    locale: 'en_US',
    url: 'https://consultrag.com',
    siteName: 'ConsultRAG',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ConsultRAG — AI Consulting & RAG Assistant',
    description: 'AI-powered multi-role consulting with private document RAG and deep source tracing.',
  },
}
