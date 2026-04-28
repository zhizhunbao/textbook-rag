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
    defaultColumns: ['name', 'slug', 'isEnabled', 'sortOrder', 'updatedAt'],
    group: 'Consulting',
  },
  access: {
    read: ({ req: { user } }) => !!user,  // any authenticated user
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
      name: 'chromaCollection',
      type: 'text',
      required: true,
      admin: {
        description: 'ChromaDB collection name (e.g. "persona_lawyer")',
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
  ],
}
