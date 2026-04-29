'use client'

import React, { useState, useEffect } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { ArrowRight, SearchCheck } from 'lucide-react'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n'
import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'

/**
 * LoginForm — 登录表单
 * 纯 Tailwind 语义类 + dark: 前缀，无 isDark / useTheme
 */
export default function LoginForm() {
  const { login, status, user } = useAuth()
  const { t } = useI18n()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'loggedIn' && user) {
      if (user.role === 'admin') { window.location.href = '/chat'; return }
      window.location.href = user.isOnboarded ? '/chat' : '/onboarding'
    }
  }, [status, user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setFormError(t.loginErrorEmpty)
      return
    }
    try {
      setFormError(null)
      setIsLoading(true)
      await login({ email: email.trim(), password })
      // Redirect is handled by the useEffect above after user state updates
    } catch {
      setFormError(t.loginErrorFailed)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <Image
        src="/consultrag-hero.png"
        alt="ConsultRAG workspace background"
        fill
        priority
        sizes="100vw"
        className="object-cover"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(2,6,23,0.94)_0%,rgba(15,23,42,0.78)_48%,rgba(15,23,42,0.48)_100%)]" />

      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-black/25 backdrop-blur-md">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-3 text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15">
              <SearchCheck className="h-5 w-5" aria-hidden />
            </span>
            <span className="text-sm font-bold uppercase tracking-widest">ConsultRAG</span>
          </Link>

          <div className="flex items-center gap-3">
            <LanguageToggle className="border-white/15 bg-white/10 text-white hover:bg-white/20" />
            <ThemeToggle className="border-white/15 bg-white/10 text-white hover:bg-white/20" />
            <Link
              href="/register"
              className="hidden items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-950 hover:bg-white/90 sm:inline-flex"
            >
              Start free
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </nav>
      </header>

      <section className="relative z-10 mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-5 pb-10 pt-28 md:px-8 lg:grid-cols-[1fr_440px]">
        <div className="hidden max-w-2xl text-white lg:block">
          <p className="mb-5 inline-flex items-center rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-xs font-bold uppercase tracking-widest text-blue-100 backdrop-blur">
            Welcome back
          </p>
          <h1 className="text-5xl font-extrabold leading-tight tracking-normal">
            Return to cited answers, private files, and expert roles.
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-100">
            Continue research sessions with guarded Engine access, model routing, and reviewable source trails.
          </p>
        </div>

        {/* Login card */}
        <div className="w-full rounded-lg border border-border/70 bg-card/95 p-8 text-card-foreground shadow-[0_24px_70px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-10">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="flex flex-col gap-2">
            <span className="text-3xl font-extrabold text-primary">{t.loginHeading}</span>
            <span className="text-sm font-normal text-muted-foreground">{t.loginSubheading}</span>
          </h1>
        </div>

        {/* Error */}
        {formError && (
          <div className="flex items-center gap-2.5 bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3.5 rounded-xl text-sm font-medium mb-4">
            <svg className="shrink-0" width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <line x1="15" y1="9" x2="9" y2="15" stroke="currentColor" strokeWidth="2"/>
              <line x1="9" y1="9" x2="15" y2="15" stroke="currentColor" strokeWidth="2"/>
            </svg>
            {formError}
          </div>
        )}

        {/* Form */}
        <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
          {/* Email */}
          <div className="flex flex-col">
            <label className="font-semibold text-sm mb-2.5 flex items-center gap-2 text-foreground">
              <svg className="text-muted-foreground" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              {t.emailLabel}
            </label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder={t.emailPlaceholder} disabled={isLoading} autoComplete="email" required
              className="px-4 py-3.5 border-2 border-input bg-background rounded-xl text-sm text-foreground
                placeholder:text-muted-foreground outline-none transition-all duration-300
                focus:border-primary focus:shadow-[0_0_0_4px_rgba(37,99,235,0.15)]
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Password */}
          <div className="flex flex-col">
            <label className="font-semibold text-sm mb-2.5 flex items-center gap-2 text-foreground">
              <svg className="text-muted-foreground" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              {t.passwordLabel}
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'} value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder={t.passwordPlaceholder}
                disabled={isLoading} autoComplete="current-password" required
                className="w-full px-4 py-3.5 pr-12 border-2 border-input bg-background rounded-xl text-sm text-foreground
                  placeholder:text-muted-foreground outline-none transition-all duration-300
                  focus:border-primary focus:shadow-[0_0_0_4px_rgba(37,99,235,0.15)]
                  disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="button" tabIndex={-1}
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-muted-foreground hover:bg-primary/10 transition-all"
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
                )}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit" disabled={isLoading}
            className="mt-1 flex items-center justify-center gap-2.5 px-6 py-4 rounded-xl text-base font-semibold text-white
              bg-[linear-gradient(135deg,#003d7a,#004890)] shadow-[0_8px_30px_rgba(0,72,144,0.3)]
              hover:translate-y-[-2px] hover:shadow-[0_12px_40px_rgba(0,72,144,0.4)]
              active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed disabled:translate-y-0
              transition-all duration-300 relative overflow-hidden"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {t.signingIn}
              </>
            ) : (
              <>
                <svg className="shrink-0" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                  <polyline points="10 17 15 12 10 7" />
                  <line x1="15" y1="12" x2="3" y2="12" />
                </svg>
                {t.signIn}
              </>
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="text-center mt-7 pt-5 border-t border-border space-y-2">
          <div>
            <span className="text-sm text-muted-foreground">
              {t.loginNoAccount}{' '}
              <a href="/register" className="font-semibold text-primary no-underline hover:underline transition-colors">
                {t.loginGoToRegister}
              </a>
            </span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">
              {t.adminAccess}{' '}
              <a href="/admin/login" className="font-semibold text-primary no-underline hover:underline transition-colors">
                {t.goToAdminPanel}
              </a>
            </span>
          </div>
        </div>
        </div>
      </section>
    </main>
  )
}
