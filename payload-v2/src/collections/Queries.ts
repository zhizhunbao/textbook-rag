import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isOwnerOrAdmin } from '../access/isOwnerOrAdmin'
import { afterChangeHook } from '../hooks/queries/afterChange'

/**
 * Queries — query execution logs.
 * Aligned with engine-v2/query_engine/ module.
 */
export const Queries: CollectionConfig = {
  slug: 'queries',
  hooks: {
    afterChange: [afterChangeHook],
  },
  admin: {
    useAsTitle: 'question',
    defaultColumns: ['question', 'user', 'provider', 'latencyMs', 'createdAt'],
    group: 'Analytics',
  },
  access: {
    read: isOwnerOrAdmin,
    create: () => true,   // Engine writes logs
    update: isAdmin,
    delete: isOwnerOrAdmin,
  },
  fields: [
    {
      name: 'user',
      type: 'relationship',
      relationTo: 'users',
    },
    {
      name: 'sessionId',
      type: 'text',
      index: true,
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
