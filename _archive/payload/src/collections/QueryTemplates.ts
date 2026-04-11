import type { CollectionConfig } from 'payload'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

/**
 * QueryTemplates — 问题引导模板
 *
 * Admin-managed templates that guide the system to:
 * 1. Detect ambiguous or vague questions
 * 2. Suggest clarifying follow-up questions
 * 3. Structure the expected answer format
 */
export const QueryTemplates: CollectionConfig = {
  slug: 'query-templates',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'category', 'isEnabled', 'updatedAt'],
    group: 'Settings',
  },
  access: {
    read: () => true,
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      admin: { description: 'Template name (e.g. "Definition vs Comparison")' },
    },
    {
      name: 'category',
      type: 'select',
      required: true,
      options: [
        { label: 'Disambiguation', value: 'disambiguation' },
        { label: 'Scope Narrowing', value: 'scope' },
        { label: 'Format Guidance', value: 'format' },
        { label: 'Follow-up', value: 'followup' },
      ],
      admin: { description: 'Type of question guidance' },
    },
    {
      name: 'triggerPatterns',
      type: 'json',
      admin: {
        description: 'Array of keyword/pattern strings that trigger this template (e.g. ["what is", "explain"])',
      },
    },
    {
      name: 'clarifyPrompt',
      type: 'textarea',
      required: true,
      admin: {
        description: 'English prompt shown to user for clarification',
        rows: 3,
      },
    },
    {
      name: 'clarifyPromptZh',
      type: 'textarea',
      admin: {
        description: '中文澄清提示',
        rows: 3,
      },
    },
    {
      name: 'suggestedQuestions',
      type: 'json',
      admin: {
        description: 'Array of suggested follow-up questions (e.g. ["Are you asking about the definition?", "Do you want a comparison?"])',
      },
    },
    {
      name: 'suggestedQuestionsZh',
      type: 'json',
      admin: {
        description: '中文建议问题数组',
      },
    },
    {
      name: 'answerFormat',
      type: 'textarea',
      admin: {
        description: 'Instruction appended to the system prompt to structure the answer (e.g. "Respond with a comparison table")',
        rows: 3,
      },
    },
    {
      name: 'answerFormatZh',
      type: 'textarea',
      admin: {
        description: '中文回答格式指令',
        rows: 3,
      },
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
