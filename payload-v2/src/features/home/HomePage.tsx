'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useI18n } from '@/features/shared/i18n'
import { useAuth } from '@/features/shared/AuthProvider'
import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'

/**
 * HomePage — Fullscreen scroll-snap landing page
 * 3 sections: Hero → Features → Pricing
 * Each section fills 100vh and snaps on scroll
 */
export default function HomePage() {
  const { t } = useI18n()
  const { user } = useAuth()
  const router = useRouter()
  const containerRef = useRef<HTMLDivElement>(null)
  const [activeSection, setActiveSection] = useState(0)
  const isScrolling = useRef(false)

  // Real-time stats from Payload CMS collections
  const [stats, setStats] = useState({ books: 0, sessions: 0, queries: 0, models: 0 })

  useEffect(() => {
    async function fetchStats() {
      try {
        const [booksRes, sessionsRes, queriesRes, llmsRes] = await Promise.all([
          fetch('/api/books?limit=0&depth=0'),
          fetch('/api/chat-sessions?limit=0&depth=0'),
          fetch('/api/queries?limit=0&depth=0'),
          fetch('/api/llms?limit=0&depth=0'),
        ])
        const [books, sessions, queries, llms] = await Promise.all([
          booksRes.json(), sessionsRes.json(), queriesRes.json(), llmsRes.json(),
        ])
        setStats({
          books: books.totalDocs ?? 0,
          sessions: sessions.totalDocs ?? 0,
          queries: queries.totalDocs ?? 0,
          models: llms.totalDocs ?? 0,
        })
      } catch {
        // Keep default zeros on error
      }
    }
    fetchStats()
  }, [])

  const handleStartChat = () => {
    router.push(user ? '/chat' : '/login')
  }

  // ── Scroll-snap navigation via wheel ──
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()
    if (isScrolling.current) return

    const direction = e.deltaY > 0 ? 1 : -1
    setActiveSection((prev) => {
      const next = Math.max(0, Math.min(2, prev + direction))
      if (next !== prev) {
        isScrolling.current = true
        const sections = containerRef.current?.querySelectorAll('[data-section]')
        sections?.[next]?.scrollIntoView({ behavior: 'smooth' })
        setTimeout(() => { isScrolling.current = false }, 900)
      }
      return next
    })
  }, [])

  // ── Keyboard navigation ──
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'PageDown') {
      e.preventDefault()
      handleWheel({ deltaY: 100, preventDefault: () => { } } as WheelEvent)
    } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
      e.preventDefault()
      handleWheel({ deltaY: -100, preventDefault: () => { } } as WheelEvent)
    }
  }, [handleWheel])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.addEventListener('wheel', handleWheel, { passive: false })
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      el.removeEventListener('wheel', handleWheel)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleWheel, handleKeyDown])

  // ── Dot navigation ──
  const scrollTo = (idx: number) => {
    if (isScrolling.current) return
    isScrolling.current = true
    setActiveSection(idx)
    const sections = containerRef.current?.querySelectorAll('[data-section]')
    sections?.[idx]?.scrollIntoView({ behavior: 'smooth' })
    setTimeout(() => { isScrolling.current = false }, 900)
  }

  return (
    <div ref={containerRef} className="h-screen overflow-hidden font-sans bg-background text-foreground relative">

      {/* Top-left logo */}
      <div className="fixed top-4 left-5 z-50">
        <img
          src="/ottawa-logo.jpg"
          alt="City of Ottawa"
          className="h-14 md:h-16 rounded-lg"
        />
      </div>

      {/* Top-right controls */}
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <LanguageToggle className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm" />
        <ThemeToggle className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm" />
      </div>

      {/* ── Dot Navigation (right side) ── */}
      <nav className="fixed right-6 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-3
        bg-black/10 dark:bg-white/10 backdrop-blur-md rounded-full py-3 px-2">
        {['Hero', 'Features', 'Pricing'].map((label, i) => (
          <button
            key={label}
            onClick={() => scrollTo(i)}
            aria-label={`Go to ${label}`}
            className={`group relative w-3 h-3 rounded-full transition-all duration-300 cursor-pointer
              ${activeSection === i
                ? 'bg-[#004890] dark:bg-white scale-125 shadow-[0_0_8px_rgba(0,72,144,0.4)] dark:shadow-[0_0_8px_rgba(255,255,255,0.6)]'
                : 'bg-[#004890]/30 dark:bg-white/30 hover:bg-[#004890]/60 dark:hover:bg-white/60'
              }`}
          >
            <span className="absolute right-6 top-1/2 -translate-y-1/2 text-xs text-[#333] dark:text-white/80 font-medium
              opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              {label}
            </span>
          </button>
        ))}
      </nav>

      {/* ── Section 1: Hero ── (original styling preserved) */}
      <section
        data-section
        className="relative h-screen flex items-center overflow-hidden
          bg-[linear-gradient(135deg,#004890_0%,#0066cc_50%,#004890_100%)]
          dark:bg-[linear-gradient(135deg,#0a1628_0%,#0d2240_40%,#1a3a5c_70%,#0d2240_100%)]
          transition-colors duration-500 py-24 px-6"
      >
        {/* Decorative blur orbs */}
        <div className="absolute inset-0 z-0 opacity-10">
          <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-white rounded-full blur-[150px] -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-white rounded-full blur-[120px] translate-y-1/3 -translate-x-1/4" />
        </div>

        <div className="container mx-auto px-6 text-center relative z-10">
          <div className="max-w-[900px] mx-auto">

            <h1 className="text-5xl md:text-7xl font-extrabold leading-[1.1] mb-6 text-white tracking-tight">
              {t.heroTitle1}
              <span className="bg-clip-text text-transparent bg-[linear-gradient(45deg,#ffd700,#ffb000,#ff8c00)]">{t.heroTitleHighlight}</span>
            </h1>

            <p className="text-xl md:text-2xl text-white/90 leading-relaxed mb-10 max-w-3xl mx-auto font-medium">
              {t.heroSubtitle}
            </p>

            <div className="flex gap-5 justify-center mb-14">
              <button onClick={handleStartChat}
                className="inline-flex items-center gap-2.5 px-12 py-5 text-lg font-bold rounded-xl
                  bg-white text-[#004890] shadow-xl hover:shadow-2xl
                  hover:-translate-y-1 transition-all duration-300 hover:bg-white/95 cursor-pointer"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                {t.startAsking}
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
              </button>

              <Link href="/login"
                className="inline-flex items-center gap-2.5 px-9 py-5 text-lg font-bold rounded-xl
                  border-2 border-white/40 text-white hover:bg-white/15 hover:border-white/70
                  hover:-translate-y-1 transition-all duration-300 backdrop-blur-sm"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" /></svg>
                {t.signIn}
              </Link>
            </div>

            {/* Stats – real data from Payload CMS */}
            <div className="flex justify-center gap-6 max-w-5xl mx-auto px-4">
              {[
                { number: String(stats.books), label: t.statMultiTextbook },
                { number: String(stats.sessions), label: t.statDeepTrace },
                { number: String(stats.queries), label: t.statPageCitations },
                { number: String(stats.models), label: t.statMultiModels },
              ].map((stat) => (
                <div key={stat.label} className="flex-1 min-w-0 max-w-[220px] bg-white/10 backdrop-blur-md border border-white/10 p-6 rounded-2xl hover:bg-white/15 transition-all duration-300">
                  <div className="text-4xl font-black text-[#ffd700] mb-2">{stat.number}</div>
                  <div className="text-white/80 text-xs font-bold tracking-widest uppercase leading-normal">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════ */}
      {/* ── Section 2: Features ── */}
      {/* ═══════════════════════════════════════ */}
      <section
        data-section
        className="h-screen flex items-center justify-center relative
          bg-gradient-to-b from-[#f0f4f8] to-white
          dark:from-[#0a0e1a] dark:to-[#0d1117]"
      >
        <div className="w-full max-w-6xl mx-auto px-6">
          {/* Section header */}
          <div className="text-center mb-10">
            <p className="text-xs font-bold text-[#004890] dark:text-blue-400 uppercase tracking-[0.2em] mb-3">
              Why choose us
            </p>
            <h2 className="text-3xl md:text-5xl font-extrabold text-[#111] dark:text-white tracking-tight mb-2">
              {t.featuresTitle}
            </h2>
            <p className="text-base text-[#666] dark:text-[#888] max-w-2xl mx-auto">
              {t.featuresSubtitle}
            </p>
          </div>

          {/* 3 feature cards with bullet points */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
            {[
              {
                title: t.featureQATitle,
                desc: t.featureQADesc,
                icon: (
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                ),
                iconBg: 'bg-blue-500/10 text-blue-600 dark:bg-blue-500/15 dark:text-blue-400',
                bullets: ['Natural language queries across all documents', 'Multi-document cross-referencing', 'Source-grounded answers with citations'],
              },
              {
                title: t.featurePDFTitle,
                desc: t.featurePDFDesc,
                icon: (
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                ),
                iconBg: 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/15 dark:text-amber-400',
                bullets: ['Side-by-side document & chat view', 'Auto-highlighted source passages', 'Page-level navigation & zoom'],
              },
              {
                title: t.featureTraceTitle,
                desc: t.featureTraceDesc,
                icon: (
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                ),
                iconBg: 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400',
                bullets: ['Complete retrieval scoring breakdown', 'Chunk ranking & relevance visualization', 'Full query performance analytics'],
              },
            ].map((f) => (
              <div
                key={f.title}
                className="relative p-7 rounded-2xl
                  bg-white border border-[#e8ecf2] shadow-sm
                  dark:bg-[#151b2e]/50 dark:border-white/[0.06]
                  hover:shadow-lg hover:-translate-y-1
                  dark:hover:border-white/[0.12] dark:hover:bg-[#151b2e]/70
                  transition-all duration-300 group"
              >
                <div className={`w-12 h-12 rounded-xl ${f.iconBg} flex items-center justify-center mb-4
                  group-hover:scale-110 transition-transform duration-300`}>
                  {f.icon}
                </div>
                <h3 className="text-lg font-bold mb-2 text-[#111] dark:text-white">{f.title}</h3>
                <p className="text-sm text-[#666] dark:text-[#888] leading-relaxed mb-4">{f.desc}</p>
                <div className="border-t border-[#f0f0f0] dark:border-white/[0.06] pt-3">
                  <ul className="space-y-2">
                    {f.bullets.map((b) => (
                      <li key={b} className="flex items-start gap-2 text-xs text-[#555] dark:text-[#999]">
                        <svg className="w-3.5 h-3.5 text-[#004890] dark:text-blue-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>

          {/* Trust bar */}
          <div className="flex flex-wrap justify-center gap-6 md:gap-10 pt-5 border-t border-[#e8ecf2] dark:border-white/[0.06]">
            {[
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>, text: '256-bit Encryption' },
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>, text: '99.9% Uptime SLA' },
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>, text: 'Government-grade Security' },
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg>, text: 'Trusted by Researchers' },
            ].map((trust) => (
              <div key={trust.text} className="flex items-center gap-2 text-xs font-medium text-[#888] dark:text-[#666]">
                <span className="text-[#004890] dark:text-blue-400">{trust.icon}</span>
                {trust.text}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════ */}
      {/* ── Section 3: Pricing ── */}
      {/* ═══════════════════════════════════════ */}
      <section
        data-section
        id="pricing"
        className="h-screen flex items-center justify-center relative
          bg-white dark:bg-[#080b14]"
      >
        <div className="w-full max-w-4xl mx-auto px-6">
          {/* Section header */}
          <div className="text-center mb-10">
            <p className="text-xs font-bold text-[#004890] dark:text-blue-400 uppercase tracking-[0.2em] mb-3">
              Pricing
            </p>
            <h2 className="text-3xl md:text-5xl font-extrabold text-[#111] dark:text-white tracking-tight mb-3">
              {t.pricingTitle}
            </h2>
            <p className="text-base text-[#888] dark:text-[#666]">
              {t.pricingSubtitle}
            </p>
          </div>

          {/* 2 pricing cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto mb-8">
            {/* Free */}
            <div className="rounded-2xl p-8
              bg-[#f8f9fb] border border-[#e8ecf2]
              dark:bg-white/[0.03] dark:border-white/[0.06]
              hover:shadow-lg transition-all duration-300"
            >
              <div className="text-xs font-bold text-[#999] dark:text-[#666] uppercase tracking-widest mb-4">Free</div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-5xl font-extrabold text-[#111] dark:text-white">$0</span>
              </div>
              <p className="text-sm text-[#999] dark:text-[#666] mb-6">Free forever</p>

              <button
                onClick={() => router.push(user ? '/chat' : '/register')}
                className="w-full py-3 rounded-lg text-sm font-semibold
                  border border-[#ddd] dark:border-[#333]
                  text-[#111] dark:text-white bg-transparent
                  hover:bg-[#f0f0f0] dark:hover:bg-white/[0.05]
                  transition-colors cursor-pointer mb-6"
              >
                {t.pricingGetStarted}
              </button>

              <ul className="space-y-3">
                {['30 queries / day', '3 uploads / month', 'All consulting roles', 'Source citations'].map((text) => (
                  <li key={text} className="flex items-center gap-2.5 text-sm text-[#555] dark:text-[#999]">
                    <svg className="w-4 h-4 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    {text}
                  </li>
                ))}
              </ul>
            </div>

            {/* Pro — highlighted with gradient bar + glow */}
            <div className="rounded-2xl overflow-hidden relative
              bg-[#fafafa] dark:bg-white/[0.04]
              border-2 border-[#004890]/80 dark:border-[#004890]/60
              shadow-lg shadow-[#004890]/[0.06] dark:shadow-[#004890]/[0.12]
              hover:shadow-xl hover:shadow-[#004890]/[0.12] dark:hover:shadow-[#004890]/[0.2]
              transition-all duration-300"
            >
              {/* Gradient top accent bar */}
              <div className="h-1 bg-gradient-to-r from-[#004890] via-[#0066cc] to-[#ffd700]" />

              <div className="p-8">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-[10px] font-bold text-white bg-gradient-to-r from-[#004890] to-[#0066cc]
                    px-3 py-1 rounded-full uppercase tracking-wider shadow-sm">
                    {t.pricingPopular}
                  </span>
                </div>

                <div className="text-xs font-bold text-[#004890] dark:text-blue-400 uppercase tracking-widest mb-4">Pro</div>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-5xl font-extrabold text-[#111] dark:text-white">$19</span>
                  <span className="text-base text-[#999]">/mo</span>
                </div>
                <p className="text-sm text-[#999] dark:text-[#666] mb-6">For power users & teams</p>

                <button
                  onClick={() => router.push(user ? '/chat' : '/register')}
                  className="w-full py-3 rounded-lg text-sm font-bold
                    bg-gradient-to-r from-[#004890] to-[#0066cc] text-white
                    hover:from-[#003d7a] hover:to-[#0055aa]
                    transition-all cursor-pointer mb-6 shadow-md shadow-[#004890]/20"
                >
                  {t.pricingUpgrade}
                </button>

                <p className="text-[10px] font-bold text-[#999] dark:text-[#666] uppercase tracking-wider mb-3">Everything in Free, plus:</p>
                <ul className="space-y-3">
                  {['200 queries / day', '100 uploads / month', 'Priority generation', 'Advanced analytics', 'Priority support'].map((text) => (
                    <li key={text} className="flex items-center gap-2.5 text-sm text-[#555] dark:text-[#999]">
                      <svg className="w-4 h-4 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {text}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Trust signals row */}
          <div className="flex flex-wrap justify-center gap-5 md:gap-8 max-w-3xl mx-auto">
            {[
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><rect x="1" y="4" width="22" height="16" rx="2" /><line x1="1" y1="10" x2="23" y2="10" /></svg>, text: 'No credit card required' },
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" /></svg>, text: '14-day money-back' },
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>, text: 'Data encrypted at rest' },
              { icon: <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>, text: 'Cancel anytime' },
            ].map((trust) => (
              <div key={trust.text} className="flex items-center gap-2 text-xs font-medium text-[#999] dark:text-[#555]">
                <span className="text-[#004890]/70 dark:text-blue-400/60">{trust.icon}</span>
                {trust.text}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
