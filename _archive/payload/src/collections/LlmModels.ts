import type { CollectionConfig } from 'payload'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

export const LlmModels: CollectionConfig = {
  slug: 'llm-models',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'provider', 'isFree', 'isDefault', 'updatedAt'],
    group: 'Settings',
  },
  access: {
    read: () => true,
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  fields: [
    // ── Basic Info ──
    {
      name: 'name',
      type: 'text',
      required: true,
      unique: true,
      admin: { description: 'Model identifier used in API calls (e.g. "qwen3.5:4b")' },
    },
    {
      name: 'displayName',
      type: 'text',
      admin: { description: 'Human-readable name (e.g. "Qwen 2.5 7B")' },
    },
    {
      name: 'provider',
      type: 'select',
      required: true,
      options: [
        { label: 'Ollama (Local)', value: 'ollama' },
        { label: 'Azure OpenAI', value: 'azure_openai' },
        { label: 'OpenAI', value: 'openai' },
        { label: 'Other', value: 'other' },
      ],
      defaultValue: 'ollama',
    },

    // ── Capabilities ──
    {
      name: 'description',
      type: 'textarea',
      admin: { description: 'English description of strengths and best use cases', rows: 3 },
    },
    {
      name: 'useCases',
      type: 'json',
      admin: { description: 'Array of use case strings, e.g. ["RAG Q&A", "Summarization", "Code"]' },
    },
    {
      name: 'languages',
      type: 'text',
      admin: { description: 'Supported languages (e.g. "en, zh, ja")' },
    },

    // ── Technical Specs ──
    {
      name: 'parameterSize',
      type: 'text',
      admin: { description: 'Parameter count (e.g. "7B", "14B", "70B")' },
    },
    {
      name: 'contextWindow',
      type: 'number',
      admin: { description: 'Maximum context window in tokens' },
    },
    {
      name: 'maxOutputTokens',
      type: 'number',
      admin: { description: 'Maximum output tokens per response' },
    },
    {
      name: 'minRamGb',
      type: 'number',
      admin: { description: 'Minimum RAM/VRAM needed in GB' },
    },
    {
      name: 'quantization',
      type: 'text',
      admin: { description: 'Quantization level (e.g. "Q4_K_M", "FP16")' },
    },

    // ── Pricing ──
    {
      name: 'isFree',
      type: 'checkbox',
      defaultValue: true,
      admin: { description: 'Free to use (local models = true)' },
    },
    {
      name: 'costPer1kInput',
      type: 'number',
      admin: { description: 'Cost per 1K input tokens (USD), 0 for free/local' },
    },
    {
      name: 'costPer1kOutput',
      type: 'number',
      admin: { description: 'Cost per 1K output tokens (USD), 0 for free/local' },
    },

    // ── Throughput ──
    {
      name: 'inputTokensPerMin',
      type: 'number',
      admin: { description: 'Input processing throughput (tokens/min). Measured or estimated.' },
    },
    {
      name: 'outputTokensPerMin',
      type: 'number',
      admin: { description: 'Output generation throughput (tokens/min). Measured or estimated.' },
    },

    // ── Status ──
    {
      name: 'isDefault',
      type: 'checkbox',
      defaultValue: false,
      admin: { description: 'Default model for new conversations' },
    },
    {
      name: 'isEnabled',
      type: 'checkbox',
      defaultValue: true,
      admin: { description: 'Whether this model is available for selection' },
    },
    {
      name: 'sortOrder',
      type: 'number',
      defaultValue: 0,
      admin: { description: 'Display order (lower = first)' },
    },
  ],
}
