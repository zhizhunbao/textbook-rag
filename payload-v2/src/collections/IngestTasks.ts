import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isAdminOrApiKey } from '../access/isAdminOrApiKey'

/**
 * IngestTasks — tracks ingestion pipeline progress.
 * Aligned with engine-v2/ingestion/ module.
 */
export const IngestTasks: CollectionConfig = {
  slug: 'ingest-tasks',
  admin: {
    useAsTitle: 'taskType',
    defaultColumns: ['taskType', 'book', 'status', 'progress', 'startedAt'],
    group: 'Admin',
  },
  access: {
    read: isAdmin,
    create: isAdmin,
    update: isAdminOrApiKey,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'taskType',
      type: 'select',
      required: true,
      options: [
        { label: 'Full', value: 'full' },
        { label: 'Parse', value: 'parse' },
        { label: 'Ingest', value: 'ingest' },
      ],
    },
    {
      name: 'book',
      type: 'relationship',
      relationTo: 'books',
    },
    {
      name: 'status',
      type: 'select',
      defaultValue: 'queued',
      options: [
        { label: 'Queued', value: 'queued' },
        { label: 'Running', value: 'running' },
        { label: 'Done', value: 'done' },
        { label: 'Error', value: 'error' },
      ],
    },
    {
      name: 'progress',
      type: 'number',
      defaultValue: 0,
      min: 0,
      max: 100,
    },
    {
      name: 'log',
      type: 'textarea',
    },
    {
      name: 'error',
      type: 'textarea',
    },
    {
      name: 'startedAt',
      type: 'date',
    },
    {
      name: 'finishedAt',
      type: 'date',
    },
  ],
}
