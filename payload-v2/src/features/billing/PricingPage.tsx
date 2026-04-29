/**
 * PricingPage - Public Free vs Pro plan comparison.
 *
 * Route: /pricing
 * Layout: standalone public page
 */

'use client'

import Link from 'next/link'
import { useState } from 'react'

// ============================================================
// Component
// ============================================================
export function PricingPage() {
  const [loading, setLoading] = useState(false)

  const handleUpgrade = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/stripe/rest', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stripeMethod: 'checkout.sessions.create',
          stripeArgs: [{
            mode: 'subscription',
            payment_method_types: ['card'],
            line_items: [{
              price: process.env.NEXT_PUBLIC_STRIPE_PRO_PRICE_ID || '',
              quantity: 1,
            }],
            success_url: `${window.location.origin}/consulting?upgraded=true`,
            cancel_url: `${window.location.origin}/pricing`,
          }],
        }),
      })
      if (res.ok) {
        const { data } = await res.json()
        if (data?.url) window.location.href = data.url
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link href="/" className="text-sm font-bold uppercase tracking-widest text-primary">
          ConsultRAG
        </Link>
        <div className="flex items-center gap-4 text-sm font-medium">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            Home
          </Link>
          <Link href="/register" className="rounded-lg bg-primary px-4 py-2 text-primary-foreground">
            Start free
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-10">
        <div className="max-w-2xl">
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-primary">
            Pricing
          </p>
          <h1 className="text-4xl font-extrabold tracking-tight md:text-6xl">
            Choose the plan that matches your consulting workload.
          </h1>
          <p className="mt-5 text-lg leading-8 text-muted-foreground">
            Start with grounded answers and citations for free. Upgrade when you need higher
            daily limits, more private document capacity, and priority generation.
          </p>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <PlanCard
            name="Free"
            price="$0"
            summary="For first projects and light daily research."
            cta={<Link href="/register" className="block rounded-lg border border-border px-4 py-3 text-center text-sm font-semibold hover:bg-muted">Start free</Link>}
            features={[
              '10 queries per day',
              '3 private documents per month',
              'Basic consulting roles',
              'Source citations',
            ]}
          />
          <PlanCard
            name="Pro"
            price="$19/mo"
            summary="For repeat consulting sessions and heavier document workflows."
            highlighted
            cta={(
              <button
                onClick={handleUpgrade}
                disabled={loading}
                className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Redirecting...' : 'Upgrade with Stripe'}
              </button>
            )}
            features={[
              '200 queries per day',
              '100 private documents per month',
              'All consulting roles',
              'Priority answers',
            ]}
          />
        </div>
      </section>
    </main>
  )
}

function PlanCard({
  name,
  price,
  summary,
  features,
  cta,
  highlighted = false,
}: {
  name: string
  price: string
  summary: string
  features: string[]
  cta: React.ReactNode
  highlighted?: boolean
}) {
  return (
    <article className={`rounded-xl border p-7 ${highlighted ? 'border-primary bg-primary/5' : 'border-border bg-card'}`}>
      <div className="mb-6">
        <h2 className="text-xl font-bold">{name}</h2>
        <div className="mt-4 text-4xl font-extrabold">{price}</div>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{summary}</p>
      </div>
      {cta}
      <ul className="mt-6 space-y-3">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-3 text-sm text-muted-foreground">
            <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            {feature}
          </li>
        ))}
      </ul>
    </article>
  )
}
