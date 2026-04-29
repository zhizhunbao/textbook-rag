/**
 * UsagePanel — Compact quota usage display for sidebar/user menu.
 *
 * Shows today's queries (X/30) and monthly ingests (Y/3) as progress bars.
 * Color coding: green (0-70%) → amber (70-90%) → red (90-100%).
 *
 * GO-MON-05: Visual quota awareness to drive Pro upgrades.
 */

'use client'

import { useQuota, type QuotaBucket } from './useQuota'

// ============================================================
// Component
// ============================================================

export default function UsagePanel() {
  const { data, loading } = useQuota()

  if (loading || !data) {
    return (
      <div className="px-3 py-2 text-xs text-muted-foreground">
        Loading usage...
      </div>
    )
  }

  return (
    <div className="px-3 py-2 space-y-2 border-t border-border/50">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
          Usage
        </span>
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
          data.tier === 'pro'
            ? 'bg-indigo-500/20 text-indigo-400'
            : 'bg-zinc-500/20 text-zinc-400'
        }`}>
          {data.tier.toUpperCase()}
        </span>
      </div>
      <QuotaBar label="Queries today" bucket={data.query} />
      <QuotaBar label="Docs this month" bucket={data.ingest} />
    </div>
  )
}

// ============================================================
// Sub-components
// ============================================================

function QuotaBar({ label, bucket }: { label: string; bucket: QuotaBucket }) {
  const pct = bucket.limit > 0 ? (bucket.used / bucket.limit) * 100 : 0
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-emerald-500'

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground/70 tabular-nums">
          {bucket.used}/{bucket.limit}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-muted/50 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  )
}
