'use client'

import Link from 'next/link'

/**
 * HomePage — 首页组件（feature 模块）
 * 改编自 RAG-Project 首页，使用 Tailwind 统一风格
 */
export default function HomePage() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-surface-950 text-slate-100 font-sans">
      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-surface-950 via-surface-900 to-surface-800" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(96,165,250,0.08),transparent_50%),radial-gradient(circle_at_80%_80%,rgba(139,92,246,0.06),transparent_50%)]" />

        {/* Floating shapes */}
        <div className="absolute top-[20%] left-[10%] w-20 h-20 rounded-full bg-gradient-to-tr from-brand-400/15 to-accent-500/10 animate-bounce opacity-70" />
        <div className="absolute top-[60%] right-[15%] w-14 h-14 rounded-full bg-gradient-to-tr from-brand-400/10 to-brand-500/15 animate-pulse opacity-70" />
        <div className="absolute bottom-[20%] left-[20%] w-28 h-28 rounded-full bg-gradient-to-tr from-accent-500/8 to-brand-400/6 animate-bounce opacity-50" style={{ animationDelay: '2s' }} />

        <div className="container mx-auto px-6 text-center relative z-10">
          <div className="max-w-[900px] mx-auto animate-[fadeInUp_0.8s_ease-out]">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold leading-[1.1] mb-6">
              AI-Powered
              <span className="bg-gradient-to-r from-brand-400 via-accent-400 to-brand-500 bg-clip-text text-transparent"> Textbook Assistant</span>
            </h1>

            <p className="text-lg md:text-xl text-slate-400 leading-relaxed mb-12 max-w-[700px] mx-auto">
              Ask questions about your textbooks and get instant, accurate answers
              with deep source tracing and page-level citations.
            </p>

            <div className="flex gap-5 justify-center flex-wrap mb-16">
              <Link
                href="/ask"
                className="inline-flex items-center gap-2.5 px-9 py-4.5 text-lg font-semibold rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-[0_8px_32px_rgba(59,130,246,0.3)] hover:translate-y-[-3px] hover:shadow-[0_12px_40px_rgba(59,130,246,0.4)] transition-all duration-300"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                Start Asking
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
              </Link>

              <Link
                href="/login"
                className="inline-flex items-center gap-2.5 px-9 py-4.5 text-lg font-semibold rounded-xl border-2 border-slate-500/30 text-slate-400 hover:bg-white/5 hover:border-slate-400/50 hover:text-white hover:translate-y-[-2px] transition-all duration-300"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" /></svg>
                Sign In
              </Link>
            </div>

            {/* Stats */}
            <div className="flex justify-center gap-6 flex-wrap px-5">
              {[
                { icon: '📚', label: 'Multi-Textbook Support' },
                { icon: '🔍', label: 'Deep Source Tracing' },
                { icon: '📄', label: 'Page-Level Citations' },
                { icon: '🤖', label: 'Multiple AI Models' },
              ].map((s) => (
                <div key={s.label} className="text-center px-6 py-5 rounded-2xl bg-white/[0.04] border border-white/[0.06] backdrop-blur-sm hover:translate-y-[-5px] hover:bg-white/[0.07] transition-all duration-300 min-w-[160px]">
                  <div className="text-3xl mb-2">{s.icon}</div>
                  <div className="text-xs text-slate-400 font-medium">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-28 bg-gradient-to-b from-surface-950 to-surface-900 relative">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
        <div className="container mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold text-slate-100 mb-5 relative inline-block">
              Powerful Features
              <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-14 h-1 bg-gradient-to-r from-brand-500 to-accent-500 rounded-full" />
            </h2>
            <p className="text-lg text-slate-500 max-w-[600px] mx-auto mt-4">Everything you need to study smarter, not harder</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { title: 'Intelligent Q&A', desc: 'Ask natural language questions and get accurate answers grounded in your actual textbook content.', icon: <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10H12V2z" /><path d="M20 12a8 8 0 0 0-8-8v8h8z" /></svg> },
              { title: 'PDF Viewer with Highlights', desc: 'View your textbook side-by-side with the chat. Source passages are highlighted directly on the PDF page.', icon: <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg> },
              { title: 'Full Trace & Analytics', desc: 'See exactly how the AI found its answer — retrieval scores, chunk rankings, and full query trace.', icon: <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg> },
            ].map((f) => (
              <div key={f.title} className="group bg-white/[0.03] p-10 rounded-2xl border border-white/[0.06] text-center relative overflow-hidden hover:translate-y-[-6px] hover:bg-white/[0.06] hover:shadow-[0_20px_40px_rgba(0,0,0,0.3)] transition-all duration-400">
                <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-brand-500 to-accent-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-left" />
                <div className="w-[72px] h-[72px] bg-gradient-to-br from-brand-500 to-accent-500 rounded-2xl flex items-center justify-center mx-auto mb-6 text-white shadow-[0_8px_25px_rgba(59,130,246,0.25)]">
                  {f.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-100 mb-3">{f.title}</h3>
                <p className="text-slate-400 leading-relaxed text-sm">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-28 bg-surface-950">
        <div className="container mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold text-slate-100 mb-5 relative inline-block">
              How It Works
              <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-14 h-1 bg-gradient-to-r from-brand-500 to-accent-500 rounded-full" />
            </h2>
            <p className="text-lg text-slate-500 max-w-[600px] mx-auto mt-4">Three simple steps to get started</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {[
              { n: '1', title: 'Upload Textbooks', desc: 'Admin uploads PDF textbooks. The system automatically ingests, chunks, and indexes the content.' },
              { n: '2', title: 'Ask Questions', desc: 'Type a question in natural language. The AI searches across all indexed textbook content.' },
              { n: '3', title: 'Get Cited Answers', desc: 'Receive accurate answers with page-level citations. Click sources to jump to the exact PDF page.' },
            ].map((s) => (
              <div key={s.n} className="text-center p-11 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:translate-y-[-5px] hover:bg-white/[0.05] transition-all duration-300">
                <div className="w-16 h-16 bg-gradient-to-br from-brand-500 to-accent-500 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-[0_8px_25px_rgba(59,130,246,0.25)]">
                  {s.n}
                </div>
                <h3 className="text-xl font-bold text-slate-100 mb-3">{s.title}</h3>
                <p className="text-slate-400 leading-relaxed text-sm">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-28 bg-gradient-to-r from-surface-900 via-surface-800 to-surface-900 relative overflow-hidden">
        <div className="container mx-auto px-6">
          <div className="text-center max-w-[700px] mx-auto relative z-10">
            <h2 className="text-4xl font-bold text-slate-100 mb-5">Ready to Study Smarter?</h2>
            <p className="text-xl text-slate-400 mb-12 leading-relaxed">Sign in and start asking your textbooks questions today.</p>

            <div className="flex gap-5 justify-center flex-wrap">
              <Link href="/ask" className="inline-flex items-center gap-2.5 px-9 py-4.5 text-lg font-semibold rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-[0_8px_32px_rgba(59,130,246,0.3)] hover:translate-y-[-3px] hover:shadow-[0_15px_45px_rgba(59,130,246,0.4)] transition-all duration-300">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                Start Asking
              </Link>
              <Link href="/login" className="inline-flex items-center gap-2.5 px-9 py-4.5 text-lg font-semibold rounded-xl border-2 border-slate-500/30 text-slate-400 hover:bg-white/5 hover:border-slate-400/50 hover:text-white hover:translate-y-[-2px] transition-all duration-300">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" /><polyline points="10 17 15 12 10 7" /><line x1="15" y1="12" x2="3" y2="12" /></svg>
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
