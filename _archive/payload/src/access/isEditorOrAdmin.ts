import type { Access } from 'payload'

export const isEditorOrAdmin: Access = ({ req: { user } }) => {
  return user?.role === 'admin' || user?.role === 'editor'
}
