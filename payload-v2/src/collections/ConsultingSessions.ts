/**
 * ConsultingSessions Collection — Persona-bound consulting conversations.
 *
 * Slug: consulting-sessions
 * Each session belongs to one user and one consulting persona.
 */

import type { CollectionConfig } from 'payload'

export const ConsultingSessions: CollectionConfig = {
  slug: 'consulting-sessions',
  labels: {
    singular: 'Consulting Session',
    plural: 'Consulting Sessions',
  },
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'user', 'persona', 'createdAt'],
    group: 'Consulting',
  },
  access: {
    read: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
    create: ({ req: { user } }) => !!user,
    update: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
    delete: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
  },
  fields: [
    {
      name: 'user',
      type: 'relationship',
      relationTo: 'users',
      required: true,
      index: true,
      admin: { position: 'sidebar' },
    },
    {
      name: 'persona',
      type: 'relationship',
      relationTo: 'consulting-personas',
      required: true,
      index: true,
      admin: { position: 'sidebar' },
    },
    {
      name: 'title',
      type: 'text',
      required: true,
    },
  ],
}

