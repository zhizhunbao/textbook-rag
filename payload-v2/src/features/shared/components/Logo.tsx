'use client'

import { cn } from '@/features/shared/utils'

/**
 * Logo — inline SVG ConsultRAG logo.
 *
 * Design: magnifying glass with knowledge-graph / neural-network inside.
 * Theme: light mode → navy icon on light bg; dark mode → cyan icon on dark bg.
 * Single SVG component, zero external image files, infinite scalability.
 */
export default function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('shrink-0', className)}
      aria-label="ConsultRAG logo"
    >
      <defs>
        {/* Light-mode gradient: navy → indigo */}
        <linearGradient id="cr-light" x1="25" y1="25" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#1e293b" />
          <stop offset="100%" stopColor="#312e81" />
        </linearGradient>
        {/* Dark-mode gradient: cyan → teal */}
        <linearGradient id="cr-dark" x1="25" y1="25" x2="100" y2="100" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>

      {/* Background rounded square */}
      <rect
        width="120" height="120" rx="26"
        className="fill-[#f1f5f9] dark:fill-[#0f172a]"
      />

      {/* ── Magnifying glass ── */}
      {/* Use two identical groups: one for light, one for dark, toggled via CSS */}

      {/* LIGHT mode group */}
      <g stroke="url(#cr-light)" className="dark:opacity-0 opacity-100 transition-opacity">
        <circle cx="52" cy="50" r="28" strokeWidth="5" fill="none" />
        <circle cx="52" cy="50" r="21" strokeWidth="3" fill="none" opacity="0.4" />
        <line x1="73" y1="72" x2="95" y2="94" strokeWidth="7" strokeLinecap="round" />
      </g>

      {/* DARK mode group */}
      <g stroke="url(#cr-dark)" className="opacity-0 dark:opacity-100 transition-opacity">
        <circle cx="52" cy="50" r="28" strokeWidth="5" fill="none" />
        <circle cx="52" cy="50" r="21" strokeWidth="3" fill="none" opacity="0.4" />
        <line x1="73" y1="72" x2="95" y2="94" strokeWidth="7" strokeLinecap="round" />
      </g>

      {/* ── Knowledge graph (neural network nodes + edges) ── */}

      {/* LIGHT mode graph */}
      <g fill="url(#cr-light)" stroke="url(#cr-light)" strokeWidth="1.8" className="dark:opacity-0 opacity-100 transition-opacity">
        {/* Center node */}
        <circle cx="52" cy="50" r="4" stroke="none" />
        {/* Spokes */}
        <line x1="52" y1="50" x2="52" y2="35" />
        <line x1="52" y1="50" x2="63" y2="39" />
        <line x1="52" y1="50" x2="67" y2="50" />
        <line x1="52" y1="50" x2="63" y2="61" />
        <line x1="52" y1="50" x2="52" y2="65" />
        <line x1="52" y1="50" x2="41" y2="61" />
        <line x1="52" y1="50" x2="37" y2="50" />
        <line x1="52" y1="50" x2="41" y2="39" />
        {/* Outer nodes */}
        <circle cx="52" cy="35" r="2.5" stroke="none" />
        <circle cx="63" cy="39" r="2.5" stroke="none" />
        <circle cx="67" cy="50" r="2.5" stroke="none" />
        <circle cx="63" cy="61" r="2.5" stroke="none" />
        <circle cx="52" cy="65" r="2.5" stroke="none" />
        <circle cx="41" cy="61" r="2.5" stroke="none" />
        <circle cx="37" cy="50" r="2.5" stroke="none" />
        <circle cx="41" cy="39" r="2.5" stroke="none" />
        {/* Mesh edges between adjacent nodes */}
        <line x1="52" y1="35" x2="63" y2="39" opacity="0.45" />
        <line x1="63" y1="39" x2="67" y2="50" opacity="0.45" />
        <line x1="67" y1="50" x2="63" y2="61" opacity="0.45" />
        <line x1="63" y1="61" x2="52" y2="65" opacity="0.45" />
        <line x1="52" y1="65" x2="41" y2="61" opacity="0.45" />
        <line x1="41" y1="61" x2="37" y2="50" opacity="0.45" />
        <line x1="37" y1="50" x2="41" y2="39" opacity="0.45" />
        <line x1="41" y1="39" x2="52" y2="35" opacity="0.45" />
      </g>

      {/* DARK mode graph */}
      <g fill="url(#cr-dark)" stroke="url(#cr-dark)" strokeWidth="1.8" className="opacity-0 dark:opacity-100 transition-opacity">
        {/* Center node */}
        <circle cx="52" cy="50" r="4" stroke="none" />
        {/* Spokes */}
        <line x1="52" y1="50" x2="52" y2="35" />
        <line x1="52" y1="50" x2="63" y2="39" />
        <line x1="52" y1="50" x2="67" y2="50" />
        <line x1="52" y1="50" x2="63" y2="61" />
        <line x1="52" y1="50" x2="52" y2="65" />
        <line x1="52" y1="50" x2="41" y2="61" />
        <line x1="52" y1="50" x2="37" y2="50" />
        <line x1="52" y1="50" x2="41" y2="39" />
        {/* Outer nodes */}
        <circle cx="52" cy="35" r="2.5" stroke="none" />
        <circle cx="63" cy="39" r="2.5" stroke="none" />
        <circle cx="67" cy="50" r="2.5" stroke="none" />
        <circle cx="63" cy="61" r="2.5" stroke="none" />
        <circle cx="52" cy="65" r="2.5" stroke="none" />
        <circle cx="41" cy="61" r="2.5" stroke="none" />
        <circle cx="37" cy="50" r="2.5" stroke="none" />
        <circle cx="41" cy="39" r="2.5" stroke="none" />
        {/* Mesh edges between adjacent nodes */}
        <line x1="52" y1="35" x2="63" y2="39" opacity="0.45" />
        <line x1="63" y1="39" x2="67" y2="50" opacity="0.45" />
        <line x1="67" y1="50" x2="63" y2="61" opacity="0.45" />
        <line x1="63" y1="61" x2="52" y2="65" opacity="0.45" />
        <line x1="52" y1="65" x2="41" y2="61" opacity="0.45" />
        <line x1="41" y1="61" x2="37" y2="50" opacity="0.45" />
        <line x1="37" y1="50" x2="41" y2="39" opacity="0.45" />
        <line x1="41" y1="39" x2="52" y2="35" opacity="0.45" />
      </g>

      {/* Center glow in dark mode */}
      <circle cx="52" cy="50" r="6" fill="url(#cr-dark)" opacity="0.3" className="opacity-0 dark:opacity-30" />
    </svg>
  )
}
