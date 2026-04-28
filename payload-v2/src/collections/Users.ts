import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isOwnerOrAdmin } from '../access/isOwnerOrAdmin'

export const Users: CollectionConfig = {
  slug: 'users',
  auth: true,  // Payload built-in auth: email + password + JWT
  admin: {
    useAsTitle: 'email',
    defaultColumns: ['email', 'displayName', 'role', 'createdAt'],
    group: 'Admin',
  },
  access: {
    read: isOwnerOrAdmin,
    create: isAdmin,
    update: isOwnerOrAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'displayName',
      type: 'text',
    },
    {
      name: 'role',
      type: 'select',
      defaultValue: 'reader',
      required: true,
      options: [
        { label: 'Admin', value: 'admin' },
        { label: 'Editor', value: 'editor' },
        { label: 'Reader', value: 'reader' },
      ],
      access: {
        update: ({ req: { user } }) => user?.role === 'admin',  // only admin can change role
      },
    },
    // ── Consulting onboarding fields ──
    {
      name: 'selectedPersona',
      type: 'relationship',
      relationTo: 'consulting-personas',
      admin: { position: 'sidebar' },
    },
    {
      name: 'isOnboarded',
      type: 'checkbox',
      defaultValue: false,
      admin: { position: 'sidebar' },
    },
  ],
}
