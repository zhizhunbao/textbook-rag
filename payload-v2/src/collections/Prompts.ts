import type { CollectionConfig } from 'payload'
import { isLoggedIn } from '../access/isLoggedIn'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

/**
 * Prompts — merged from QueryTemplates + PromptModes.
 * Aligned with engine-v2/response_synthesizers/ module.
 *
 * Combines:
 *   - Prompt modes (system prompts for different answer styles)
 *   - Query templates (question clarification patterns)
 */
export const Prompts: CollectionConfig = {
  slug: 'prompts',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'type', 'isEnabled', 'updatedAt'],
    group: 'Settings',
  },
  access: {
    read: isLoggedIn,  // GO-MU-09: was () => true
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      admin: { description: 'Display name (e.g. "Learning Mode" or "Definition vs Comparison")' },
    },
    {
      name: 'type',
      type: 'select',
      required: true,
      options: [
        { label: 'System Prompt (Mode)', value: 'mode' },
        { label: 'Query Template', value: 'template' },
      ],
      admin: { description: 'mode = answer style prompt, template = question clarification pattern' },
    },

    // ── Common fields ──
    {
      name: 'slug',
      type: 'text',
      required: true,
      unique: true,
      index: true,
      admin: { description: 'URL-safe identifier (e.g. "learning", "disambiguation")' },
    },
    {
      name: 'description',
      type: 'text',
      required: true,
      admin: { description: 'Short description shown to users' },
    },
    {
      name: 'icon',
      type: 'text',
      admin: { description: 'Lucide icon name (e.g. "lightbulb", "book", "chart")' },
    },

    // ── Mode-specific fields ──
    {
      name: 'systemPrompt',
      type: 'textarea',
      admin: {
        description: 'System prompt sent to LLM (for type=mode)',
        rows: 8,
        condition: (_, siblingData) => siblingData?.type === 'mode',
      },
    },

    // ── Template-specific fields ──
    {
      name: 'category',
      type: 'select',
      options: [
        { label: 'Disambiguation', value: 'disambiguation' },
        { label: 'Scope Narrowing', value: 'scope' },
        { label: 'Format Guidance', value: 'format' },
        { label: 'Follow-up', value: 'followup' },
      ],
      admin: {
        description: 'Type of question guidance (for type=template)',
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'triggerPatterns',
      type: 'json',
      admin: {
        description: 'Array of keywords that trigger this template',
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'clarifyPrompt',
      type: 'textarea',
      admin: {
        description: 'Prompt shown to user for clarification',
        rows: 3,
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'clarifyPromptZh',
      type: 'textarea',
      admin: {
        description: '中文澄清提示',
        rows: 3,
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'suggestedQuestions',
      type: 'json',
      admin: {
        description: 'Array of suggested follow-up questions',
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'suggestedQuestionsZh',
      type: 'json',
      admin: {
        description: '中文建议问题数组',
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'answerFormat',
      type: 'textarea',
      admin: {
        description: 'Instruction to structure the answer',
        rows: 3,
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },
    {
      name: 'answerFormatZh',
      type: 'textarea',
      admin: {
        description: '中文回答格式指令',
        rows: 3,
        condition: (_, siblingData) => siblingData?.type === 'template',
      },
    },

    // ── Status ──
    {
      name: 'isDefault',
      type: 'checkbox',
      defaultValue: false,
      admin: { description: 'If checked, this is the default for its type' },
    },
    {
      name: 'isEnabled',
      type: 'checkbox',
      defaultValue: true,
    },
    {
      name: 'sortOrder',
      type: 'number',
      defaultValue: 0,
    },
  ],
}
