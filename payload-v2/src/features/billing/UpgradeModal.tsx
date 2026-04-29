/**
 * UpgradeModal — Pro upgrade prompt shown when quota is exceeded.
 *
 * Triggered when a query returns 403 (quota exceeded).
 * Shows Free vs Pro comparison table with CTA to Stripe Checkout.
 *
 * GO-MON-06: Conversion funnel — quota wall → upgrade → payment.
 */

'use client'

import { useState } from 'react'

// ============================================================
// Types
// ============================================================

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  tier?: 'free' | 'pro'
  action?: string  // 'query' | 'ingest'
}

// ============================================================
// Component
// ============================================================

export default function UpgradeModal({ open, onClose, tier = 'free', action }: UpgradeModalProps) {
  const [loading, setLoading] = useState(false)

  if (!open) return null

  const handleUpgrade = async () => {
    setLoading(true)
    try {
      // Call Stripe Checkout via Payload's Stripe plugin REST proxy
      const res = await fetch('/api/stripe/rest', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stripeMethod: 'checkout.sessions.create',
          stripeArgs: [{
            mode: 'subscription',
            line_items: [{
              price: process.env.NEXT_PUBLIC_STRIPE_PRO_PRICE_ID || '',
              quantity: 1,
            }],
            success_url: `${window.location.origin}/consulting?upgraded=true`,
            cancel_url: `${window.location.origin}/consulting`,
          }],
        }),
      })
      if (res.ok) {
        const { data } = await res.json()
        if (data?.url) {
          window.location.href = data.url
        }
      }
    } catch (e) {
      console.error('Checkout failed:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 pt-6 pb-4">
          <h2 className="text-xl font-semibold text-foreground">
            Upgrade to Pro
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {action === 'query'
              ? 'You\'ve reached your daily query limit.'
              : action === 'ingest'
                ? 'You\'ve reached your monthly document upload limit.'
                : 'Unlock higher limits and premium features.'}
          </p>
        </div>

        {/* Comparison table */}
        <div className="px-6 pb-4">
          <div className="grid grid-cols-2 gap-3">
            {/* Free column */}
            <div className={`rounded-xl p-4 border ${
              tier === 'free' ? 'border-zinc-500/50 bg-zinc-500/5' : 'border-border bg-muted/30'
            }`}>
              <div className="text-sm font-medium text-muted-foreground mb-3">Free</div>
              <ul className="space-y-2 text-sm">
                <FeatureRow label="Queries / day" value="30" />
                <FeatureRow label="Doc uploads / mo" value="3" />
                <FeatureRow label="All roles" value="Yes" />
                <FeatureRow label="Priority answers" value="—" dim />
              </ul>
              {tier === 'free' && (
                <div className="mt-3 text-[11px] text-center text-zinc-400 font-medium">
                  Current plan
                </div>
              )}
            </div>

            {/* Pro column */}
            <div className="rounded-xl p-4 border-2 border-indigo-500/60 bg-indigo-500/5 relative">
              <div className="absolute -top-2 right-3 text-[10px] font-bold text-white bg-indigo-500 px-2 py-0.5 rounded-full">
                RECOMMENDED
              </div>
              <div className="text-sm font-medium text-indigo-400 mb-3">Pro</div>
              <ul className="space-y-2 text-sm">
                <FeatureRow label="Queries / day" value="200" highlight />
                <FeatureRow label="Doc uploads / mo" value="100" highlight />
                <FeatureRow label="All roles" value="Yes" />
                <FeatureRow label="Priority answers" value="Yes" highlight />
              </ul>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 pb-6 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 text-sm font-medium rounded-lg border border-border text-muted-foreground hover:bg-muted/50 transition-colors"
          >
            Maybe later
          </button>
          <button
            onClick={handleUpgrade}
            disabled={loading}
            className="flex-1 px-4 py-2.5 text-sm font-semibold rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Redirecting...' : 'Upgrade — $19/mo'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Sub-components
// ============================================================

function FeatureRow({
  label,
  value,
  highlight = false,
  dim = false,
}: {
  label: string
  value: string
  highlight?: boolean
  dim?: boolean
}) {
  return (
    <li className="flex justify-between">
      <span className={dim ? 'text-muted-foreground/50' : 'text-muted-foreground'}>{label}</span>
      <span className={
        highlight ? 'font-semibold text-indigo-400' :
        dim ? 'text-muted-foreground/50' :
        'text-foreground/80'
      }>
        {value}
      </span>
    </li>
  )
}
