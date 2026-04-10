'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n'
import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'

/**
 * LoginForm — 登录表单
 * 纯 Tailwind 语义类 + dark: 前缀，无 isDark / useTheme
 */
export default function LoginForm() {
  const { login, status } = useAuth()
  const { t } = useI18n()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'loggedIn') window.location.href = '/chat'
  }, [status])

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
      window.location.href = '/chat'
    } catch {
      setFormError(t.loginErrorFailed)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-5 relative overflow-hidden
        bg-[linear-gradient(135deg,#1d4ed8_0%,#2563eb_50%,#3b82f6_100%)]
        dark:bg-[linear-gradient(135deg,#0a1628_0%,#0d2240_40%,#1a3a5c_70%,#0d2240_100%)]
        transition-colors duration-500"
    >
      {/* Top-right controls */}
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <LanguageToggle className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm" />
        <ThemeToggle className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm" />
      </div>

      {/* Background decorations */}
      <div className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.1), transparent 50%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.05), transparent 50%)' }}
      />
      <div className="absolute top-[20%] left-[10%] w-20 h-20 rounded-full bg-white/8 animate-bounce opacity-70 pointer-events-none" />
      <div className="absolute top-[60%] right-[15%] w-14 h-14 rounded-full bg-white/6 animate-pulse opacity-70 pointer-events-none" />
      <div className="absolute bottom-[20%] left-[20%] w-28 h-28 rounded-full bg-white/4 animate-bounce opacity-50 pointer-events-none" style={{ animationDelay: '2s' }} />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[440px] backdrop-blur-xl rounded-3xl shadow-[0_32px_64px_rgba(0,0,0,0.3)] p-10
        bg-card/95 text-card-foreground border border-border/50
        animate-[slideUp_0.8s_cubic-bezier(0.34,1.56,0.64,1)]"
      >
        {/* Logo */}
        <div className="flex justify-center mb-5">
          <img src="/ottawa-logo.jpg" alt="City of Ottawa" className="h-14 w-14 rounded-xl object-contain" />
        </div>

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
              bg-[linear-gradient(135deg,#1d4ed8,#2563eb)] shadow-[0_8px_30px_rgba(37,99,235,0.3)]
              hover:translate-y-[-2px] hover:shadow-[0_12px_40px_rgba(37,99,235,0.4)]
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
        <div className="text-center mt-7 pt-5 border-t border-border">
          <span className="text-xs text-muted-foreground">
            {t.adminAccess}{' '}
            <a href="/admin/login" className="font-semibold text-primary no-underline hover:underline transition-colors">
              {t.goToAdminPanel}
            </a>
          </span>
        </div>
      </div>

    </div>
  )
}
