/**
 * PersonaCard — Displays a consulting persona with KB status badge.
 *
 * Shows icon + name + description + status badge + chunk count.
 * Status badge: Ready (green) / Empty (gray) / Processing (yellow).
 */

'use client'

import { cn } from '@/features/shared/utils'
import type { PersonaKbStatus, PersonaWithStats } from '../types'

// ── Status badge config ──

const STATUS_CONFIG: Record<PersonaKbStatus, {
  label: string
  bg: string
  text: string
  dot: string
}> = {
  ready: {
    label: 'Ready',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    dot: 'bg-emerald-500',
  },
  empty: {
    label: 'Empty',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    dot: 'bg-muted-foreground',
  },
  processing: {
    label: 'Processing',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    dot: 'bg-amber-500',
  },
}

// ── Icon mapping (SVG only, no emoji per global rules) ──

function PersonaIcon({ icon }: { icon?: string }) {
  if (icon === 'scale') {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3v17M5 7l7-4 7 4M4.2 10.5l.5 6h6.6l.5-6M12.2 10.5l.5 6h6.6l.5-6" />
      </svg>
    )
  }
  if (icon === 'shield-check') {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    )
  }
  if (icon === 'clipboard-check') {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect width="8" height="4" x="8" y="2" rx="1" ry="1" />
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
        <path d="m9 14 2 2 4-4" />
      </svg>
    )
  }
  // Default: briefcase
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="14" x="2" y="7" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  )
}

// ── Component ──

interface PersonaCardProps {
  persona: PersonaWithStats
  selected?: boolean
  onClick?: () => void
}

export default function PersonaCard({
  persona,
  selected,
  onClick,
}: PersonaCardProps) {
  const status = STATUS_CONFIG[persona.status]

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full text-left rounded-xl border p-4 transition-all',
        'hover:border-primary/30 hover:bg-card/80',
        selected
          ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/20'
          : 'border-border bg-card',
      )}
    >
      {/* Top: icon + name + status */}
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
          <PersonaIcon icon={persona.icon} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground truncate">
              {persona.name}
            </h3>
            <span className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium',
              status.bg, status.text,
            )}>
              <span className={cn('w-1.5 h-1.5 rounded-full', status.dot)} />
              {status.label}
            </span>
          </div>
          {persona.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {persona.description}
            </p>
          )}
        </div>
      </div>

      {/* Bottom: stats */}
      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border/50">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
          <span>{persona.chunkCount} chunks</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
          </svg>
          <span className="font-mono text-[10px]">{persona.chromaCollection}</span>
        </div>
      </div>
    </button>
  )
}
