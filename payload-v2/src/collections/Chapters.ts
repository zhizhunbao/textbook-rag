import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'

export const Chapters: CollectionConfig = {
  slug: 'chapters',
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'book', 'chapterKey'],
    group: 'Content',
  },
  access: {
    read: isAdmin,  // GO-MU-08: was () => true
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isEditorOrAdmin,
  },
  fields: [
    {
      name: 'book',
      type: 'relationship',
      relationTo: 'books',
      required: true,
      index: true,
    },
    {
      name: 'chapterKey',
      type: 'text',
      required: true,
    },
    {
      name: 'title',
      type: 'text',
      required: true,
    },
    {
      name: 'contentType',
      type: 'select',
      defaultValue: 'text',
      options: [
        { label: 'Text', value: 'text' },
        { label: 'Table', value: 'table' },
        { label: 'Image', value: 'image' },
        { label: 'Equation', value: 'equation' },
      ],
    },
  ],
}
