/**
 * features/models/types.ts
 * LLM 模型类型定义
 * 
 * 统一管理本地模型（Ollama）和云端模型（Azure OpenAI / OpenAI）的类型
 * Unified types for local (Ollama) and cloud (Azure OpenAI / OpenAI) models
 */

// ── Provider 枚举 ──────────────────────────────────────────────────────────────
export type ModelProvider = 'ollama' | 'azure_openai' | 'openai' | 'other'

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

// ── 完整模型信息（来自 Payload CMS llm-models 集合）──────────────────────────
export interface LlmModel {
  id: number
  name: string
  displayName: string | null
  provider: ModelProvider
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

// ── Provider 配置（前端展示用）──────────────────────────────────────────────────
// ── 自动探测到的本地模型（未在 Payload 注册）──────────────────────────────────
export interface DiscoveredLocalModel {
  /** Ollama 模型名称 / Ollama model name (e.g. "llama3.2:3b") */
  name: string
  /** 模型大小 / Model size (from Ollama API, e.g. "2.0 GB") */
  size: string | null
  /** 原始字节大小 / Raw size in bytes */
  sizeBytes: number | null
  /** 修改时间 / Modified time */
  modifiedAt: string | null
  /** 参数量 / Parameter size (e.g. "7B", "3.2B") */
  parameterSize: string | null
  /** 量化级别 / Quantization level (e.g. "Q4_K_M") */
  quantization: string | null
  /** 模型家族 / Model family (e.g. "qwen2", "llama") */
  family: string | null
  /** 是否已注册到 Payload CMS / Whether already registered in Payload CMS */
  isRegistered: false
}

// ── 探测结果（已注册 + 发现的未注册）──────────────────────────────────────────
export interface ModelDiscoveryResult {
  /** 已注册模型（含可用性）/ Registered models with availability */
  registered: RuntimeModel[]
  /** 本地存在但未注册的模型 / Locally present but unregistered models */
  discovered: DiscoveredLocalModel[]
  /** 检测时间 / Detection timestamp */
  checkedAt: number
}

export interface ProviderConfig {
  label: string
  labelZh: string
  color: string
  bg: string
  emoji: string
}

export const PROVIDER_CONFIGS: Record<ModelProvider, ProviderConfig> = {
  ollama: {
    label: 'Ollama',
    labelZh: 'Ollama (本地)',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    emoji: '🦙',
  },
  azure_openai: {
    label: 'Azure OpenAI',
    labelZh: 'Azure OpenAI',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    emoji: '☁️',
  },
  openai: {
    label: 'OpenAI',
    labelZh: 'OpenAI',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    emoji: '🤖',
  },
  other: {
    label: 'Other',
    labelZh: '其他',
    color: 'text-gray-400',
    bg: 'bg-gray-500/10',
    emoji: '⚙️',
  },
}
