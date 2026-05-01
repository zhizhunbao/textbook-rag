/**
 * ConsultingPersonas Collection — Predefined consulting role definitions.
 *
 * Slug: consulting-personas
 * Each persona has a name, icon, description, system prompt, and bound ChromaDB collection.
 */

import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { afterChange } from '../hooks/consulting-personas/afterChange'

// ============================================================
// Config
// ============================================================
export const ConsultingPersonas: CollectionConfig = {
  slug: 'consulting-personas',
  labels: {
    singular: 'Consulting Persona',
    plural: 'Consulting Personas',
  },
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'nameEn', 'slug', 'country', 'category', 'isEnabled', 'sortOrder', 'updatedAt'],
    group: 'Consulting',
  },
  access: {
    read: () => true,  // public — persona list shown on landing page + read by Engine
    create: isAdmin,
    update: isAdmin,
    delete: isAdmin,
  },
  hooks: {
    afterChange: [afterChange],
  },

  // ============================================================
  // Fields
  // ============================================================
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      admin: { description: 'Chinese display name (e.g. 移民顾问)' },
    },
    {
      name: 'nameEn',
      type: 'text',
      admin: { description: 'English display name (e.g. Immigration Advisor)' },
    },
    {
      name: 'slug',
      type: 'text',
      required: true,
      unique: true,
      index: true,
    },
    {
      name: 'icon',
      type: 'text',
      admin: {
        description: 'Lucide icon name (e.g. "scale", "shield-check")',
      },
    },
    {
      name: 'avatar',
      type: 'text',
      admin: {
        description: 'Path to avatar image (e.g. "/avatars/lawyer.png")',
      },
    },
    {
      name: 'description',
      type: 'textarea',
    },
    {
      name: 'systemPrompt',
      type: 'textarea',
      admin: {
        rows: 10,
        description: 'Full persona system prompt with {context_str} and {query_str} placeholders',
      },
    },
    {
      name: 'greeting',
      type: 'textarea',
      admin: {
        rows: 3,
        description: 'Opening greeting message displayed when a user starts a new session with this persona',
      },
    },
    {
      name: 'chromaCollection',
      type: 'text',
      required: true,
      admin: {
        description: 'ChromaDB collection name (e.g. "ca_edu-school-planning")',
      },
    },
    {
      name: 'mineruCategory',
      type: 'text',
      defaultValue: 'consulting',
      admin: {
        description: 'MinerU output category directory (default: "consulting")',
      },
    },
    {
      name: 'country',
      type: 'select',
      required: true,
      defaultValue: 'ca',
      options: [
        { label: 'Canada', value: 'ca' },
        { label: 'USA', value: 'us' },
        { label: 'UK', value: 'uk' },
        { label: 'Australia', value: 'au' },
      ],
      index: true,
      admin: { position: 'sidebar' },
    },
    {
      name: 'category',
      type: 'select',
      required: true,
      defaultValue: 'settlement',
      options: [
        { label: '🎓 Education', value: 'education' },
        { label: '🛂 Immigration', value: 'immigration' },
        { label: '🏠 Settlement', value: 'settlement' },
        { label: '🏥 Healthcare', value: 'healthcare' },
        { label: '💰 Finance', value: 'finance' },
        { label: '💼 Career', value: 'career' },
        { label: '⚖️ Legal', value: 'legal' },
        { label: '📊 Analysis', value: 'analysis' },
      ],
      index: true,
      admin: { position: 'sidebar' },
    },
    {
      name: 'isEnabled',
      type: 'checkbox',
      defaultValue: true,
      admin: { position: 'sidebar' },
    },
    {
      name: 'sortOrder',
      type: 'number',
      defaultValue: 0,
      admin: { position: 'sidebar' },
    },
    {
      name: 'suggestedQuestions',
      type: 'json',
      admin: {
        description: 'JSON array of { id, label, icon, questions[] } for persona-scoped suggested questions',
      },
    },
  ],
}
