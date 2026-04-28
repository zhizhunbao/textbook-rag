/**
 * UserDocuments Collection — User-uploaded private PDFs for consulting.
 *
 * Slug: user-documents
 * Each document belongs to a user + persona pair, stored in an isolated
 * ChromaDB collection (user_{userId}_{personaSlug}).
 *
 * Storage: data/raw_pdfs/user_private/{userId}/ (via PdfUploads-style upload)
 */

import path from 'path'
import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'

export const UserDocuments: CollectionConfig = {
  slug: 'user-documents',
  labels: {
    singular: 'User Document',
    plural: 'User Documents',
  },
  admin: {
    useAsTitle: 'filename',
    defaultColumns: ['filename', 'user', 'persona', 'status', 'chunkCount', 'createdAt'],
    group: 'Consulting',
  },
  access: {
    // Users can only see their own documents; admins can see all
    read: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
    // Any authenticated user can upload
    create: ({ req: { user } }) => !!user,
    // Only the owner or admin can update
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
  upload: {
    staticDir: path.resolve(process.cwd(), '../data/raw_pdfs/user_private'),
    mimeTypes: ['application/pdf'],
  },
  fields: [
    // ── Owner ──
    {
      name: 'user',
      type: 'relationship',
      relationTo: 'users',
      required: true,
      index: true,
      admin: { position: 'sidebar' },
    },
    // ── Persona binding ──
    {
      name: 'persona',
      type: 'relationship',
      relationTo: 'consulting-personas',
      required: true,
      admin: {
        position: 'sidebar',
        description: 'Which consulting role this document is bound to',
      },
    },
    // ── Processing status ──
    {
      name: 'status',
      type: 'select',
      defaultValue: 'pending',
      options: [
        { label: 'Pending', value: 'pending' },
        { label: 'Processing', value: 'processing' },
        { label: 'Indexed', value: 'indexed' },
        { label: 'Error', value: 'error' },
      ],
      admin: { position: 'sidebar' },
    },
    {
      name: 'chromaCollection',
      type: 'text',
      admin: {
        readOnly: true,
        description: 'Auto-generated: user_{userId}_{personaSlug}',
      },
    },
    {
      name: 'chunkCount',
      type: 'number',
      defaultValue: 0,
      admin: { readOnly: true },
    },
    {
      name: 'error',
      type: 'textarea',
      admin: {
        readOnly: true,
        description: 'Error message if processing failed',
      },
    },
    // ── Descriptive fields ──
    {
      name: 'description',
      type: 'text',
      admin: { description: 'Optional description of the document' },
    },
  ],
}
