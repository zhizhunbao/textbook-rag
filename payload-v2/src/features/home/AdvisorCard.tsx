/**
 * AdvisorCard — Reusable consulting role card for Landing + Onboarding pages.
 *
 * Displays avatar, role name, one-line description, and a CTA button.
 * Supports two modes:
 *   - "link" (default) — renders as a Next.js Link to /consulting?persona={slug}
 *   - "select" — renders as a button with selection state (for Onboarding)
 */

'use client'

import Image from 'next/image'
import Link from 'next/link'
import { cn } from '@/features/shared/utils'
import type { CategoryDef } from '@/features/shared/consultingRoles'

export interface AdvisorCardProps {
  slug: string
  name: string
  description?: string
  avatar?: string
  enabled?: boolean
  cat: CategoryDef
  /** "link" = Landing page (navigates), "select" = Onboarding (toggle selection) */
  mode?: 'link' | 'select'
  /** Only for mode="select" */
  selected?: boolean
  /** Only for mode="select" */
  onSelect?: () => void
  /** Whether the knowledge base has data */
  hasKnowledgeBase?: boolean
}

export default function AdvisorCard({
  slug,
  name,
  description,
  avatar,
  enabled = true,
  cat,
  mode = 'link',
  selected = false,
  onSelect,
  hasKnowledgeBase = true,
}: AdvisorCardProps) {
  // ── Disabled role (coming soon) ──
  if (!enabled) {
    return (
      <div className="cursor-default opacity-60">
        <CardInner
          name={name}
          description={description}
          avatar={avatar}
          cat={cat}
          badge="Coming soon"
        />
      </div>
    )
  }

  // ── Select mode (Onboarding) ──
  if (mode === 'select') {
    return (
      <button type="button" onClick={onSelect} className="text-left w-full">
        <CardInner
          name={name}
          description={description}
          avatar={avatar}
          cat={cat}
          selected={selected}
        />
      </button>
    )
  }

  // ── Link mode (Landing) ──
  if (!hasKnowledgeBase) {
    return (
      <div className="cursor-not-allowed">
        <CardInner
          name={name}
          description={description}
          avatar={avatar}
          cat={cat}
          badge="Knowledge base preparing"
          badgeVariant="muted"
        />
      </div>
    )
  }

  return (
    <Link href={`/consulting?persona=${slug}`} className="block">
      <CardInner
        name={name}
        description={description}
        avatar={avatar}
        cat={cat}
      />
    </Link>
  )
}

/* ── Inner card layout (shared across all modes) ── */

function CardInner({
  name,
  description,
  avatar,
  cat,
  selected = false,
  badge,
  badgeVariant = 'default',
}: {
  name: string
  description?: string
  avatar?: string
  cat: CategoryDef
  selected?: boolean
  badge?: string
  badgeVariant?: 'default' | 'muted'
}) {
  return (
    <div
      className={cn(
        'group relative flex items-start gap-4 rounded-xl border p-4 transition-all duration-200',
        selected
          ? 'border-primary bg-primary/5 shadow-md shadow-primary/10 ring-2 ring-primary/30 dark:bg-primary/10 dark:shadow-primary/5'
          : badge
            ? 'border-dashed border-slate-200 bg-slate-50/50 dark:border-white/5 dark:bg-slate-900/30'
            : 'border-slate-200 bg-white shadow-sm hover:border-blue-200 hover:shadow-md hover:shadow-blue-100/50 dark:border-white/8 dark:bg-slate-900/60 dark:hover:border-white/20 dark:hover:bg-slate-800/60',
      )}
    >
      {/* Selected checkmark */}
      {selected && (
        <div className="absolute -right-1.5 -top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-primary shadow-lg shadow-primary/30">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )}

      {/* Avatar */}
      {avatar ? (
        <div className={cn(
          'h-12 w-12 shrink-0 overflow-hidden rounded-full ring-2 transition-shadow',
          selected ? 'ring-primary/60 ring-[3px]' : `${cat.ringColor} group-hover:ring-[3px]`,
        )}>
          <Image src={avatar} alt={name} width={48} height={48} className="h-full w-full object-cover" />
        </div>
      ) : (
        <div className={cn(
          'flex h-12 w-12 shrink-0 items-center justify-center rounded-full ring-2',
          cat.bgColor,
          selected ? 'ring-primary/60' : cat.ringColor,
        )}>
          <span className={cn('text-sm font-bold', cat.textColor)}>
            {name.charAt(0)}
          </span>
        </div>
      )}

      {/* Text */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h4 className={cn(
            'text-sm font-bold',
            selected ? 'text-primary' : badge ? 'text-muted-foreground' : 'text-foreground',
          )}>
            {name}
          </h4>
          {badge && (
            <span className={cn(
              'shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold',
              badgeVariant === 'muted'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300'
                : 'bg-muted text-muted-foreground',
            )}>
              {badge}
            </span>
          )}
        </div>
        {description && (
          <p className="mt-1 text-[12px] leading-[1.5] text-muted-foreground line-clamp-2">
            {description}
          </p>
        )}
      </div>
    </div>
  )
}
