'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useI18n } from '@/features/shared/i18n'
import { useAuth } from '@/features/shared/AuthProvider'
import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'

/**
 * HomePage — 首页
 * 纯 Tailwind dark: 前缀 + 语义化类，无 isDark 判断
 */
export default function HomePage() {
  const { t } = useI18n()
  const { user } = useAuth()
  const router = useRouter()

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

  return (
    <div className="min-h-screen overflow-x-hidden font-sans bg-background text-foreground">
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

      {/* ── Hero Section ── */}
      <section
        className="relative min-h-screen flex items-center overflow-hidden
          bg-[linear-gradient(135deg,#004890_0%,#0066cc_50%,#004890_100%)]
          dark:bg-[linear-gradient(135deg,#0a1628_0%,#0d2240_40%,#1a3a5c_70%,#0d2240_100%)]
          transition-colors duration-500 py-24 px-6"
      >
        {/* Decorative blur orbs (reference: ottawa-genai-research-assistant) */}
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

      {/* ── Features Section ── */}
      <section className="py-28 relative bg-secondary dark:bg-background transition-colors">
        <div className="absolute top-0 left-0 right-0 h-px bg-border" />
        <div className="container mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold mb-5 relative inline-block text-foreground">
              {t.featuresTitle}
              <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-14 h-1 rounded-full bg-brand-500" />
            </h2>
            <p className="text-lg max-w-[600px] mx-auto mt-4 text-muted-foreground">{t.featuresSubtitle}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { title: t.featureQATitle, desc: t.featureQADesc, icon: <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10H12V2z" /><path d="M20 12a8 8 0 0 0-8-8v8h8z" /></svg> },
              { title: t.featurePDFTitle, desc: t.featurePDFDesc, icon: <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg> },
              { title: t.featureTraceTitle, desc: t.featureTraceDesc, icon: <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg> },
            ].map((f) => (
              <div key={f.title}
                className="group p-10 rounded-2xl text-center relative overflow-hidden
                  bg-card border border-border shadow-[0_10px_30px_rgba(0,0,0,0.08)] dark:shadow-none
                  hover:translate-y-[-6px] transition-all duration-300"
              >
                <div className="absolute top-0 left-0 right-0 h-[4px] scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left bg-brand-500" />
                <div className="w-[85px] h-[85px] rounded-2xl flex items-center justify-center mx-auto mb-6 text-white shadow-[0_8px_25px_rgba(0,72,144,0.3)] bg-[linear-gradient(135deg,#003d7a,#004890)]">
                  {f.icon}
                </div>
                <h3 className="text-xl font-bold mb-3 text-card-foreground">{f.title}</h3>
                <p className="leading-relaxed text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="py-28 bg-background transition-colors">
        <div className="container mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold mb-5 relative inline-block text-foreground">
              {t.howTitle}
              <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-14 h-1 rounded-full bg-brand-500" />
            </h2>
            <p className="text-lg max-w-[600px] mx-auto mt-4 text-muted-foreground">{t.howSubtitle}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {[
              { n: '1', title: t.howStep1Title, desc: t.howStep1Desc },
              { n: '2', title: t.howStep2Title, desc: t.howStep2Desc },
              { n: '3', title: t.howStep3Title, desc: t.howStep3Desc },
            ].map((step) => (
              <div key={step.n}
                className="text-center p-11 rounded-2xl
                  bg-card shadow-[0_8px_25px_rgba(0,0,0,0.06)] dark:shadow-none
                  dark:border dark:border-border
                  hover:translate-y-[-5px] transition-all duration-300"
              >
                <div className="w-[70px] h-[70px] text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-[0_8px_25px_rgba(0,72,144,0.3)] bg-[linear-gradient(135deg,#003d7a,#004890)]">
                  {step.n}
                </div>
                <h3 className="text-xl font-bold mb-3 text-card-foreground">{step.title}</h3>
                <p className="leading-relaxed text-sm text-muted-foreground">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section className="py-24 px-6 relative bg-background overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1/2 bg-muted/30 z-0" />

        <div className="max-w-6xl mx-auto rounded-[3rem] p-16 bg-[linear-gradient(135deg,#004890,#0066cc)] dark:bg-[linear-gradient(135deg,#0d2240,#1a3a5c)] relative z-10 overflow-hidden shadow-2xl shadow-blue-900/10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.1),transparent)] z-0" />

          <div className="relative z-10 text-center">
            <h2 className="text-3xl md:text-5xl font-extrabold text-white mb-6 tracking-tight">{t.ctaTitle}</h2>
            <p className="text-white/80 text-lg md:text-xl font-medium mb-12 max-w-2xl mx-auto leading-relaxed">{t.ctaSubtitle}</p>

            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
              <button onClick={handleStartChat}
                className="inline-flex items-center gap-2.5 w-full sm:w-auto px-12 py-5 text-lg font-bold rounded-2xl
                  bg-white text-brand-500 shadow-xl
                  hover:scale-105 hover:bg-white/95
                  transition-all duration-300 cursor-pointer"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                {t.startAsking}
              </button>
              <Link href="/login"
                className="inline-flex items-center gap-2.5 w-full sm:w-auto px-12 py-5 text-lg font-bold rounded-2xl
                  bg-transparent border-2 border-white/40 text-white
                  hover:bg-white/10 transition-all duration-300"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" /></svg>
                {t.signIn}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
