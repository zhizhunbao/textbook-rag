/** sanitizeNewUser — beforeChange hook to force safe defaults on self-registration.
 *
 * When a non-admin creates a user (i.e. self-registration), force:
 *   - role = 'reader'
 *   - tier = 'free' (GO-MON-03)
 *   - isOnboarded = false
 *   - selectedPersona = null
 *
 * This prevents privilege escalation via crafted POST /api/users requests.
 */

import type { CollectionBeforeChangeHook } from 'payload'

export const sanitizeNewUser: CollectionBeforeChangeHook = ({
  data,
  operation,
  req,
}) => {
  // Only apply on create operations
  if (operation !== 'create') return data

  // Admin creating a user can set any fields
  const isAdmin = req.user?.role === 'admin'
  if (isAdmin) return data

  // Self-registration: force safe defaults
  return {
    ...data,
    role: 'reader',
    tier: 'free',
    stripeCustomerId: null,
    isOnboarded: false,
    selectedPersona: null,
  }
}
