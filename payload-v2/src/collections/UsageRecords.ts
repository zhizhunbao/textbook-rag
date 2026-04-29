/**
 * UsageRecords Collection — Audit log of per-user API usage for billing.
 *
 * Slug: usage-records
 *
 * GO-MON-02: Each record represents one billable action (query, ingest, etc.).
 * Phase 1 simplification: count-based metering (1 record = 1 action),
 * no token-level granularity. Token fields will be added in Phase 2
 * once per-provider token extraction is reliable.
 *
 * Admin group: Billing
 */

import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isOwnerOrAdmin } from '../access/isOwnerOrAdmin'

export const UsageRecords: CollectionConfig = {
  slug: 'usage-records',
  labels: {
    singular: 'Usage Record',
    plural: 'Usage Records',
  },
  admin: {
    useAsTitle: 'endpoint',
    defaultColumns: ['user', 'endpoint', 'model', 'createdAt'],
    group: 'Billing',
  },
  access: {
    read: isOwnerOrAdmin,     // users see their own; admin sees all
    create: isAdmin,          // only Engine (via API key → admin) writes
    update: isAdmin,          // immutable audit log — admin only
    delete: isAdmin,          // admin cleanup only
  },
  fields: [
    // ── Who ──
    {
      name: 'user',
      type: 'relationship',
      relationTo: 'users',
      required: true,
      index: true,
    },
    // ── What ──
    {
      name: 'endpoint',
      type: 'text',
      required: true,
      index: true,
      admin: {
        description: 'API endpoint path, e.g. /engine/consulting/query',
      },
    },
    {
      name: 'action',
      type: 'select',
      required: true,
      defaultValue: 'query',
      options: [
        { label: 'Query', value: 'query' },
        { label: 'Document Ingest', value: 'ingest' },
      ],
      index: true,
    },
    // ── Context ──
    {
      name: 'model',
      type: 'text',
      admin: {
        description: 'LLM model used, e.g. qwen2.5:1.5b',
      },
    },
    {
      name: 'personaSlug',
      type: 'text',
      admin: {
        description: 'Consulting persona slug, if applicable',
      },
    },
  ],
}
