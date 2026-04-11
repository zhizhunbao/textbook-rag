import type { Access } from 'payload'

export const isOwnerOrAdmin: Access = ({ req: { user }, id }) => {
  if (!user) return false
  if (user.role === 'admin') return true
  return { id: { equals: user.id } }
}
