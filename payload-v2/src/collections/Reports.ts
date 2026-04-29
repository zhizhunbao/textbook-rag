/**
 * Reports Collection — Generated analysis reports from chat sessions.
 *
 * Slug: reports
 * Each report is generated from a chat session's messages + evaluation data.
 * Contains LLM-generated Markdown content with quality assessment metrics.
 *
 * Admin group: Reports
 */

import type { CollectionConfig } from 'payload'
import { isLoggedIn } from '../access/isLoggedIn'

// ============================================================
// Config
// ============================================================
export const Reports: CollectionConfig = {
  slug: 'reports',
  labels: {
    singular: 'Report',
    plural: 'Reports',
  },
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'status', 'model', 'createdAt'],
    group: 'Reports',
  },
  access: {
    // Users can only read their own reports; admins can read all
    read: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
    // Any authenticated user can create (engine writes on behalf of user)
    create: isLoggedIn,  // GO-MU-09: was () => true
    // Only owner or admin can update
    update: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
    // Only owner or admin can delete
    delete: ({ req: { user } }) => {
      if (!user) return false
      if (user.role === 'admin') return true
      return { user: { equals: user.id } }
    },
  },
  fields: [
    // ── Owner ──
    {
      name: 'user',
      type: 'relationship',
      relationTo: 'users',
      admin: { description: 'Owner of this report' },
    },

    // ── Report content ──
    {
      name: 'title',
      type: 'text',
      required: true,
      admin: { description: 'Report title (auto-generated from session)' },
    },
    {
      name: 'content',
      type: 'textarea',
      admin: { description: 'Full Markdown content of the report' },
    },

    // ── Session reference ──
    {
      name: 'sessionId',
      type: 'text',
      required: true,
      index: true,
      admin: { description: 'ID of the chat session this report was generated from' },
    },
    {
      name: 'sessionTitle',
      type: 'text',
      admin: { description: 'Title of the source chat session' },
    },

    // ── LLM metadata ──
    {
      name: 'model',
      type: 'text',
      admin: { description: 'LLM model used for report generation' },
    },

    // ── Evaluation summary ──
    {
      name: 'stats',
      type: 'json',
      admin: {
        description: 'Aggregated stats: { messageCount, sourceCount, avgScores, questionDepths }',
      },
    },

    // ── Status ──
    {
      name: 'status',
      type: 'select',
      required: true,
      defaultValue: 'generating',
      options: [
        { label: 'Generating', value: 'generating' },
        { label: 'Completed', value: 'completed' },
        { label: 'Failed', value: 'failed' },
      ],
      admin: { description: 'Report generation status' },
    },
  ],
}
