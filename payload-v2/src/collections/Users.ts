import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isOwnerOrAdmin } from '../access/isOwnerOrAdmin'
import { sanitizeNewUser } from '../hooks/users/sanitizeNewUser'

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
    create: () => true,  // GO-MU-03: allow self-registration (sanitizeNewUser hook enforces safe defaults)
    update: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      // Users collection: the doc itself IS the user, so match by id
      return { id: { equals: user.id } }
    },
    delete: isAdmin,
  },
  hooks: {
    beforeChange: [sanitizeNewUser],
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
    // ── Billing tier (GO-MON-03) ──
    {
      name: 'tier',
      type: 'select',
      defaultValue: 'free',
      required: true,
      options: [
        { label: 'Free', value: 'free' },
        { label: 'Pro', value: 'pro' },
      ],
      access: {
        update: ({ req: { user } }) => user?.role === 'admin',  // only admin/webhook can upgrade
      },
      admin: { position: 'sidebar' },
    },
    {
      name: 'stripeCustomerId',
      type: 'text',
      unique: true,
      admin: {
        position: 'sidebar',
        readOnly: true,
        description: 'Stripe Customer ID — set by webhook',
      },
      access: {
        update: ({ req: { user } }) => user?.role === 'admin',
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
