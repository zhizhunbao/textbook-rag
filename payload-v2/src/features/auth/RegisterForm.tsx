'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n'
import PublicShell from '@/features/layout/PublicShell'

/**
 * RegisterForm — Self-service registration form (GO-MU-01).
 *
 * Mirrors LoginForm design language. Fields: email, password, confirmPassword, displayName.
 * On success: auto-login → redirect to /onboarding.
 */
export default function RegisterForm() {
  const { login, status, user } = useAuth()
  const { t } = useI18n()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // After auto-login, redirect to onboarding
  useEffect(() => {
    if (status === 'loggedIn' && user) {
      window.location.href = user.isOnboarded ? '/chat' : '/onboarding'
    }
  }, [status, user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    // Validation
    if (!email.trim() || !password.trim()) {
      setFormError(t.registerErrorEmpty)
      return
    }
    if (password.length < 6) {
      setFormError(t.registerErrorShortPassword)
      return
    }
    if (password !== confirmPassword) {
      setFormError(t.registerErrorPasswordMismatch)
      return
    }
    if (!acceptedTerms) {
      setFormError('Please agree to the Terms of Service and Privacy Policy.')
      return
    }

    try {
      setIsLoading(true)

      // Step 1: Create user via Payload REST API
      const createRes = await fetch('/api/users', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password,
          displayName: displayName.trim() || undefined,
        }),
      })

      if (!createRes.ok) {
        const err = await createRes.json().catch(() => null)
        const msg = err?.errors?.[0]?.message || ''
        if (msg.includes('unique') || msg.includes('already')) {
          setFormError(t.registerErrorEmailExists)
        } else {
          setFormError(msg || t.registerErrorFailed)
        }
        return
      }

      // Step 2: Auto-login with the new credentials
      await login({ email: email.trim(), password })
      // Redirect handled by useEffect above
    } catch {
      setFormError(t.registerErrorFailed)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <PublicShell page="register">
      <section className="relative z-10 mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-5 pb-10 pt-20 md:px-8 lg:grid-cols-[1fr_460px]">
        <div className="hidden max-w-2xl text-white lg:block">
          <p className="mb-5 inline-flex items-center rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-xs font-bold uppercase tracking-widest text-blue-100 backdrop-blur">
            Start free
          </p>
          <h1 className="text-5xl font-extrabold leading-tight tracking-normal">
            Create a private consulting workspace in minutes.
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-100">
            Upload documents, choose expert roles, and inspect every answer with citations and quality signals.
          </p>
        </div>

        {/* Register card */}
        <div className="w-full rounded-lg border border-border/70 bg-card/95 p-7 text-card-foreground shadow-[0_24px_70px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-9">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="flex flex-col gap-2">
            <span className="text-3xl font-extrabold text-primary">{t.registerHeading}</span>
            <span className="text-sm font-normal text-muted-foreground">{t.registerSubheading}</span>
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
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          {/* Display Name (optional) */}
          <div className="flex flex-col">
            <label className="font-semibold text-sm mb-2 flex items-center gap-2 text-foreground">
              <svg className="text-muted-foreground" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              {t.registerDisplayNameLabel}
            </label>
            <input
              type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t.registerDisplayNamePlaceholder} disabled={isLoading} autoComplete="name"
              className="px-4 py-3 border-2 border-input bg-background rounded-xl text-sm text-foreground
                placeholder:text-muted-foreground outline-none transition-all duration-300
                focus:border-primary focus:shadow-[0_0_0_4px_rgba(37,99,235,0.15)]
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Email */}
          <div className="flex flex-col">
            <label className="font-semibold text-sm mb-2 flex items-center gap-2 text-foreground">
              <svg className="text-muted-foreground" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              {t.emailLabel}
            </label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder={t.emailPlaceholder} disabled={isLoading} autoComplete="email" required
              className="px-4 py-3 border-2 border-input bg-background rounded-xl text-sm text-foreground
                placeholder:text-muted-foreground outline-none transition-all duration-300
                focus:border-primary focus:shadow-[0_0_0_4px_rgba(37,99,235,0.15)]
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Password */}
          <div className="flex flex-col">
            <label className="font-semibold text-sm mb-2 flex items-center gap-2 text-foreground">
              <svg className="text-muted-foreground" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              {t.passwordLabel}
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'} value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder={t.registerPasswordPlaceholder}
                disabled={isLoading} autoComplete="new-password" required minLength={6}
                className="w-full px-4 py-3 pr-12 border-2 border-input bg-background rounded-xl text-sm text-foreground
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

          {/* Confirm Password */}
          <div className="flex flex-col">
            <label className="font-semibold text-sm mb-2 flex items-center gap-2 text-foreground">
              <svg className="text-muted-foreground" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              {t.registerConfirmPasswordLabel}
            </label>
            <input
              type="password" value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t.registerConfirmPasswordPlaceholder}
              disabled={isLoading} autoComplete="new-password" required
              className="px-4 py-3 border-2 border-input bg-background rounded-xl text-sm text-foreground
                placeholder:text-muted-foreground outline-none transition-all duration-300
                focus:border-primary focus:shadow-[0_0_0_4px_rgba(37,99,235,0.15)]
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Terms agreement */}
          <label className="flex items-start gap-3 rounded-xl border border-border bg-background/70 p-3 text-xs leading-relaxed text-muted-foreground">
            <input
              type="checkbox"
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
              disabled={isLoading}
              className="mt-0.5 h-4 w-4 rounded border-input accent-primary disabled:cursor-not-allowed disabled:opacity-50"
              required
            />
            <span>
              I agree to the{' '}
              <Link href="/terms" className="font-semibold text-primary hover:underline">
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link href="/privacy" className="font-semibold text-primary hover:underline">
                Privacy Policy
              </Link>
              .
            </span>
          </label>

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
                {t.registerCreating}
              </>
            ) : (
              <>
                <svg className="shrink-0" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="8.5" cy="7" r="4" />
                  <line x1="20" y1="8" x2="20" y2="14" />
                  <line x1="23" y1="11" x2="17" y2="11" />
                </svg>
                {t.registerSubmit}
              </>
            )}
          </button>
        </form>

        {/* Footer — link to login */}
        <div className="text-center mt-7 pt-5 border-t border-border">
          <span className="text-sm text-muted-foreground">
            {t.registerHasAccount}{' '}
            <a href="/login" className="font-semibold text-primary no-underline hover:underline transition-colors">
              {t.registerGoToLogin}
            </a>
          </span>
        </div>
        </div>
      </section>
    </PublicShell>
  )
}
