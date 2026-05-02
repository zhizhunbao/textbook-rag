/**
 * ChatMessages — Persists individual chat messages to Payload CMS.
 *
 * Each message belongs to a ChatSession. User messages and assistant
 * responses (with sources/trace) are stored as separate documents.
 * Enables the evaluation module to query all user questions for
 * semantic deduplication.
 *
 * Admin group: Chat
 */

import type { CollectionConfig } from 'payload'

export const ChatMessages: CollectionConfig = {
  slug: 'chat-messages',
  admin: {
    defaultColumns: ['session', 'role', 'content', 'createdAt'],
    group: 'Chat',
  },
  access: {
    // Read: inherit from session ownership — user can read messages
    // for sessions they own; admins can read all
    read: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { 'session.user': { equals: user.id } }
    },
    // Any authenticated user can create
    create: ({ req: { user } }) => !!user,
    // Owner can update their own messages (e.g. patch queryId); admins can update all
    update: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { 'session.user': { equals: user.id } }
    },
    delete: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { 'session.user': { equals: user.id } }
    },
  },
  hooks: {
    afterChange: [
      ({ doc, operation }) => {
        console.log(`[ChatMessages] ${operation}:`, { id: doc.id, session: doc.session, role: doc.role, contentLen: doc.content?.length ?? 0 })
        return doc
      },
    ],
  },
  fields: [
    {
      name: 'session',
      type: 'relationship',
      relationTo: 'chat-sessions',
      required: true,
      index: true,
    },
    {
      name: 'role',
      type: 'select',
      required: true,
      options: [
        { label: 'User', value: 'user' },
        { label: 'Assistant', value: 'assistant' },
      ],
    },
    {
      name: 'content',
      type: 'textarea',
      required: true,
    },
    {
      name: 'sources',
      type: 'json',
      label: 'Source citations (assistant only)',
    },
    {
      name: 'trace',
      type: 'json',
      label: 'Query trace (assistant only)',
    },
    {
      name: 'queryId',
      type: 'number',
      label: 'Linked Queries record ID (assistant only)',
      index: true,
      admin: { description: 'Payload Queries doc ID for inline evaluation' },
    },
  ],
}
