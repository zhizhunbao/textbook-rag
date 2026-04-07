import type { CollectionConfig } from 'payload'
import { isAdminOrApiKey } from '../access/isAdminOrApiKey'

export const Chunks: CollectionConfig = {
  slug: 'chunks',
  admin: {
    useAsTitle: 'chunkId',
    defaultColumns: ['chunkId', 'book', 'contentType', 'pageNumber', 'vectorized'],
    group: 'Content',
  },
  access: {
    read: () => true,
    create: isAdminOrApiKey,
    update: isAdminOrApiKey,
    delete: isAdminOrApiKey,
  },
  fields: [
    {
      name: 'chunkId',
      type: 'text',
      required: true,
      unique: true,
      index: true,
    },
    {
      name: 'book',
      type: 'relationship',
      relationTo: 'books',
      index: true,
    },
    {
      name: 'chapter',
      type: 'relationship',
      relationTo: 'chapters',
    },
    {
      name: 'text',
      type: 'textarea',
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
        { label: 'Code', value: 'code' },
      ],
    },
    {
      name: 'readingOrder',
      type: 'number',
      defaultValue: 0,
    },
    {
      name: 'pageNumber',
      type: 'number',
      defaultValue: 0,
      index: true,
    },
    {
      name: 'sourceLocators',
      type: 'json',
      // [{x0, y0, x1, y1, page}]
    },
    {
      name: 'vectorized',
      type: 'checkbox',
      defaultValue: false,
    },
  ],
}
