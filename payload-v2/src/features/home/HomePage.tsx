'use client'

import Link from 'next/link'
import Image from 'next/image'
import {
  ArrowRight,
  Bot,
  Check,
  Play,
} from 'lucide-react'

import { useAuth } from '@/features/shared/AuthProvider'
import PublicNav from '@/features/layout/PublicNav'
import { CATEGORIES, ALL_ROLES, type CategoryDef, type RoleDef } from '@/features/shared/consultingRoles'

export default function HomePage() {
  const { user } = useAuth()
  const primaryHref = user ? '/consulting' : '/register'

  return (
    <main className="min-h-screen bg-background text-foreground">
      {/* ── Navigation ── */}
      <PublicNav page="landing" />

      {/* ── Hero ── */}
      <section className="relative min-h-[100vh] overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50/50 to-indigo-50/40 dark:bg-[#020617] dark:from-[#020617] dark:via-[#020617] dark:to-[#020617]">
        {/* Primary radial glow — top center */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(59,130,246,0.18),transparent)] dark:bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(59,130,246,0.12),transparent)] dark:opacity-100" />
        {/* Secondary radial glow — bottom right for depth */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_80%_80%,rgba(99,102,241,0.10),transparent)] dark:bg-[radial-gradient(ellipse_60%_50%_at_80%_80%,rgba(99,102,241,0.06),transparent)]" />
        {/* Subtle grid pattern for texture */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px] dark:bg-[linear-gradient(rgba(59,130,246,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.04)_1px,transparent_1px)]" />
        {/* Orbs — much more visible in light mode */}
        <div className="absolute left-[-8%] top-[20%] h-[600px] w-[600px] rounded-full bg-blue-500/[0.12] blur-[140px] orb-float dark:bg-blue-600/[0.07]" />
        <div className="absolute bottom-[5%] right-[0%] h-[500px] w-[500px] rounded-full bg-indigo-400/[0.10] blur-[120px] orb-float-2 dark:bg-indigo-500/[0.06]" />
        <div className="absolute right-[30%] top-[60%] h-[300px] w-[300px] rounded-full bg-violet-400/[0.08] blur-[100px] orb-float dark:bg-violet-500/[0.04]" />

        <div className="relative z-10 mx-auto flex min-h-[100vh] max-w-7xl items-center px-5 pb-24 pt-32 md:px-8">
          <div className="grid w-full items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <h1 className="hero-fade-up max-w-2xl text-5xl font-extrabold leading-[1.1] tracking-tight text-slate-900 dark:text-white md:text-7xl">
                AI consulting that{' '}
                <span className="bg-gradient-to-r from-blue-600 via-blue-500 to-indigo-500 bg-clip-text text-transparent dark:from-blue-400 dark:via-blue-300 dark:to-indigo-300">
                  shows its work.
                </span>
              </h1>

              <p className="hero-fade-up hero-fade-up-delay-1 mt-6 max-w-xl text-lg leading-8 text-muted-foreground md:text-xl">
                Ask questions across private PDFs, switch expert roles, and inspect every answer
                with citations, retrieval traces, and evaluation signals.
              </p>

              <div className="hero-fade-up hero-fade-up-delay-2 mt-10 flex flex-col gap-3 sm:flex-row">
                <Link
                  href={primaryHref}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-7 py-3.5 text-sm font-bold text-primary-foreground shadow-lg shadow-blue-500/30 transition-all hover:scale-[1.02] hover:bg-primary/90 hover:shadow-xl hover:shadow-blue-500/25 dark:bg-white dark:text-slate-950 dark:shadow-white/10 dark:hover:bg-white/95 dark:hover:shadow-white/15"
                >
                  Start free
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-7 py-3.5 text-sm font-bold text-foreground transition-colors hover:bg-muted dark:border-white/20 dark:bg-white/8 dark:text-white dark:hover:bg-white/15"
                >
                  View pricing
                </Link>
              </div>

              <div className="hero-fade-up hero-fade-up-delay-3 mt-8 flex flex-wrap gap-6 text-sm text-muted-foreground">
                {['Private documents', 'Grounded citations', 'Quality scoring'].map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-emerald-400" aria-hidden />
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {/* Score card — the hero differentiator */}
            <div className="hero-fade-in hidden lg:flex lg:justify-center" style={{ animationDelay: '700ms' }}>
              <div className="relative">
                <div className="absolute -inset-10 rounded-3xl bg-blue-500/10 blur-3xl dark:bg-blue-500/15" />
                <div className="score-pulse relative w-[340px] rounded-2xl border border-slate-200/80 bg-white p-7 shadow-xl shadow-slate-300/30 backdrop-blur-2xl dark:border-white/15 dark:bg-slate-900/90 dark:shadow-black/30">
                  {/* Header */}
                  <div className="flex items-center justify-between">
                    <div className="text-[11px] font-bold uppercase tracking-widest text-blue-600 dark:text-blue-300">
                      Quality Score
                    </div>
                    <div className="flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 dark:bg-emerald-500/15">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-300">Live</span>
                    </div>
                  </div>

                  {/* Circular score */}
                  <div className="my-6 flex items-center gap-6">
                    <div className="relative h-28 w-28 shrink-0">
                      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                        <circle cx="60" cy="60" r="52" fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-100 dark:text-white/10" />
                        <circle cx="60" cy="60" r="52" fill="none" stroke="url(#scoreGrad)" strokeWidth="8" strokeLinecap="round" strokeDasharray={`${85 * 3.267} ${100 * 3.267}`} className="score-ring-animate" />
                        <defs>
                          <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#3b82f6" />
                            <stop offset="100%" stopColor="#6366f1" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-extrabold text-foreground">85</span>
                        <span className="text-[10px] font-medium text-muted-foreground">/100</span>
                      </div>
                    </div>
                    <div className="space-y-1.5 text-xs">
                      <div className="font-bold text-foreground">Excellent</div>
                      <div className="leading-5 text-muted-foreground">All quality signals exceeded threshold. Ready for action.</div>
                    </div>
                  </div>

                  {/* Metric bars */}
                  <div className="space-y-3">
                    <ScoreBar label="Relevance" value={90} color="bg-emerald-500" dot="bg-emerald-500" />
                    <ScoreBar label="Grounding" value={82} color="bg-blue-500" dot="bg-blue-500" />
                    <ScoreBar label="Completeness" value={78} color="bg-amber-500" dot="bg-amber-500" />
                    <ScoreBar label="Clarity" value={88} color="bg-violet-500" dot="bg-violet-500" />
                  </div>

                  {/* Footer badge */}
                  <div className="mt-5 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] font-bold text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300">
                    <Check className="h-3.5 w-3.5" aria-hidden />
                    All signals passed — safe to act
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works — with live preview ── */}
      <section className="bg-white/80 py-24 dark:bg-card">
        <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 md:px-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <h2 className="text-3xl font-extrabold tracking-normal md:text-4xl">
              How it works
            </h2>
            <div className="mt-8 space-y-5">
              <HowStep number="1" title="Pick an expert role" text="Legal, finance, research, or strategy — each shapes the answer tone and retrieval scope." />
              <HowStep number="2" title="Ask against your documents" text="Private PDFs stay isolated. Shared textbook knowledge fills in gaps." />
              <HowStep number="3" title="Review before you act" text="Every response shows source citations, retrieval trace, and a multi-signal quality score." />
            </div>
          </div>

          {/* Interactive preview */}
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl shadow-slate-200/50 dark:border-border dark:bg-background dark:shadow-black/20">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Play className="h-4 w-4 text-primary" aria-hidden />
                Live preview
              </div>
              <span className="rounded-lg bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground">
                Demo
              </span>
            </div>
            <div className="grid aspect-video bg-background md:grid-cols-[170px_1fr]">
              <aside className="hidden border-r border-border bg-card p-4 md:block">
                <div className="mb-5 h-2 w-20 rounded bg-primary/70" />
                {['Strategy', 'Legal', 'Research', 'Finance'].map((role, index) => (
                  <div
                    key={role}
                    className={`mb-2 rounded-md px-3 py-2 text-xs font-semibold ${index === 1
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                      }`}
                  >
                    {role}
                  </div>
                ))}
              </aside>
              <div className="min-w-0 p-4 sm:p-5">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <div className="h-3 w-28 rounded bg-foreground/80" />
                    <div className="mt-2 h-2 w-44 rounded bg-muted-foreground/30" />
                  </div>
                  <div className="rounded-md border border-border px-2 py-1 text-[10px] font-bold uppercase text-primary">
                    Streaming
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="ml-auto max-w-[75%] rounded-lg bg-primary px-4 py-3 text-xs font-medium leading-5 text-primary-foreground">
                    Which clause creates the highest renewal risk?
                  </div>
                  <div className="rounded-lg border border-border bg-card p-4">
                    <div className="mb-3 flex items-center gap-2 text-xs font-bold">
                      <Bot className="h-4 w-4 text-primary" aria-hidden />
                      Legal persona answer
                    </div>
                    <div className="space-y-2">
                      <div className="h-2 rounded bg-foreground/70" />
                      <div className="h-2 rounded bg-muted-foreground/35" />
                      <div className="h-2 w-4/5 rounded bg-muted-foreground/35" />
                    </div>
                    <div className="mt-4 grid gap-2 sm:grid-cols-3">
                      {['Source §5.2', 'Dual-KB', '92/100'].map((label) => (
                        <span
                          key={label}
                          className="rounded-md border border-border bg-background px-2 py-1 text-center text-[10px] font-bold text-muted-foreground"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Expert Consultants — 7 categories × 28 roles ── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-slate-50 to-blue-50/30 py-24 dark:bg-[#020617] dark:from-[#020617] dark:to-[#020617]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_50%,rgba(59,130,246,0.10),transparent)] dark:bg-[radial-gradient(ellipse_60%_40%_at_50%_50%,rgba(59,130,246,0.08),transparent)]" />
        <div className="relative z-10 mx-auto max-w-7xl px-5 md:px-8">
          <div className="text-center">
            <p className="inline-flex items-center rounded-lg border border-border bg-muted px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-blue-600 backdrop-blur dark:border-white/15 dark:bg-white/8 dark:text-blue-200">
              Expert Center
            </p>
            <h2 className="mt-5 text-3xl font-extrabold tracking-normal text-foreground md:text-4xl">
              Meet your AI consultants
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-base leading-7 text-muted-foreground">
              28 domain experts across 7 categories. Each backed by a dedicated knowledge base.
            </p>
          </div>

          <div className="mt-14 space-y-12">
            {CATEGORIES.map((cat) => {
              const roles = ALL_ROLES.filter((r) => r.category === cat.value)
              return (
                <CategorySection key={cat.value} cat={cat} roles={roles} href={primaryHref} />
              )
            })}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="border-y border-slate-200 bg-white dark:border-border dark:bg-transparent">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-5 py-16 md:flex-row md:items-center md:px-8">
          <div>
            <h2 className="text-3xl font-extrabold tracking-normal">Ready to get started?</h2>
            <p className="mt-2 max-w-xl text-muted-foreground">
              Create a free workspace. Upgrade when you need higher limits or priority generation.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href={primaryHref}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-bold text-primary-foreground transition-transform hover:scale-[1.02] hover:bg-primary/90"
            >
              Create your workspace
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center rounded-lg border border-border px-5 py-3 text-sm font-bold hover:bg-muted"
            >
              Compare plans
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="flex w-full flex-col justify-between gap-3 px-5 py-4 text-sm text-muted-foreground md:flex-row md:px-8">
        <span>© 2026 ConsultRAG. All rights reserved.</span>
        <div className="flex gap-5">
          <Link href="/pricing" className="hover:text-foreground">Pricing</Link>
          <Link href="/terms" className="hover:text-foreground">Terms</Link>
          <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
        </div>
      </footer>
    </main>
  )
}

/* ── Helper components ── */

function ScoreBar({ label, value, color, dot }: { label: string; value: number; color: string; dot: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />
      <span className="w-24 text-[11px] font-medium text-foreground/70">{label}</span>
      <div className="flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-white/10">
        <div
          className={`h-1.5 rounded-full ${color} transition-all duration-1000`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="w-7 text-right text-[11px] font-bold tabular-nums text-foreground">{value}</span>
    </div>
  )
}

function HowStep({ number, title, text }: { number: string; title: string; text: string }) {
  return (
    <div className="flex gap-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
        {number}
      </span>
      <div>
        <h3 className="font-bold">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{text}</p>
      </div>
    </div>
  )
}

/* ── Expert Center — uses shared CATEGORIES + ALL_ROLES from consultingRoles.ts ── */

function CategorySection({ cat, roles, href }: { cat: CategoryDef; roles: RoleDef[]; href: string }) {
  return (
    <div>
      <h3 className="mb-4 text-sm font-semibold text-muted-foreground">
        {cat.label}
      </h3>
      {/* Roles grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map((role) => (
          <RoleCard key={role.slug} role={role} cat={cat} href={href} />
        ))}
      </div>
    </div>
  )
}

function RoleCard({ role, cat, href }: { role: RoleDef; cat: CategoryDef; href: string }) {
  const inner = (
    <div
      className={`group flex items-start gap-4 rounded-xl border p-4 transition-all ${role.enabled
          ? 'border-slate-200 bg-white shadow-sm hover:border-blue-200 hover:shadow-md hover:shadow-blue-100/50 dark:border-white/8 dark:bg-slate-900/60 dark:hover:border-white/20 dark:hover:bg-slate-800/60'
          : 'border-dashed border-slate-200 bg-slate-50/50 dark:border-white/5 dark:bg-slate-900/30'
        }`}
    >
      {/* Avatar or initial */}
      {role.avatar ? (
        <div className={`h-12 w-12 shrink-0 overflow-hidden rounded-full ring-2 ${cat.ringColor} transition-shadow group-hover:ring-[3px]`}>
          <Image src={role.avatar} alt={role.name} width={48} height={48} className="h-full w-full object-cover" />
        </div>
      ) : (
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${cat.bgColor} ring-2 ${cat.ringColor}`}>
          <span className={`text-sm font-bold ${cat.textColor}`}>
            {role.name.charAt(0)}
          </span>
        </div>
      )}
      {/* Text */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h4 className={`text-sm font-bold ${role.enabled ? 'text-foreground' : 'text-muted-foreground'}`}>
            {role.name}
          </h4>
          {!role.enabled && (
            <span className="shrink-0 rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
              Coming soon
            </span>
          )}
        </div>
        <p className="mt-1 text-[12px] leading-[1.5] text-muted-foreground">
          {role.description}
        </p>
      </div>
    </div>
  )

  if (!role.enabled) return <div className="cursor-default opacity-60">{inner}</div>

  return (
    <Link href={href} className="block">
      {inner}
    </Link>
  )
}

