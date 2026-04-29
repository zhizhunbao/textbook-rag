'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useEffect, useState, type ReactNode } from 'react'
import {
  ArrowRight,
  BarChart3,
  Bot,
  Check,
  FileText,
  LockKeyhole,
  MessageSquareText,
  Play,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from 'lucide-react'

import { useAuth } from '@/features/shared/AuthProvider'
import ThemeToggle from '@/features/shared/components/ThemeToggle'

type HomeMetrics = {
  expertRoles: number
  indexedBooks: number
  knowledgeChunks: number
  evaluations: number
}

/**
 * HomePage - Public landing page for ConsultRAG.
 *
 * Route: /
 * Purpose: explain the product value before registration and route visitors
 * into signup, pricing, or the authenticated consulting workspace.
 */
export default function HomePage() {
  const { user } = useAuth()
  const primaryHref = user ? '/consulting' : '/register'
  const [metrics, setMetrics] = useState<HomeMetrics | null>(null)

  useEffect(() => {
    let cancelled = false

    fetch('/api/home-metrics', {
      credentials: 'include',
      cache: 'no-store',
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: HomeMetrics | null) => {
        if (!cancelled && data) setMetrics(data)
      })
      .catch(() => {
        if (!cancelled) setMetrics(null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-black/25 backdrop-blur-md">
        <nav className="flex w-full items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-3 text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15">
              <SearchCheck className="h-5 w-5" aria-hidden />
            </span>
            <span className="text-sm font-bold uppercase tracking-widest">ConsultRAG</span>
          </Link>

          <div className="flex items-center gap-3">
            <ThemeToggle className="border-white/15 bg-white/10 text-white hover:bg-white/20" />
            <Link
              href={primaryHref}
              className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-950 hover:bg-white/90"
            >
              Start free
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            {!user && (
              <Link
                href="/login"
                className="inline-flex items-center rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-sm font-bold text-white backdrop-blur hover:bg-white/15"
              >
                Log in
              </Link>
            )}
          </div>
        </nav>
      </header>

      <section className="relative min-h-[92vh] overflow-hidden">
        <Image
          src="/consultrag-hero.png"
          alt="ConsultRAG product workspace with AI answers, source citations, PDF context, and evaluation scores"
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(2,6,23,0.92)_0%,rgba(15,23,42,0.74)_42%,rgba(15,23,42,0.36)_100%)]" />

        <div className="relative z-10 mx-auto flex min-h-[92vh] max-w-7xl items-center px-5 pb-20 pt-28 md:px-8">
          <div className="max-w-3xl">
            <p className="mb-5 inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-xs font-bold uppercase tracking-widest text-blue-100 backdrop-blur">
              <Sparkles className="h-4 w-4" aria-hidden />
              Multi-role private document intelligence
            </p>
            <h1 className="max-w-3xl text-5xl font-extrabold leading-tight tracking-normal text-white md:text-7xl">
              AI consulting that shows its work.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-100 md:text-xl">
              Ask questions across private PDFs, switch expert roles, and inspect every answer with
              citations, retrieval traces, and evaluation signals.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href={primaryHref}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-bold text-slate-950 hover:bg-white/90"
              >
                Start free
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/20 bg-white/10 px-6 py-3 text-sm font-bold text-white backdrop-blur hover:bg-white/15"
              >
                View pricing
              </Link>
            </div>

            <div className="mt-10 grid max-w-2xl gap-3 text-sm text-slate-100 sm:grid-cols-3">
              {['Private documents', 'Grounded citations', 'Quality scoring'].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-teal-300" aria-hidden />
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-card">
        <div className="mx-auto grid max-w-7xl gap-4 px-5 py-8 md:grid-cols-4 md:px-8">
          <Metric value={formatMetric(metrics?.expertRoles)} label="enabled expert roles" />
          <Metric value={formatMetric(metrics?.indexedBooks)} label="indexed books" />
          <Metric value={formatMetric(metrics?.knowledgeChunks)} label="knowledge chunks" />
          <Metric value={formatMetric(metrics?.evaluations)} label="quality evaluations" />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 md:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-widest text-primary">Core workflow</p>
          <h2 className="mt-3 text-3xl font-extrabold tracking-normal md:text-5xl">
            Built for repeated research, not one-off demos.
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            ConsultRAG keeps document context, expert persona, answer quality, and evidence in one
            workspace so every session can be reviewed and improved.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          <FeatureCard
            icon={<UsersRound className="h-5 w-5" aria-hidden />}
            title="Choose the role"
            description="Use analyst, consultant, researcher, or student modes to shape the answer style."
          />
          <FeatureCard
            icon={<FileText className="h-5 w-5" aria-hidden />}
            title="Upload private PDFs"
            description="Keep document-specific context separate from shared textbook knowledge."
          />
          <FeatureCard
            icon={<MessageSquareText className="h-5 w-5" aria-hidden />}
            title="Ask naturally"
            description="Get streamed answers grounded in relevant passages instead of raw search results."
          />
          <FeatureCard
            icon={<BarChart3 className="h-5 w-5" aria-hidden />}
            title="Inspect quality"
            description="Review citations, retrieval trace, and evaluation signals before trusting output."
          />
        </div>
      </section>

      <section className="bg-card py-20">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 md:px-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-primary">Product demo</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-normal md:text-5xl">
              From role selection to cited answer in one flow.
            </h2>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              The recorded demo slot is ready for a 30-second walkthrough. Until the final clip is
              captured, this preview shows the actual flow visitors will see after signup.
            </p>
            <div className="mt-8 space-y-4">
              <Step number="1" text="Select an expert persona for the task." />
              <Step number="2" text="Ask against private documents and shared knowledge." />
              <Step number="3" text="Review answer, citations, and score before acting." />
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-border bg-background shadow-sm">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Play className="h-4 w-4 text-primary" aria-hidden />
                30s walkthrough
              </div>
              <span className="rounded-lg bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground">
                Preview
              </span>
            </div>
            <div className="grid aspect-video bg-background md:grid-cols-[170px_1fr]">
              <aside className="hidden border-r border-border bg-card p-4 md:block">
                <div className="mb-5 h-2 w-20 rounded bg-primary/70" />
                {['Strategy', 'Legal', 'Research', 'Finance'].map((role, index) => (
                  <div
                    key={role}
                    className={`mb-2 rounded-md px-3 py-2 text-xs font-semibold ${
                      index === 1
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
                      {['Source 3', 'Both', 'Pass'].map((label) => (
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

      <section className="mx-auto max-w-7xl px-5 py-20 md:px-8">
        <div className="grid gap-5 md:grid-cols-3">
          <TrustCard
            icon={<LockKeyhole className="h-5 w-5" aria-hidden />}
            title="Private by default"
            description="User documents and consulting knowledge bases stay isolated per account."
          />
          <TrustCard
            icon={<ShieldCheck className="h-5 w-5" aria-hidden />}
            title="Designed for review"
            description="Every answer can carry source context, retrieval metadata, and quality status."
          />
          <TrustCard
            icon={<Bot className="h-5 w-5" aria-hidden />}
            title="Model-flexible"
            description="Local and configured LLMs can be tested, compared, and routed by workload."
          />
        </div>
      </section>

      <section className="border-y border-border bg-card">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-5 py-14 md:flex-row md:items-center md:px-8">
          <div>
            <h2 className="text-3xl font-extrabold tracking-normal">Start with the free tier.</h2>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Upgrade when you need higher query limits, more private documents, and priority answer generation.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href={primaryHref}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-bold text-primary-foreground hover:bg-primary/90"
            >
              Start free
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

      <footer className="flex w-full flex-col justify-between gap-4 px-5 py-8 text-sm text-muted-foreground md:flex-row md:px-8">
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

function formatMetric(value: number | undefined) {
  if (typeof value !== 'number') return '--'
  return new Intl.NumberFormat('en-US', { notation: value >= 1000 ? 'compact' : 'standard' }).format(value)
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-lg border border-border bg-background p-5">
      <div className="text-3xl font-extrabold">{value}</div>
      <div className="mt-1 text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</div>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: ReactNode
  title: string
  description: string
}) {
  return (
    <article className="rounded-lg border border-border bg-card p-6">
      <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </div>
      <h3 className="font-bold">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
    </article>
  )
}

function Step({ number, text }: { number: string; text: string }) {
  return (
    <div className="flex gap-4">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
        {number}
      </span>
      <p className="pt-1 text-sm font-medium text-muted-foreground">{text}</p>
    </div>
  )
}

function TrustCard({
  icon,
  title,
  description,
}: {
  icon: ReactNode
  title: string
  description: string
}) {
  return (
    <article className="rounded-lg border border-border bg-card p-6">
      <div className="mb-4 text-primary">{icon}</div>
      <h3 className="font-bold">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
    </article>
  )
}
