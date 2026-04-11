/**
 * features/models/api.ts
 * 模型 API 层 — 真实的可用性检测
 *
 * 职责:
 *   1. 从 Payload CMS 拉取所有已注册的 LLM 模型
 *   2. 调用 Engine API 进行真实可用性检测（Ollama 本地 / 云端 API ping）
 *   3. 返回包含实时状态的 RuntimeModel[]
 *
 * Responsibilities:
 *   1. Fetch all registered LLM models from Payload CMS
 *   2. Call Engine API for real availability checks (Ollama local / cloud API ping)
 *   3. Return RuntimeModel[] with live status
 */

import type {
  LlmModel,
  RuntimeModel,
  AvailabilityResult,
  ProviderHealth,
  ModelProvider,
  DiscoveredLocalModel,
  ModelDiscoveryResult,
} from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000'

// ── 基础请求工具 / Base request helper ──────────────────────────────────────────

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ── 1. 获取 Payload CMS 中所有已注册的模型 / Fetch registered models ──────────

export async function fetchRegisteredModels(): Promise<LlmModel[]> {
  const data = await request<{ docs: any[] }>(
    '/api/llm-models?limit=100&sort=sortOrder'
  )
  return (data.docs || []).map(mapPayloadToLlmModel)
}

/** 只获取启用的模型 / Fetch only enabled models */
export async function fetchEnabledModels(): Promise<LlmModel[]> {
  const data = await request<{ docs: any[] }>(
    '/api/llm-models?limit=100&sort=sortOrder&where[isEnabled][equals]=true'
  )
  return (data.docs || []).map(mapPayloadToLlmModel)
}

function mapPayloadToLlmModel(doc: any): LlmModel {
  return {
    id: doc.id,
    name: doc.name ?? '',
    displayName: doc.displayName ?? null,
    provider: (doc.provider ?? 'other') as ModelProvider,
    description: doc.description ?? null,
    useCases: Array.isArray(doc.useCases) ? doc.useCases : null,
    languages: doc.languages ?? null,
    parameterSize: doc.parameterSize ?? null,
    contextWindow: doc.contextWindow ?? null,
    maxOutputTokens: doc.maxOutputTokens ?? null,
    minRamGb: doc.minRamGb ?? null,
    quantization: doc.quantization ?? null,
    isFree: doc.isFree ?? true,
    costPer1kInput: doc.costPer1kInput ?? null,
    costPer1kOutput: doc.costPer1kOutput ?? null,
    inputTokensPerMin: doc.inputTokensPerMin ?? null,
    outputTokensPerMin: doc.outputTokensPerMin ?? null,
    isDefault: doc.isDefault ?? false,
    isEnabled: doc.isEnabled ?? true,
    sortOrder: doc.sortOrder ?? 0,
  }
}

/** 删除一个模型 / Delete a model from Payload CMS by ID */
export async function deleteModel(modelId: number): Promise<void> {
  await fetch(`/api/llm-models/${modelId}`, {
    method: 'DELETE',
    credentials: 'include',
  })
}

/**
 * 注册一个发现的本地模型到 Payload CMS
 * Register a discovered local model into Payload CMS
 */
