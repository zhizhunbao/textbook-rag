import type { CollectionConfig } from 'payload'
import { afterChangeHook } from '../hooks/books/afterChange'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

export const Books: CollectionConfig = {
  slug: 'books',
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'category', 'status', 'chunkCount', 'updatedAt'],
    group: 'Content',
  },
  access: {
    read: () => true,
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  // PDF upload is optional — books synced from engine don't have uploads
  // For new books uploaded via admin, use the pdfPath field
  hooks: {
    afterChange: [afterChangeHook],
  },
  fields: [
    {
      name: 'engineBookId',
      type: 'text',
      unique: true,
      index: true,
      admin: { description: 'Maps to engine SQLite book_id (e.g. ramalho_fluent_python)' },
    },
    {
      name: 'title',
      type: 'text',
      required: true,
    },
    {
      name: 'authors',
      type: 'text',
    },
    {
      name: 'isbn',
      type: 'text',
    },
    {
      name: 'category',
      type: 'select',
      required: true,
      defaultValue: 'textbook',
      options: [
        { label: 'Textbook', value: 'textbook' },
        { label: 'EC Dev', value: 'ecdev' },
        { label: 'Real Estate', value: 'real_estate' },
      ],
    },
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
      admin: { readOnly: true },
    },
    {
      name: 'chunkCount',
      type: 'number',
      admin: { readOnly: true },
    },
    {
      name: 'metadata',
      type: 'json',
      admin: { condition: (_, siblingData) => siblingData?.status === 'indexed' },
    },
  ],
}
