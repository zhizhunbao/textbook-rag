/**
 * access/isAdminOrApiKey — allows admin users OR engine API key auth.
 *
 * Engine (Python) calls Payload REST API to update ingest-tasks and books
 * during the pipeline. Since Engine is a trusted server-side service,
 * we authenticate it via a shared secret PAYLOAD_API_KEY.
 *
 * Usage in collection access:
 *   update: isAdminOrApiKey,
 *
 * Env: ENGINE_API_KEY — must match the key sent by Engine in
 *   Authorization: Bearer <key>
 */

import type { Access } from 'payload'

const ENGINE_API_KEY = process.env.ENGINE_API_KEY || process.env.PAYLOAD_API_KEY || ''

export const isAdminOrApiKey: Access = ({ req }) => {
  // Admin or editor user — normal session auth
  const role = req.user?.role
  if (role === 'admin' || role === 'editor') return true

  // Engine API key — Bearer token in Authorization header
  if (ENGINE_API_KEY) {
    const authHeader = req.headers.get?.('authorization')
      ?? (req.headers as any)?.authorization
      ?? ''
    if (authHeader === `Bearer ${ENGINE_API_KEY}`) return true
    if (authHeader === `users API-Key ${ENGINE_API_KEY}`) return true
  }

  return false
}