export async function registerModel(model: {
  name: string
  parameterSize?: string | null
  quantization?: string | null
  family?: string | null
  sizeBytes?: number | null
}): Promise<LlmModel> {
  // 生成友好的 displayName: "qwen3.5:4b" → "Qwen3.5 4B"
  const displayName = model.name
    .replace(/:latest$/, '')
    .split(':')
    .map((part) => {
      // 尝试解析参数大小部分 (7b, 14b, etc.)
      if (/^\d+\.?\d*[bBmM]$/.test(part)) return part.toUpperCase()
      // 首字母大写
      return part.charAt(0).toUpperCase() + part.slice(1)
    })
    .join(' ')

  // 根据参数大小推测上下文窗口 / Estimate context window from parameter size
  const paramSize = model.parameterSize?.toLowerCase() || ''
  let contextWindow = 4096 // 默认
  if (paramSize.includes('70b') || paramSize.includes('72b')) contextWindow = 131072
  else if (paramSize.includes('14b') || paramSize.includes('13b')) contextWindow = 131072
  else if (paramSize.includes('7b') || paramSize.includes('8b')) contextWindow = 131072
  else if (paramSize.includes('3b') || paramSize.includes('4b')) contextWindow = 131072
  else if (paramSize.includes('1b') || paramSize.includes('2b')) contextWindow = 65536

  // 根据 family 推测语言支持 / Estimate language support from family
  const family = model.family?.toLowerCase() || ''
  let languages = 'en'
  if (family.includes('qwen')) languages = 'en, zh, ja, ko'
  else if (family.includes('llama')) languages = 'en, de, fr, it, pt, hi, es, th'
  else if (family.includes('deepseek')) languages = 'en, zh'
  else if (family.includes('gemma')) languages = 'en'

  // 根据 family 推测用途 / Estimate use cases from family
  const useCases: string[] = ['General Q&A']
  if (family.includes('deepseek') && model.name.includes('r1')) {
    useCases.push('Reasoning', 'Step-by-step Analysis', 'Math')
  } else if (family.includes('qwen')) {
    useCases.push('RAG Q&A', 'Summarization', 'Translation')
  } else if (family.includes('llama')) {
    useCases.push('English Content', 'Fast Processing')
  }

  const payload = {
    name: model.name,
    displayName,
    provider: 'ollama',
    description: `Auto-discovered local model: ${model.name}`,
    parameterSize: model.parameterSize || null,
    quantization: model.quantization || null,
    contextWindow,
    languages,
    useCases,
    isFree: true,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    isDefault: false,
    isEnabled: true,
    sortOrder: 50,
  }

  const res = await fetch('/api/llm-models', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Failed to register model: ${res.status} ${body}`)
  }

  const data = await res.json()
  return mapPayloadToLlmModel(data.doc || data)
}

/**
 * 从本地 Ollama 移除一个模型
 * Remove a model from local Ollama installation via Engine API
 */
export async function removeOllamaModel(modelName: string): Promise<void> {
  const res = await fetch(`${ENGINE}/engine/models/${encodeURIComponent(modelName)}`, {
    method: 'DELETE',
    timeout: 30_000,
  } as RequestInit)

  const data = await res.json()
  if (data.status === 'error') {
    throw new Error(data.error || 'Failed to remove model from Ollama')
  }
}

// ── 2. 真实可用性检测 / Real availability detection ──────────────────────────────

/**
 * 检测所有 provider 的可用性（通过 Engine API 代理）
 * Detect availability for all providers via Engine API proxy
 *
 * Engine 暴露:
 *   GET /engine/models        → Ollama 本地模型列表
 *   GET /engine/providers     → 可用的 provider 列表
 *   GET /engine/models/check  → 完整的可用性检测（我们在此新建）
 */

/** 检测 Ollama 本地模型可用性 / Check Ollama local model availability */
export async function checkOllamaModels(): Promise<ProviderHealth> {
  const start = Date.now()
  try {
    const data = await request<{ models: string[] }>(
      `${ENGINE}/engine/models`
    )
    return {
      provider: 'ollama',
      status: 'available',
      availableModels: data.models || [],
      latencyMs: Date.now() - start,
      checkedAt: Date.now(),
      error: null,
    }
  } catch (err) {
    return {
      provider: 'ollama',
      status: 'unavailable',
      availableModels: [],
      latencyMs: null,
      checkedAt: Date.now(),
      error: err instanceof Error ? err.message : 'Ollama service unavailable',
    }
  }
}

/** 检测云端 provider 可用性 / Check cloud provider availability */
export async function checkCloudProviders(): Promise<ProviderHealth[]> {
  const start = Date.now()
  try {
    const data = await request<{ providers: string[] }>(
      `${ENGINE}/engine/providers`
    )
    const providers = data.providers || []
    const results: ProviderHealth[] = []

    // Azure OpenAI
    if (providers.includes('azure_openai')) {
      results.push({
        provider: 'azure_openai',
        status: 'available',
        availableModels: [], // 云端模型不需要本地检测，只要 provider 可用
        latencyMs: Date.now() - start,
        checkedAt: Date.now(),
        error: null,
      })
    } else {
      results.push({
        provider: 'azure_openai',
        status: 'unavailable',
        availableModels: [],
        latencyMs: null,
        checkedAt: Date.now(),
        error: 'Azure OpenAI endpoint not configured',
      })
    }

    // OpenAI
    if (providers.includes('openai')) {
      results.push({
        provider: 'openai',
        status: 'available',
        availableModels: [],
        latencyMs: Date.now() - start,
        checkedAt: Date.now(),
        error: null,
      })
    } else {
      results.push({
        provider: 'openai',
        status: 'unavailable',
        availableModels: [],
        latencyMs: null,
        checkedAt: Date.now(),
        error: 'OpenAI API key not configured',
      })
    }

    return results
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : 'Engine unreachable'
    return [
      {
        provider: 'azure_openai',
        status: 'unavailable',
        availableModels: [],
        latencyMs: null,
        checkedAt: Date.now(),
        error: errorMsg,
      },
      {
        provider: 'openai',
        status: 'unavailable',
        availableModels: [],
        latencyMs: null,
        checkedAt: Date.now(),
        error: errorMsg,
      },
    ]
  }
}

/**
 * 完整的可用性检测 — 并行检测所有 provider
 * Full availability check — parallel detection for all providers
 *
 * 返回每个已注册模型的 RuntimeModel（含实时可用性）
 * Returns RuntimeModel[] for all registered models with live availability
 */
export async function checkAllModels(
  registeredModels?: LlmModel[]
): Promise<RuntimeModel[]> {
  // 1. 拉取已注册模型（如未传入）/ Fetch registered models if not provided
  const models = registeredModels ?? await fetchEnabledModels()

  // 2. 并行检测所有 provider / Parallel check all providers
  const [ollamaHealth, cloudHealthResults] = await Promise.all([
    checkOllamaModels(),
    checkCloudProviders(),
  ])

  // 3. 构建 provider → health 映射 / Build provider → health map
  const healthMap = new Map<ModelProvider, ProviderHealth>()
  healthMap.set('ollama', ollamaHealth)
  for (const h of cloudHealthResults) {
    healthMap.set(h.provider, h)
  }

  // 4. 为每个模型生成可用性结果 / Generate availability for each model
  return models.map((model) => {
    const health = healthMap.get(model.provider)
    const availability = resolveAvailability(model, health)
    return { ...model, availability }
  })
}


/**
 * 根据 provider 健康状态和模型信息推断可用性
 * Resolve availability based on provider health and model info
 */
function resolveAvailability(
  model: LlmModel,
  health: ProviderHealth | undefined
): AvailabilityResult {
  // 模型未启用 → 标记为 unavailable / Disabled → unavailable
  if (!model.isEnabled) {
    return {
      status: 'unavailable',
      latencyMs: null,
      checkedAt: Date.now(),
      error: 'Model is disabled in settings',
    }
  }

  // 没有 provider 健康数据 → unknown / No health data → unknown
  if (!health) {
    return {
      status: 'unknown',
      latencyMs: null,
      checkedAt: null,
      error: null,
    }
  }

  // Provider 不可用 → unavailable / Provider down → unavailable
  if (health.status !== 'available') {
    return {
      status: 'unavailable',
      latencyMs: null,
      checkedAt: health.checkedAt,
      error: health.error ?? `${model.provider} provider is not available`,
    }
  }

  // Ollama: 检查模型是否真实存在于本地 / Ollama: check if model is actually pulled locally
  if (model.provider === 'ollama') {
    const isLocally = health.availableModels.some(
      (m) => m === model.name || m.startsWith(model.name.split(':')[0])
    )
    if (!isLocally) {
      return {
        status: 'unavailable',
        latencyMs: health.latencyMs,
        checkedAt: health.checkedAt,
        error: `Model "${model.name}" is not pulled locally. Run: ollama pull ${model.name}`,
      }
    }
  }

  // 一切正常 / All good
  return {
    status: 'available',
    latencyMs: health.latencyMs,
    checkedAt: health.checkedAt,
    error: null,
  }
}

// ── 3. 兼容旧 API 的简化接口 / Backward-compatible simple interface ─────────────

/**
 * 兼容旧的 fetchModels() 接口
 * Backward-compatible fetchModels() — used by ChatPanel
 *
 * 返回 { name, is_default, provider }[] 但只包含真正可用的模型
 * Returns { name, is_default, provider }[] but only actually available models
 */
export async function fetchAvailableModels(): Promise<
  { name: string; is_default: boolean; provider?: string }[]
> {
  try {
    const runtimeModels = await checkAllModels()
    const available = runtimeModels.filter(
      (m) => m.availability.status === 'available'
    )

    if (available.length > 0) {
      return available.map((m) => ({
        name: m.name,
        is_default: m.isDefault,
        provider: m.provider,
      }))
    }

    // 所有模型都不可用时 fallback 到旧逻辑
    // Fallback to old logic when all models are unavailable
    return runtimeModels
      .filter((m) => m.isEnabled)
      .map((m) => ({
        name: m.name,
        is_default: m.isDefault,
        provider: m.provider,
      }))
  } catch {
    // 完全失败时 fallback 到 engine models 端点
    // Complete failure: fallback to engine /models endpoint
    try {
      const data = await request<{ models: string[] }>(
        `${ENGINE}/engine/models`
      )
      return (data.models || []).map((name: string, i: number) => ({
        name,
        is_default: i === 0,
        provider: 'ollama',
      }))
    } catch {
      return [{ name: 'llama3.2:3b', is_default: true, provider: 'ollama' }]
    }
  }
}


// ── 4. 本地模型自动探测 / Local model auto-discovery ─────────────────────────────

/**
 * Ollama 模型详情（来自 /api/tags 响应）
 * Ollama model detail from /api/tags response
 */
interface OllamaModelDetail {
  name: string
  model: string
  size: number
  modified_at: string
  digest: string
  details?: {
    parent_model?: string
    format?: string
    family?: string
    parameter_size?: string
    quantization_level?: string
  }
}

/**
 * 直接探测 Ollama 本地安装了哪些模型（含详细信息）
 * Directly probe which models are installed in Ollama (with details)
 *
 * 通过 Engine 代理访问 Ollama /api/tags 端点
 * Proxied through Engine to reach Ollama /api/tags endpoint
 */
export async function discoverLocalModels(): Promise<OllamaModelDetail[]> {
  try {
    // 先尝试 Engine 提供的详细端点
    // Try Engine's detailed endpoint first
    const data = await request<{ models: OllamaModelDetail[] }>(
      `${ENGINE}/engine/models/discover`
    )
    return data.models || []
  } catch {
    // fallback: 使用旧端点，只有名称
    // Fallback: use old endpoint, names only
    try {
      const data = await request<{ models: string[] }>(
        `${ENGINE}/engine/models`
      )
      return (data.models || []).map((name) => ({
        name,
        model: name,
        size: 0,
        modified_at: '',
        digest: '',
      }))
    } catch {
      return []
    }
  }
}

/**
 * 格式化文件大小 / Format file size
 */
function formatSize(bytes: number): string {
  if (bytes <= 0) return ''
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  const mb = bytes / (1024 * 1024)
  return `${mb.toFixed(0)} MB`
}

/**
 * 完整探测：已注册模型的可用性 + 发现未注册的本地模型
 * Full discovery: registered model availability + unregistered local models
 *
 * 使用场景: Dashboard 模型管理页面
 * Use case: Dashboard model management page
 */
export async function discoverAllModels(): Promise<ModelDiscoveryResult> {
  // 并行: 拉取注册模型 + 检测可用性 + 探测本地模型
  // Parallel: fetch registered + check availability + discover local
  const [runtimeModels, localModels] = await Promise.all([
    checkAllModels(),
    discoverLocalModels(),
  ])

  // 建立本地模型名称 → 详情索引 / Index local models by name
  const localIndex = new Map(localModels.map((l) => [l.name, l]))

  // ── 自动修补：已注册但字段缺失的 Ollama 模型 ──────────────────────────────
  // Auto-enrich: registered Ollama models with missing fields
  const enrichPromises: Promise<void>[] = []
  for (const rm of runtimeModels) {
    if (rm.provider !== 'ollama') continue
    const local = localIndex.get(rm.name)
    if (!local?.details) continue

    // 检查哪些字段需要补充 / Check which fields need populating
    const patches: Record<string, unknown> = {}
    if (!rm.parameterSize && local.details.parameter_size) {
      patches.parameterSize = local.details.parameter_size
    }
    if (!rm.quantization && local.details.quantization_level) {
      patches.quantization = local.details.quantization_level
    }
    if (!rm.contextWindow) {
      // 推测上下文窗口 / Estimate context window
      const ps = (local.details.parameter_size || '').toLowerCase()
      if (ps.includes('70b') || ps.includes('72b')) patches.contextWindow = 131072
      else if (ps.includes('14b') || ps.includes('13b')) patches.contextWindow = 131072
      else if (ps.includes('7b') || ps.includes('8b')) patches.contextWindow = 131072
      else if (ps.includes('3b') || ps.includes('4b')) patches.contextWindow = 131072
      else if (ps.includes('1b') || ps.includes('2b')) patches.contextWindow = 65536
      else patches.contextWindow = 4096
    }
    if (!rm.languages && local.details.family) {
      const fam = local.details.family.toLowerCase()
      if (fam.includes('qwen')) patches.languages = 'en, zh, ja, ko'
      else if (fam.includes('llama')) patches.languages = 'en, de, fr, it, pt, hi, es, th'
      else if (fam.includes('deepseek')) patches.languages = 'en, zh'
      else patches.languages = 'en'
    }
    if ((!rm.useCases || rm.useCases.length === 0) && local.details.family) {
      const fam = local.details.family.toLowerCase()
      const uc: string[] = ['General Q&A']
      if (fam.includes('deepseek') && rm.name.includes('r1')) {
        uc.push('Reasoning', 'Step-by-step Analysis', 'Math')
      } else if (fam.includes('qwen')) {
        uc.push('RAG Q&A', 'Summarization', 'Translation')
      } else if (fam.includes('llama')) {
        uc.push('English Content', 'Fast Processing')
      }
      patches.useCases = uc
    }

    // 如果确实有需要修补的字段就 PATCH / If patches exist, apply them
    if (Object.keys(patches).length > 0) {
      enrichPromises.push(
        fetch(`/api/llm-models/${rm.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(patches),
        })
          .then(() => {
            // 立即更新内存中的 runtime model / Update in-memory runtime model
            Object.assign(rm, patches)
          })
          .catch(() => { /* 修补失败不阻塞 / Enrich failure is non-blocking */ })
      )
    }
  }
  // 不阻塞主流程，后台修补 / Non-blocking background enrichment
  if (enrichPromises.length > 0) {
    await Promise.allSettled(enrichPromises)
  }

  // 找出本地存在但未注册的模型
  // Find locally present but unregistered models
  const registeredNames = new Set(runtimeModels.map((m) => m.name))
  const discovered: DiscoveredLocalModel[] = localModels
    .filter((local) => !registeredNames.has(local.name))
    .map((local) => ({
      name: local.name,
      size: local.size ? formatSize(local.size) : null,
      sizeBytes: local.size || null,
      modifiedAt: local.modified_at || null,
      parameterSize: local.details?.parameter_size || null,
      quantization: local.details?.quantization_level || null,
      family: local.details?.family || null,
      isRegistered: false as const,
    }))

  return {
    registered: runtimeModels,
    discovered,
    checkedAt: Date.now(),
  }
}

