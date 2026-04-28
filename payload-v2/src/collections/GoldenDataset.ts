import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'

/**
 * GoldenDataset Collection — Ground-truth QA pairs for IR evaluation.
 *
 * Slug: golden-dataset
 * Aligned with engine_v2/evaluation/golden_dataset.py
 *
 * Used by:
 *   - EI-T1: Golden Dataset generation + management
 *   - EI-T2: Retrieval metrics (expected_chunk_ids for IR evaluation)
 *   - EI-T3: CorrectnessEvaluator (expected_answer for F1 comparison)
 */
export const GoldenDataset: CollectionConfig = {
  slug: 'golden-dataset',
  admin: {
    useAsTitle: 'question',
    defaultColumns: [
      'question', 'verified', 'bookId', 'sourcePage', 'createdAt',
    ],
    group: 'Analytics',
  },
  access: {
    read: isAdmin,
    create: () => true,   // Engine writes generated records
    update: isAdmin,
    delete: isAdmin,
  },
  fields: [
    // ── Core QA pair ──
    {
      name: 'question',
      type: 'text',
      required: true,
      admin: { description: 'The golden question (ground truth)' },
    },
    {
      name: 'expectedAnswer',
      type: 'textarea',
      required: true,
      admin: { description: 'The expected correct answer (ground truth)' },
    },

    // ── Source tracking ──
    {
      name: 'expectedChunkIds',
      type: 'json',
      admin: { description: 'Array of chunk IDs that should be retrieved (ground truth)' },
    },
    {
      name: 'bookId',
      type: 'text',
      admin: { description: 'Book identifier this QA pair was generated from' },
    },
    {
      name: 'sourcePage',
      type: 'text',
      admin: { description: 'Source page number(s) in the original PDF' },
    },

    // ── Quality control ──
    {
      name: 'verified',
      type: 'checkbox',
      defaultValue: false,
      admin: { description: 'Has this QA pair been verified (auto or manual)?' },
    },
    {
      name: 'verificationSource',
      type: 'select',
      options: [
        { label: 'Auto (LLM generated)', value: 'auto' },
        { label: 'Manual (human reviewed)', value: 'manual' },
      ],
      admin: { description: 'How was this record verified? (EUX-T1-01)' },
    },
    {
      name: 'tags',
      type: 'json',
      admin: {
        description: 'Classification tags, e.g. ["factual", "synthesis", "comparison"]',
      },
    },
  ],
}
