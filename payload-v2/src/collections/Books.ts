import type { CollectionConfig } from 'payload'
import { afterChangeHook } from '../hooks/books/afterChange'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'
import { isAdminOrApiKey } from '../access/isAdminOrApiKey'
import { importUrlEndpoint, syncEngineEndpoint } from './endpoints'

export const Books: CollectionConfig = {
  slug: 'books',
  endpoints: [syncEngineEndpoint, importUrlEndpoint],
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'authors', 'category', 'subcategory', 'status', 'chunkCount', 'updatedAt'],
    group: 'Content',
  },
  access: {
    read: isEditorOrAdmin,  // GO-MU-08: was () => true
    create: isEditorOrAdmin,
    update: isAdminOrApiKey,
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
      admin: { description: 'Maps to engine book_id (e.g. ramalho_fluent_python)' },
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
      name: 'coverImage',
      type: 'upload',
      relationTo: 'media',
      admin: { description: 'Book cover image (auto-generated or manually uploaded)' },
    },
    {
      name: 'pdfMedia',
      type: 'upload',
      relationTo: 'pdf-uploads',
      admin: { description: 'Uploaded PDF file for MinerU parsing → ingestion pipeline' },
    },
    {
      name: 'category',
      type: 'text',
      required: true,
      defaultValue: 'textbooks',
      admin: {
        description: 'Book category (auto-classified by LLM, user-editable). E.g. textbook, ecdev, real_estate, research_paper',
      },
    },
    {
      name: 'subcategory',
      type: 'text',
      admin: { description: 'Sub-classification within category (e.g. Python, NLP, Policy)' },
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
    // ── Pipeline stage status (2 stages) ──
    // parse:  MinerU PDF parsing → content_list.json
    // ingest: MinerUReader → IngestionPipeline → ChromaDB + Payload sync
    {
      name: 'pipeline',
      type: 'group',
      admin: {
        description: 'Processing pipeline stage status (parse → ingest)',
      },
      fields: [
        {
          name: 'parse',
          type: 'select',
          defaultValue: 'pending',
          options: [
            { label: 'Pending', value: 'pending' },
            { label: 'Done', value: 'done' },
            { label: 'Error', value: 'error' },
          ],
          admin: { readOnly: true, width: '50%' },
        },
        {
          name: 'ingest',
          type: 'select',
          defaultValue: 'pending',
          options: [
            { label: 'Pending', value: 'pending' },
            { label: 'Done', value: 'done' },
            { label: 'Error', value: 'error' },
          ],
          admin: { readOnly: true, width: '50%' },
        },
        {
          name: 'parseOutput',
          type: 'json',
          admin: {
            readOnly: true,
            description: 'MinerU parse results: output path, content_list count, images count, sample entries',
          },
        },
        {
          name: 'ingestOutput',
          type: 'json',
          admin: {
            readOnly: true,
            description: 'Ingestion results: node count, ChromaDB collection, chunk push stats',
          },
        },
      ],
    },
    {
      name: 'metadata',
      type: 'json',
      admin: { condition: (_, siblingData) => siblingData?.status === 'indexed' },
    },
  ],
}
