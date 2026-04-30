/**
 * ConsultingSidebar — Left sidebar for consulting mode.
 *
 * Sprint C4-06: Integrates UserDocsPanel + persona info into the chat layout.
 * Shows the user's private documents for the active persona.
 */

'use client'

import { cn } from '@/features/shared/utils'
import UserDocsPanel from './consulting/UserDocsPanel'

// ── Types ──

interface ConsultingSidebarProps {
  personaSlug: string | null
  personaName: string | null
  onClose: () => void
  style?: React.CSSProperties
  className?: string
}

// ── Component ──

export default function ConsultingSidebar({
  personaSlug,
  personaName,
  onClose,
  style,
  className,
}: ConsultingSidebarProps) {
  if (!personaSlug) {
    return (
      <div
        className={cn(
          'flex flex-col h-full border-r border-border bg-card overflow-hidden',
          className,
        )}
        style={style}
      >
        <SidebarHeader title="Consulting" onClose={onClose} />
        <div className="flex-1 flex items-center justify-center p-6">
          <p className="text-xs text-muted-foreground text-center">
            Select a consulting persona to manage your private documents.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-col h-full border-r border-border bg-card overflow-hidden',
        className,
      )}
      style={style}
    >
      <SidebarHeader
        title={personaName ?? 'Consulting'}
        subtitle="Private Documents"
        onClose={onClose}
      />

      {/* Scrollable content area */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        <UserDocsPanel
          personaSlug={personaSlug}
          personaName={personaName ?? undefined}
        />
      </div>
    </div>
  )
}

// ── Sidebar Header sub-component ──

function SidebarHeader({
  title,
  subtitle,
  onClose,
}: {
  title: string
  subtitle?: string
  onClose: () => void
}) {
  return (
    <div className="shrink-0 flex items-center gap-2 px-4 py-3 border-b border-border">
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-foreground truncate flex items-center gap-2">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="text-primary shrink-0"
          >
            <path d="M20 7h-9m9 10h-9M4 7h.01M4 17h.01M4 12h16" />
          </svg>
          {title}
        </h3>
        {subtitle && (
          <p className="text-[10px] text-muted-foreground mt-0.5">{subtitle}</p>
        )}
      </div>
      <button
        type="button"
        onClick={onClose}
        className="flex items-center justify-center h-7 w-7 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        title="Close sidebar"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 18 18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  )
}
