'use client'

import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { useAuth } from '@/features/shared/AuthProvider'
import CountrySelector from '@/features/shared/components/CountrySelector'
import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'

/**
 * PublicNav — shared navbar for all public pages (landing, login, register).
 *
 * The only variation is the right-side CTA button:
 *   - landing → Sign up + Log in
 *   - login   → Start free (→ /register)
 *   - register → Log in (→ /login)
 */
export default function PublicNav({ page = 'landing' }: { page?: 'landing' | 'login' | 'register' }) {
  const { user } = useAuth()
  const primaryHref = user ? '/consulting' : '/register'

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-white/85 shadow-sm shadow-slate-200/50 backdrop-blur-xl dark:border-white/10 dark:bg-black/30 dark:shadow-none">
      <nav className="flex w-full items-center justify-between px-5 py-4 md:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 text-foreground">
          <img src="/consultrag-logo.png" alt="ConsultRAG" className="h-9 w-9 rounded-lg object-contain" />
          <span className="text-sm font-bold uppercase tracking-widest">ConsultRAG</span>
        </Link>

        {/* Right controls */}
        <div className="flex items-center gap-3">
          <CountrySelector className="[&_button]:border-border [&_button]:bg-muted [&_button]:text-foreground [&_button]:hover:bg-accent dark:[&_button]:border-white/15 dark:[&_button]:bg-white/10 dark:[&_button]:text-white dark:[&_button]:hover:bg-white/20" />
          <LanguageToggle className="border-border bg-muted text-foreground hover:bg-accent dark:border-white/15 dark:bg-white/10 dark:text-white dark:hover:bg-white/20" />
          <ThemeToggle className="border-border bg-muted text-foreground hover:bg-accent dark:border-white/15 dark:bg-white/10 dark:text-white dark:hover:bg-white/20" />

          {/* CTA — varies by page */}
          {page === 'landing' && (
            <>
              <Link
                href={primaryHref}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 dark:bg-white dark:text-slate-950 dark:hover:bg-white/90"
              >
                Sign up
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
              {!user && (
                <Link
                  href="/login"
                  className="inline-flex items-center rounded-lg border border-border px-3 py-1.5 text-xs font-bold text-foreground hover:bg-muted dark:border-white/20 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
                >
                  Log in
                </Link>
              )}
            </>
          )}
          {page === 'login' && (
            <Link
              href="/register"
              className="hidden items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 dark:bg-white dark:text-slate-950 dark:hover:bg-white/90 sm:inline-flex"
            >
              Start free
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          )}
          {page === 'register' && (
            <Link
              href="/login"
              className="hidden items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 dark:bg-white dark:text-slate-950 dark:hover:bg-white/90 sm:inline-flex"
            >
              Log in
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          )}
        </div>
      </nav>
    </header>
  )
}
