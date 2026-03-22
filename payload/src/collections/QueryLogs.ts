import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isOwnerOrAdmin } from '../access/isOwnerOrAdmin'

export const QueryLogs: CollectionConfig = {
  slug: 'query-logs',
  admin: {
    useAsTitle: 'question',
    defaultColumns: ['question', 'user', 'provider', 'latencyMs', 'createdAt'],
    group: 'Analytics',
  },
  access: {
    read: isOwnerOrAdmin,
    create: () => true,   // Engine writes logs
    update: isAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'user',
      type: 'relationship',
      relationTo: 'users',
    },
    {
      name: 'question',
      type: 'text',
      required: true,
    },
    {
      name: 'answer',
      type: 'textarea',
    },
    {
      name: 'sources',
      type: 'json',
    },
    {
      name: 'trace',
      type: 'json',
    },
    {
      name: 'warnings',
      type: 'json',
    },
    {
      name: 'model',
      type: 'text',
    },
    {
      name: 'provider',
      type: 'select',
      options: [
        { label: 'Ollama', value: 'ollama' },
        { label: 'Azure OpenAI', value: 'azure_openai' },
      ],
    },
    {
      name: 'latencyMs',
      type: 'number',
    },
    {
      name: 'config',
      type: 'json',
    },
  ],
}
