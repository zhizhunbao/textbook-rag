import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'

export const PipelineTasks: CollectionConfig = {
  slug: 'pipeline-tasks',
  admin: {
    useAsTitle: 'taskType',
    defaultColumns: ['taskType', 'book', 'status', 'progress', 'startedAt'],
    group: 'Admin',
  },
  access: {
    read: isAdmin,
    create: isAdmin,
    update: isAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'taskType',
      type: 'select',
      required: true,
      options: [
        { label: 'Ingest', value: 'ingest' },
        { label: 'Vectorize', value: 'vectorize' },
        { label: 'Reindex', value: 'reindex' },
        { label: 'Full', value: 'full' },
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
