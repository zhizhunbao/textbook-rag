'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'

/**
 * UserMenu — header dropdown showing user info + logout
 * Uses Payload's /api/users REST endpoints via AuthProvider
 */
export default function UserMenu() {
  const { user, logout, status } = useAuth()
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  if (!user || status !== 'loggedIn') {
    return (
      <a
        href="/login"
        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-white/8 text-xs font-medium transition-all duration-150"
      >
        Login
      </a>
    )
  }

  const initials = (user.displayName ?? user.email)
    .split(/[\s@]+/)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('')

  const displayLabel = user.displayName || user.email.split('@')[0]

  const roleBadgeColors: Record<string, string> = {
    admin: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    editor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    reader: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  }

  async function handleLogout() {
    try {
      await logout()
    } catch {
      // ignore
    }
    window.location.href = '/login'
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 transition-all duration-150 hover:bg-white/8"
      >
        {/* Avatar circle */}
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-linear-to-br from-brand-400 to-accent-500 text-[11px] font-bold text-white shadow-sm">
          {initials}
        </span>
        <span className="hidden text-sm font-medium text-slate-200 sm:inline">
          {displayLabel}
        </span>
        {/* Chevron */}
        <svg
          className={`h-3.5 w-3.5 text-slate-500 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1.5 w-56 rounded-xl border border-white/10 bg-surface-800 p-1.5 shadow-xl shadow-black/40 backdrop-blur-xl">
          {/* User info section */}
          <div className="border-b border-white/8 px-3 py-2.5">
            <div className="text-sm font-semibold text-white">{displayLabel}</div>
            <div className="mt-0.5 text-xs text-slate-400">{user.email}</div>
            <span
              className={`mt-1.5 inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${roleBadgeColors[user.role] ?? roleBadgeColors.reader}`}
            >
              {user.role}
            </span>
          </div>

          {/* Menu items */}
          <div className="mt-1 space-y-0.5">
            <a
              href="/admin"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-300 transition hover:bg-white/8 hover:text-white"
            >
              <svg className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 0 1 1.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 0 1-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 0 1-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 0 1 .12-1.45l.773-.773a1.125 1.125 0 0 1 1.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
              </svg>
              Admin Panel
            </a>
            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-300 transition hover:bg-rose-500/10 hover:text-rose-300"
            >
              <svg className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
              </svg>
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
