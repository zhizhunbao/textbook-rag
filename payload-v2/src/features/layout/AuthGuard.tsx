/**
 * AuthGuard — Client-side route guard for consulting onboarding flow.
 *
 * Logic:
 *   - /login and /onboarding routes are always allowed (no guard)
 *   - Not logged in → redirect to /login
 *   - Logged in + admin → always allowed
 *   - Logged in + not onboarded → redirect to /onboarding
 *   - Logged in + onboarded → render children
 */

'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/features/shared/AuthProvider'

/** Routes that should never trigger a guard redirect */
const UNGUARDED_ROUTES = ['/login', '/onboarding']

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, status } = useAuth()
  const pathname = usePathname()
  const [allowed, setAllowed] = useState(false)

  useEffect(() => {
    // Still loading auth state — don't redirect yet
    if (status === undefined) return

    // Unguarded routes are always allowed
    if (UNGUARDED_ROUTES.some((r) => pathname.startsWith(r))) {
      setAllowed(true)
      return
    }

    // Not logged in → /login
    if (status === 'loggedOut' || !user) {
      window.location.href = '/login'
      return
    }

    // Admin users bypass onboarding guard
    if (user.role === 'admin') {
      setAllowed(true)
      return
    }

    // Not onboarded → /onboarding
    if (!user.isOnboarded) {
      window.location.href = '/onboarding'
      return
    }

    // All checks passed
    setAllowed(true)
  }, [status, user, pathname])

  // Show nothing while auth is loading or redirecting
  if (!allowed) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  return <>{children}</>
}
