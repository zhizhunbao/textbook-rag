/**
 * features/models/types.ts
 * LLM 模型类型定义
 * 
 * 统一管理本地模型（Ollama）和云端模型（Azure OpenAI / OpenAI）的类型
 * Unified types for local (Ollama) and cloud (Azure OpenAI / OpenAI) models
 */

// ── Provider 枚举 ──────────────────────────────────────────────────────────────
export type ModelProvider = 'ollama' | 'azure_openai' | 'openai' | 'other'

// ── 模型类型枚举 / Model capability type ─────────────────────────────────────
export type ModelType = 'chat' | 'embedding' | 'vision'


// ── 可用性状态 ─────────────────────────────────────────────────────────────────
export type AvailabilityStatus = 'available' | 'unavailable' | 'checking' | 'unknown'

// ── 可用性检测结果 ──────────────────────────────────────────────────────────────
export interface AvailabilityResult {
  /** 当前状态 / Current status */
  status: AvailabilityStatus
  /** 延迟(ms)，仅 available 时有值 / Latency in ms, only when available */
  latencyMs: number | null
  /** 上次检测时间戳 / Last check timestamp */
  checkedAt: number | null
  /** 错误信息 / Error message if unavailable */
  error: string | null
}

// ── 完整模型信息（来自 Payload CMS llms 集合）──────────────────────────
export interface LlmModel {
  id: number
  name: string
  displayName: string | null
  provider: ModelProvider
  /** Chat = text generation, Embedding = vector retrieval, Vision = multimodal */
  modelType: ModelType
  description: string | null
  useCases: string[] | null
  languages: string | null

  // 技术参数 / Technical specs
  parameterSize: string | null
  contextWindow: number | null
  maxOutputTokens: number | null
  minRamGb: number | null
  quantization: string | null

  // 定价 / Pricing
  isFree: boolean
  costPer1kInput: number | null
  costPer1kOutput: number | null

  // 吞吐量 / Throughput
  inputTokensPerMin: number | null
  outputTokensPerMin: number | null

  // 状态 / Status
  isDefault: boolean
  isEnabled: boolean
  sortOrder: number
}

// ── 运行时模型（含可用性）──────────────────────────────────────────────────────
export interface RuntimeModel extends LlmModel {
  /** 实时可用性检测结果 / Real-time availability check result */
  availability: AvailabilityResult
}

// ── Provider 健康状态 ──────────────────────────────────────────────────────────
export interface ProviderHealth {
  provider: ModelProvider
  status: AvailabilityStatus
  /** 该 provider 下可用的模型 ID 列表 / Available model names under this provider */
  availableModels: string[]
  latencyMs: number | null
  checkedAt: number | null
  error: string | null
}

// ── 简化的模型选择信息（供 ChatHeader 等组件使用）─────────────────────────────
export interface ModelOption {
  name: string
  displayName: string
  provider: ModelProvider
  isDefault: boolean
  isAvailable: boolean
  isFree: boolean
  latencyMs: number | null
}

// ── 本地已发现但未注册的模型 / Discovered local model (not yet registered) ────
export interface DiscoveredLocalModel {
  /** Ollama 模型名称 / Ollama model name (e.g. "llama3.2:3b") */
  name: string
  /** 模型参数量 / Parameter size (e.g. "3B") */
  parameterSize: string | null
  /** 量化方式 / Quantization level (e.g. "Q4_K_M") */
  quantization: string | null
  /** 模型家族 / Model family (e.g. "llama") */
  family: string | null
  /** 文件大小(可读) / File size human-readable (e.g. "2.0 GB") */
  size: string | null
  /** 最后修改时间 / Last modified ISO string */
  modifiedAt: string | null
}

export interface ProviderConfig {
  label: string
  labelFr: string
  color: string
  bg: string
  emoji: string
}

export const PROVIDER_CONFIGS: Record<ModelProvider, ProviderConfig> = {
  ollama: {
    label: 'Ollama',
    labelFr: 'Ollama (local)',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    emoji: '🦙',
  },
  azure_openai: {
    label: 'Azure OpenAI',
    labelFr: 'Azure OpenAI',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    emoji: '☁️',
  },
  openai: {
    label: 'OpenAI',
    labelFr: 'OpenAI',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    emoji: '🤖',
  },
  other: {
    label: 'Other',
    labelFr: 'Autre',
    color: 'text-gray-400',
    bg: 'bg-gray-500/10',
    emoji: '⚙️',
  },
}

export interface ModelTypeConfig {
  label: string
  emoji: string
  color: string
  bg: string
}

export const MODEL_TYPE_CONFIGS: Record<ModelType, ModelTypeConfig> = {
  chat: {
    label: 'Chat / LLM',
    emoji: '💬',
    color: 'text-indigo-400',
    bg: 'bg-indigo-500/10',
  },
  embedding: {
    label: 'Embedding',
    emoji: '🔢',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  vision: {
    label: 'Vision / VLM',
    emoji: '👁️',
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
  },
}


export type CatalogCategory = 'recommended' | 'reasoning' | 'lightweight' | 'specialized'

export interface CatalogModel {
  /** Ollama 模型名称 / Ollama model name (e.g. "qwen3:4b") */
  name: string
  displayName: string
  family: string
  category: CatalogCategory
  /** 模型功能类型 / Model capability type */
  modelType: ModelType
  parameterSize: string
  description: string
  advantages: string[]
  bestFor: string[]
  contextWindow: number
  released: string
  minRamGb: number
  languages: string
  /** HuggingFace 下载数 / HuggingFace download count */
  downloads: number
  /** HuggingFace 点赞数 / HuggingFace likes */
  likes: number
  /** 开源协议 / Open-source license (e.g. "apache-2.0") */
  license: string
  /** HuggingFace 仓库 ID / HuggingFace repository ID */
  hfRepo: string
  /** 是否已本地安装 / Whether model is installed locally */
  installed: boolean
  /** 模型来源 / Model source ("ollama", "huggingface") */
  source: string
}

// ── 标准测试问题 / Standard benchmark questions ────────────────────────────────
export interface BenchmarkQuestion {
  id: string
  question: string
  category: string
  expectedLength: string
  description: string
}

// ── 测试结果 / Benchmark result ────────────────────────────────────────────────
export interface BenchmarkResult {
  model: string
  question: string
  answer: string
  latencyMs: number
  inputTokens: number
  outputTokens: number
  totalTokens: number
  estimatedCost: number
  error: string | null
}

// ── Pull 进度 / Pull progress (SSE events) ─────────────────────────────────────
export interface PullProgress {
  status: string
  /** 已下载字节 / Bytes downloaded so far */
  completed?: number
  /** 文件总大小 / Total file size */
  total?: number
  /** 摘要 hash / Digest hash */
  digest?: string
  /** 错误信息 / Error message */
  error?: string
}

// ── 批量测试运行状态 / Batch benchmark run status ──────────────────────────────
export type BenchmarkRunStatus = 'idle' | 'running' | 'done' | 'error'
