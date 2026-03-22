'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'

/**
 * LoginForm — 登录表单组件（auth feature 模块）
 * 使用 Payload REST API 认证，Tailwind 统一风格
 */
export default function LoginForm() {
  const { login, status } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'loggedIn') window.location.href = '/ask'
  }, [status])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setFormError('Please enter both email and password')
      return
    }
    try {
      setFormError(null)
      setIsLoading(true)
      await login({ email: email.trim(), password })
      window.location.href = '/ask'
    } catch {
      setFormError('Login failed. Please check your credentials.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-950 via-surface-900 to-surface-800 p-5 relative overflow-hidden">
      {/* Floating shapes */}
      <div className="absolute top-[20%] left-[10%] w-20 h-20 rounded-full bg-gradient-to-tr from-brand-400/15 to-accent-500/10 animate-bounce opacity-70 pointer-events-none" />
      <div className="absolute top-[60%] right-[15%] w-14 h-14 rounded-full bg-gradient-to-tr from-brand-400/10 to-brand-500/15 animate-pulse opacity-70 pointer-events-none" />
      <div className="absolute bottom-[20%] left-[20%] w-28 h-28 rounded-full bg-gradient-to-tr from-accent-500/8 to-brand-400/6 animate-bounce opacity-50 pointer-events-none" style={{ animationDelay: '2s' }} />
      <div className="absolute top-[30%] right-[30%] w-10 h-10 rounded-full bg-gradient-to-tr from-brand-400/12 to-accent-500/10 animate-pulse opacity-70 pointer-events-none" style={{ animationDelay: '1s' }} />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[440px] bg-surface-900/95 backdrop-blur-xl rounded-3xl shadow-[0_32px_64px_rgba(0,0,0,0.4),0_0_0_1px_rgba(255,255,255,0.06)] p-10 animate-[slideUp_0.8s_cubic-bezier(0.34,1.56,0.64,1)]">
        {/* Logo */}
        <div className="flex justify-center mb-5">
          <span className="text-5xl animate-pulse" style={{ animationDuration: '3s' }}>📚</span>
        </div>

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="flex flex-col gap-2">
            <span className="text-3xl font-extrabold bg-gradient-to-r from-brand-400 to-accent-400 bg-clip-text text-transparent">Textbook RAG</span>
            <span className="text-sm text-slate-400 font-normal">Sign in to access your AI-powered textbook assistant</span>
          </h1>
        </div>

        {/* Error */}
        {formError && (
          <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 text-red-300 px-4 py-3.5 rounded-xl text-sm font-medium mb-4 animate-[fadeIn_0.3s_ease]">
            <svg className="shrink-0 text-red-400" width="20" height="20" viewBox="0 0 24 24" fill="none">
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
          <div className="flex flex-col group">
            <label className="text-slate-300 font-semibold text-sm mb-2.5 flex items-center gap-2">
              <svg className="text-slate-500 group-focus-within:text-brand-400 transition-colors" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              Email
            </label>
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com" disabled={isLoading} autoComplete="email" required
              className="px-4 py-3.5 border-2 border-white/8 rounded-xl text-sm bg-white/[0.04] text-slate-100 placeholder:text-slate-600 outline-none transition-all duration-300 focus:border-brand-400 focus:bg-white/[0.06] focus:shadow-[0_0_0_4px_rgba(96,165,250,0.1)] disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Password */}
          <div className="flex flex-col group">
            <label className="text-slate-300 font-semibold text-sm mb-2.5 flex items-center gap-2">
              <svg className="text-slate-500 group-focus-within:text-brand-400 transition-colors" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'} value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password"
                disabled={isLoading} autoComplete="current-password" required
                className="w-full px-4 py-3.5 pr-12 border-2 border-white/8 rounded-xl text-sm bg-white/[0.04] text-slate-100 placeholder:text-slate-600 outline-none transition-all duration-300 focus:border-brand-400 focus:bg-white/[0.06] focus:shadow-[0_0_0_4px_rgba(96,165,250,0.1)] disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="button" tabIndex={-1}
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-slate-500 hover:text-brand-400 hover:bg-brand-400/10 transition-all"
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
            className="mt-1 flex items-center justify-center gap-2.5 px-6 py-4 rounded-xl text-base font-semibold text-white bg-gradient-to-r from-brand-500 via-brand-600 to-brand-700 shadow-[0_8px_30px_rgba(59,130,246,0.3)] hover:translate-y-[-2px] hover:shadow-[0_12px_40px_rgba(59,130,246,0.4)] active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed disabled:translate-y-0 transition-all duration-300 relative overflow-hidden"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Signing in...
              </>
            ) : (
              <>
                <svg className="shrink-0" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                  <polyline points="10 17 15 12 10 7" />
                  <line x1="15" y1="12" x2="3" y2="12" />
                </svg>
                Sign In
              </>
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="text-center mt-7 pt-5 border-t border-white/[0.06]">
          <span className="text-slate-500 text-xs">
            Admin access?{' '}
            <a href="/admin/login" className="text-brand-400 hover:text-brand-300 font-semibold no-underline transition-colors">
              Go to Admin Panel →
            </a>
          </span>
        </div>
      </div>

      <style jsx>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(40px) scale(0.9); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>
    </div>
  )
}
