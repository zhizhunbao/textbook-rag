'use client'

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

  const handleStartChat = () => {
    router.push(user ? '/chat' : '/login')
  }

  return (
    <div className="min-h-screen overflow-x-hidden font-sans bg-background text-foreground">
      {/* Top-right controls */}
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <LanguageToggle className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm" />
        <ThemeToggle className="bg-white/20 text-white hover:bg-white/30 backdrop-blur-sm" />
      </div>

      {/* ── Hero Section ── */}
      <section
        className="relative min-h-[85vh] flex items-center overflow-hidden
          bg-[linear-gradient(135deg,#004890_0%,#0066cc_50%,#004890_100%)]
          dark:bg-[linear-gradient(135deg,#0a1628_0%,#0d2240_40%,#1a3a5c_70%,#0d2240_100%)]
          transition-colors duration-500"
      >
        {/* Decorative overlay */}
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.1) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.05) 0%, transparent 50%)' }} />
        <div className="absolute top-[20%] left-[10%] w-20 h-20 rounded-full bg-white/8 animate-bounce opacity-70" />
        <div className="absolute top-[60%] right-[15%] w-14 h-14 rounded-full bg-white/6 animate-pulse opacity-70" />
        <div className="absolute bottom-[20%] left-[20%] w-28 h-28 rounded-full bg-white/4 animate-bounce opacity-50" style={{ animationDelay: '2s' }} />

        <div className="container mx-auto px-6 text-center relative z-10">
          <div className="max-w-[900px] mx-auto">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold leading-[1.1] mb-6 text-white drop-shadow-sm">
              {t.heroTitle1}
              <span className="bg-clip-text text-transparent bg-[linear-gradient(45deg,#ffd700,#ffb000,#ff8c00)]">{t.heroTitleHighlight}</span>
            </h1>

            <p className="text-lg md:text-xl text-white/90 leading-relaxed mb-12 max-w-[700px] mx-auto">
              {t.heroSubtitle}
            </p>

            <div className="flex gap-5 justify-center flex-wrap mb-16">
              <button onClick={handleStartChat}
                className="inline-flex items-center gap-2.5 px-9 py-4 text-lg font-semibold rounded-xl
                  bg-white/95 text-brand-500 shadow-[0_8px_32px_rgba(255,255,255,0.2)]
                  hover:translate-y-[-3px] hover:shadow-[0_12px_40px_rgba(255,255,255,0.3)]
                  transition-all duration-300 backdrop-blur-sm cursor-pointer"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                {t.startAsking}
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
              </button>

              <Link href="/login"
                className="inline-flex items-center gap-2.5 px-9 py-4 text-lg font-semibold rounded-xl
                  border-2 border-white/40 text-white hover:bg-white/15 hover:border-white/70
                  hover:translate-y-[-2px] transition-all duration-300 backdrop-blur-sm"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" /></svg>
                {t.signIn}
              </Link>
            </div>

            {/* Stats – glassmorphism cards */}
            <div className="flex justify-center gap-6 flex-wrap px-5">
              {[
                { label: t.statMultiTextbook, icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15z" /><path d="M8 7h8" /><path d="M8 11h6" /></svg> },
                { label: t.statDeepTrace, icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="11" y1="8" x2="11" y2="14" /><line x1="8" y1="11" x2="14" y2="11" /></svg> },
                { label: t.statPageCitations, icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" /></svg> },
                { label: t.statMultiModels, icon: <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400"><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 9h.01" /><path d="M15 9h.01" /><path d="M9 15h.01" /><path d="M15 15h.01" /><path d="M9 12h6" /></svg> },
              ].map((stat) => (
                <div key={stat.label} className="text-center px-6 py-5 rounded-2xl bg-white/10 border border-white/20 backdrop-blur-sm hover:translate-y-[-5px] hover:bg-white/15 transition-all duration-300 min-w-[160px]">
                  <div className="flex justify-center mb-2">{stat.icon}</div>
                  <div className="text-xs text-white/90 font-medium">{stat.label}</div>
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
                <div className="w-[85px] h-[85px] rounded-2xl flex items-center justify-center mx-auto mb-6 text-white shadow-[0_8px_25px_rgba(0,72,144,0.3)] bg-[linear-gradient(135deg,#004890,#0066cc)]">
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
                <div className="w-[70px] h-[70px] text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-[0_8px_25px_rgba(0,72,144,0.3)] bg-[linear-gradient(135deg,#004890,#0066cc)]">
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
      <section
        className="py-28 relative overflow-hidden text-white
          bg-[linear-gradient(135deg,#004890_0%,#0066cc_50%,#004890_100%)]
          dark:bg-[linear-gradient(135deg,#0a1628_0%,#0d2240_40%,#1a3a5c_70%,#0d2240_100%)]
          transition-colors duration-500"
      >
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.1) 0%, transparent 50%), radial-gradient(circle at 70% 80%, rgba(255,255,255,0.05) 0%, transparent 50%)' }} />
        <div className="container mx-auto px-6">
          <div className="text-center max-w-[700px] mx-auto relative z-10">
            <h2 className="text-4xl font-bold mb-5 drop-shadow-sm">{t.ctaTitle}</h2>
            <p className="text-xl text-white/95 mb-12 leading-relaxed">{t.ctaSubtitle}</p>

            <div className="flex gap-5 justify-center flex-wrap">
              <button onClick={handleStartChat}
                className="inline-flex items-center gap-2.5 px-9 py-4 text-lg font-semibold rounded-xl
                  bg-white text-brand-500 shadow-[0_8px_32px_rgba(255,255,255,0.2)]
                  hover:translate-y-[-3px] hover:shadow-[0_15px_45px_rgba(255,255,255,0.3)]
                  transition-all duration-300 cursor-pointer"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                {t.startAsking}
              </button>
              <Link href="/login"
                className="inline-flex items-center gap-2.5 px-9 py-4 text-lg font-semibold rounded-xl
                  border-2 border-white/40 text-white hover:bg-white/15 hover:border-white/70
                  hover:translate-y-[-2px] transition-all duration-300 backdrop-blur-sm"
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
