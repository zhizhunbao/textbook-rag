import type { CollectionConfig } from 'payload'
import { isLoggedIn } from '../access/isLoggedIn'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

/**
 * Llms — Unified model registry for all model types.
 * Covers Chat/LLM, Embedding, and Vision/VLM models.
 * Aligned with engine-v2/llms/ module.
 */
export const Llms: CollectionConfig = {
  slug: 'llms',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'provider', 'isFree', 'isDefault', 'updatedAt'],
    group: 'Settings',
  },
  access: {
    read: isLoggedIn,  // GO-MU-09: was () => true
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
    {
      name: 'modelType',
      type: 'select',
      required: true,
      options: [
        { label: 'Chat / LLM', value: 'chat' },
        { label: 'Embedding', value: 'embedding' },
        { label: 'Vision / VLM', value: 'vision' },
      ],
      defaultValue: 'chat',
      admin: { description: 'Model capability type: Chat for generation, Embedding for retrieval, Vision for multimodal.' },
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

    // ── Catalog Metadata (synced from engine via POST /api/llms/sync-catalog) ──
    {
      name: 'family',
      type: 'text',
      admin: {
        description: 'Model family (e.g. "qwen", "llama"). Auto-filled by catalog sync.',
        position: 'sidebar',
      },
    },
    {
      name: 'category',
      type: 'select',
      options: [
        { label: 'Recommended', value: 'recommended' },
        { label: 'Reasoning', value: 'reasoning' },
        { label: 'Lightweight', value: 'lightweight' },
        { label: 'Specialized', value: 'specialized' },
      ],
      admin: {
        description: 'Catalog category. Auto-filled by catalog sync.',
        position: 'sidebar',
      },
    },
    {
      name: 'installed',
      type: 'checkbox',
      defaultValue: false,
      admin: {
        description: 'Whether the model is currently installed in local Ollama. Auto-filled.',
        position: 'sidebar',
      },
    },
    {
      name: 'source',
      type: 'select',
      options: [
        { label: 'Ollama Library', value: 'ollama' },
        { label: 'HuggingFace', value: 'huggingface' },
      ],
      defaultValue: 'ollama',
      admin: {
        description: 'Where this model was discovered from. Auto-filled.',
        position: 'sidebar',
      },
    },
    {
      name: 'released',
      type: 'text',
      admin: {
        description: 'Release month (e.g. "2025-04"). Auto-filled by catalog sync.',
        position: 'sidebar',
      },
    },
    {
      name: 'downloads',
      type: 'number',
      admin: {
        description: 'HuggingFace download count. Auto-filled by catalog sync.',
        position: 'sidebar',
      },
    },
    {
      name: 'likes',
      type: 'number',
      admin: {
        description: 'HuggingFace likes. Auto-filled by catalog sync.',
        position: 'sidebar',
      },
    },
    {
      name: 'license',
      type: 'text',
      admin: {
        description: 'License identifier (e.g. "apache-2.0"). Auto-filled.',
        position: 'sidebar',
      },
    },
    {
      name: 'hfRepo',
      type: 'text',
      admin: {
        description: 'HuggingFace repo ID (e.g. "Qwen/Qwen3-8B"). Auto-filled.',
        position: 'sidebar',
      },
    },
    {
      name: 'advantages',
      type: 'json',
      admin: {
        description: 'Advantage tags (e.g. ["Vision capable", "Tool calling"]). Auto-filled.',
      },
    },
    {
      name: 'bestFor',
      type: 'json',
      admin: {
        description: 'Best-use-case tags aligned with personas. Auto-filled.',
      },
    },
  ],
  endpoints: [
    {
      path: '/sync-catalog',
      method: 'post',
      handler: async (req) => {
        const { syncCatalogEndpoint } = await import('./endpoints/sync-catalog')
        return syncCatalogEndpoint(req)
      },
    },
  ],
}
