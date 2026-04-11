import type { CollectionConfig } from 'payload'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

export const PromptModes: CollectionConfig = {
  slug: 'prompt-modes',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'slug', 'isDefault', 'updatedAt'],
    group: 'Settings',
  },
  access: {
    read: () => true,        // users need to fetch modes
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      admin: { description: 'Display name (e.g. "Learning Mode")' },
    },
    {
      name: 'slug',
      type: 'text',
      required: true,
      unique: true,
      index: true,
      admin: { description: 'URL-safe identifier (e.g. "learning")' },
    },
    {
      name: 'description',
      type: 'text',
      required: true,
      admin: { description: 'English description shown to users' },
    },
    {
      name: 'systemPrompt',
      type: 'textarea',
      required: true,
      admin: {
        description: 'English system prompt sent to the LLM',
        rows: 8,
      },
    },
    {
      name: 'icon',
      type: 'text',
      admin: { description: 'Lucide icon identifier (e.g. "lightbulb", "book", "chart")' },
    },
    {
      name: 'isDefault',
      type: 'checkbox',
      defaultValue: false,
      admin: { description: 'If checked, this mode is pre-selected for new conversations' },
    },
  ],
}
