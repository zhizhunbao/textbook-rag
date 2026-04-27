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
  CatalogModel,
  CatalogCategory,
  BenchmarkQuestion,
  BenchmarkResult,
  PullProgress,
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
    '/api/llms?limit=100&sort=sortOrder'
  )
  return (data.docs || []).map(mapPayloadToLlmModel)
}

/** 只获取启用的模型 / Fetch only enabled models */
export async function fetchEnabledModels(): Promise<LlmModel[]> {
  const data = await request<{ docs: any[] }>(
    '/api/llms?limit=100&sort=sortOrder&where[isEnabled][equals]=true'
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
  await fetch(`/api/llms/${modelId}`, {
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

  const res = await fetch('/api/llms', {
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
  const res = await fetch(`${ENGINE}/engine/llms/models/${encodeURIComponent(modelName)}`, {
    method: 'DELETE',
    timeout: 30_000,
  } as RequestInit)

  const data = await res.json()
  if (data.status === 'error') {
    throw new Error(data.error || 'Failed to remove model from Ollama')
  }
}

// ── 2. Real availability detection ──────────────────────────────────────────

/**
 * Engine API response shape for /engine/llms/providers
 *
 *   { providers: [{ name, display_name, model, available, base_url?, endpoint? }] }
 */
interface EngineProviderInfo {
  name: string
  display_name?: string
  model?: string
  available: boolean
  base_url?: string
  endpoint?: string
}

/**
 * Engine API response shape for /engine/llms/models
 *
 *   { llm: { model, provider }, embed_model: { model } }
 */
interface EngineModelsResponse {
  llm?: { model?: string; provider?: string }
  embed_model?: { model?: string }
}

/**
 * Fetch all provider health from Engine's /engine/llms/providers endpoint.
 * This is the single source of truth for availability.
 */
async function fetchProviderHealth(): Promise<EngineProviderInfo[]> {
  const data = await request<{ providers: EngineProviderInfo[] }>(
    `${ENGINE}/engine/llms/providers`
  )
  return data.providers || []
}

/** Check Ollama local model availability */
export async function checkOllamaModels(): Promise<ProviderHealth> {
  const start = Date.now()
  try {
    const providers = await fetchProviderHealth()
    const ollama = providers.find((p) => p.name === 'ollama')

    if (ollama?.available) {
      // Also try to get the list of locally installed Ollama models
      let availableModels: string[] = []
      try {
        // Engine /engine/llms/models returns current active model info
        const modelsData = await request<EngineModelsResponse>(
          `${ENGINE}/engine/llms/models`
        )
        if (modelsData.llm?.model) {
          availableModels.push(modelsData.llm.model)
        }
        if (modelsData.embed_model?.model) {
          availableModels.push(modelsData.embed_model.model)
        }
      } catch {
        // If we can't get model list, just use the provider's model name
        if (ollama.model) availableModels = [ollama.model]
      }

      return {
        provider: 'ollama',
        status: 'available',
        availableModels,
        latencyMs: Date.now() - start,
        checkedAt: Date.now(),
        error: null,
      }
    }

    return {
      provider: 'ollama',
      status: 'unavailable',
      availableModels: [],
      latencyMs: Date.now() - start,
      checkedAt: Date.now(),
      error: ollama ? 'Ollama service not responding' : 'Ollama not configured',
    }
  } catch (err) {
    return {
      provider: 'ollama',
      status: 'unavailable',
      availableModels: [],
      latencyMs: null,
      checkedAt: Date.now(),
      error: err instanceof Error ? err.message : 'Engine unreachable',
    }
  }
}

/** Check cloud provider availability */
export async function checkCloudProviders(): Promise<ProviderHealth[]> {
  const start = Date.now()
  try {
    const providers = await fetchProviderHealth()
    const results: ProviderHealth[] = []

    // Azure OpenAI
    const azure = providers.find((p) => p.name === 'azure_openai')
    results.push({
      provider: 'azure_openai',
      status: azure?.available ? 'available' : 'unavailable',
      availableModels: azure?.model ? [azure.model] : [],
      latencyMs: Date.now() - start,
      checkedAt: Date.now(),
      error: azure?.available ? null : 'Azure OpenAI endpoint not configured',
    })

    // OpenAI (direct, not Azure)
    const openai = providers.find((p) => p.name === 'openai')
    results.push({
      provider: 'openai',
      status: openai?.available ? 'available' : 'unavailable',
      availableModels: openai?.model ? [openai.model] : [],
      latencyMs: Date.now() - start,
      checkedAt: Date.now(),
      error: openai?.available ? null : 'OpenAI API key not configured',
    })

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
  // 1. Fetch registered models if not provided
  const models = registeredModels ?? await fetchEnabledModels()

  // 2. Fetch provider health (single API call)
  let providers: EngineProviderInfo[] = []
  try {
    providers = await fetchProviderHealth()
  } catch {
    // Engine unreachable — all providers unavailable
  }

  // 3. Build provider → health map from the single response
  const healthMap = new Map<ModelProvider, ProviderHealth>()
  const now = Date.now()

  // Ollama health
  const ollama = providers.find((p) => p.name === 'ollama')
  healthMap.set('ollama', {
    provider: 'ollama',
    status: ollama?.available ? 'available' : 'unavailable',
    availableModels: ollama?.model ? [ollama.model] : [],
    latencyMs: providers.length > 0 ? 0 : null,
    checkedAt: now,
    error: ollama?.available ? null : 'Ollama not available',
  })

  // Azure OpenAI health
  const azure = providers.find((p) => p.name === 'azure_openai')
  healthMap.set('azure_openai', {
    provider: 'azure_openai',
    status: azure?.available ? 'available' : 'unavailable',
    availableModels: azure?.model ? [azure.model] : [],
    latencyMs: providers.length > 0 ? 0 : null,
    checkedAt: now,
    error: azure?.available ? null : 'Azure OpenAI not configured',
  })

  // OpenAI health
  const openai = providers.find((p) => p.name === 'openai')
  healthMap.set('openai', {
    provider: 'openai',
    status: openai?.available ? 'available' : 'unavailable',
    availableModels: openai?.model ? [openai.model] : [],
    latencyMs: providers.length > 0 ? 0 : null,
    checkedAt: now,
    error: openai?.available ? null : 'OpenAI not configured',
  })

  // 4. Generate availability result for each model
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

  // Ollama: if the service is available, trust it for all registered models.
  // The Engine confirms Ollama is reachable — specific models can be pulled on demand.
  // Cloud providers: provider-level availability is sufficient.

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
        `${ENGINE}/engine/llms/models`
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


// ── 4. Discover local Ollama models (not yet registered) ────────────────────────

/**
 * 发现本地 Ollama 已安装的模型
 * Discover locally installed Ollama models via /api/tags
 *
 * Returns raw list; caller should diff against registered models.
 */
export async function discoverLocalModels(): Promise<DiscoveredLocalModel[]> {
  try {
    const data = await request<{ models: any[] }>(
      `${ENGINE}/engine/llms/discover`
    ).catch(() => null)

    // If the engine exposes a /discover endpoint, use it;
    // otherwise, fall back to querying Ollama /api/tags directly.
    if (data?.models) {
      return data.models.map(mapOllamaTag)
    }

    // Fallback: query Ollama directly (same-origin or OLLAMA_BASE_URL)
    const ollamaUrl = process.env.NEXT_PUBLIC_OLLAMA_URL || 'http://localhost:11434'
    const tagsResp = await fetch(`${ollamaUrl}/api/tags`)
    if (!tagsResp.ok) return []
    const tagsData = await tagsResp.json() as { models?: any[] }
    return (tagsData.models || []).map(mapOllamaTag)
  } catch {
    return []
  }
}

/** Map an Ollama /api/tags entry to DiscoveredLocalModel */
function mapOllamaTag(m: any): DiscoveredLocalModel {
  // Ollama returns size in bytes; convert to human-readable
  const sizeBytes = m.size ?? m.sizeBytes ?? 0
  let sizeStr: string | null = null
  if (sizeBytes > 0) {
    if (sizeBytes >= 1e9) sizeStr = `${(sizeBytes / 1e9).toFixed(1)} GB`
    else if (sizeBytes >= 1e6) sizeStr = `${(sizeBytes / 1e6).toFixed(0)} MB`
    else sizeStr = `${sizeBytes} B`
  }

  return {
    name: m.name ?? m.model ?? '',
    parameterSize: m.details?.parameter_size ?? m.parameterSize ?? null,
    quantization: m.details?.quantization_level ?? m.quantization ?? null,
    family: m.details?.family ?? m.family ?? null,
    size: sizeStr,
    modifiedAt: m.modified_at ?? m.modifiedAt ?? null,
  }
}


// ── 5. Model Hub — Catalog search (MH-07) ──────────────────────────────────────

/**
 * 搜索精选模型目录
 * Search the curated Ollama model catalog
 */
export async function searchLibrary(opts?: {
  q?: string
  category?: CatalogCategory
  source?: string
  sort?: 'newest' | 'downloads' | 'name'
}): Promise<CatalogModel[]> {
  const params = new URLSearchParams()
  if (opts?.q) params.set('q', opts.q)
  if (opts?.category) params.set('category', opts.category)
  if (opts?.source) params.set('source', opts.source)
  if (opts?.sort) params.set('sort', opts.sort)
  const qs = params.toString()
  const url = `${ENGINE}/engine/llms/library/search${qs ? `?${qs}` : ''}`
  const data = await request<{ models: CatalogModel[]; count: number }>(url)
  return data.models || []
}

/**
 * 获取目录分类列表
 * Get catalog categories
 */
export async function fetchLibraryCategories(): Promise<Record<string, string>> {
  const data = await request<{ categories: Record<string, string> }>(
    `${ENGINE}/engine/llms/library/categories`
  )
  return data.categories || {}
}


// ── 6. Model Hub — Benchmark questions (MH-07) ─────────────────────────────────

/**
 * 获取标准测试问题
 * Fetch standard benchmark questions
 */
export async function fetchBenchmarkQuestions(category?: string): Promise<BenchmarkQuestion[]> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : ''
  const data = await request<{ questions: BenchmarkQuestion[]; count: number }>(
    `${ENGINE}/engine/llms/benchmark/questions${qs}`
  )
  return data.questions || []
}


// ── 7. Model Hub — Pull model (SSE) (MH-07) ────────────────────────────────────

/**
 * 从 Ollama 拉取模型（SSE 流式进度）
 * Pull a model from Ollama registry with SSE progress
 *
 * @param name  模型名称 / Model name (e.g. "qwen3:4b")
 * @param onProgress  进度回调 / Progress callback
 * @param onDone  完成回调 / Completion callback
 * @param onError  错误回调 / Error callback
 * @returns  AbortController 用于取消 / for cancellation
 */
export function pullModel(
  name: string,
  onProgress: (p: PullProgress) => void,
  onDone?: () => void,
  onError?: (err: string) => void,
): AbortController {
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(`${ENGINE}/engine/llms/models/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
        signal: controller.signal,
      })

      if (!res.ok || !res.body) {
        onError?.(`Pull failed: ${res.status}`)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6)) as PullProgress
            if (data.error) {
              onError?.(data.error)
              return
            }
            onProgress(data)
          } catch { /* skip malformed */ }
        }
      }
      onDone?.()
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err instanceof Error ? err.message : 'Pull failed')
      }
    }
  })()

  return controller
}


// ── 8. Model Hub — Benchmark test (MH-07) ──────────────────────────────────────

/**
 * 对单个模型运行测试
 * Run benchmark test on a single model
 */
export async function testModel(
  model: string,
  question: string,
  provider?: string,
): Promise<BenchmarkResult> {
  return request<BenchmarkResult>(`${ENGINE}/engine/llms/models/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, question, provider }),
  })
}

/**
 * 批量串行测试多个模型（SSE 流式结果）
 * Batch test multiple models serially (SSE streaming results)
 *
 * @param models   模型列表 / Model names
 * @param questions  测试问题列表 / Test questions
 * @param onResult  每个结果回调 / Callback for each result
 * @param onRunning 开始运行回调 / Callback when a test starts running
 * @param onDone   全部完成回调 / Callback when all done
 * @param onError  错误回调 / Error callback
 * @returns  AbortController 用于取消 / for cancellation
 */
export function testBatch(
  models: string[],
  questions: string[],
  onResult: (r: BenchmarkResult & { progress: string }) => void,
  onRunning?: (info: { model: string; question: string; progress: string }) => void,
  onDone?: (total: number) => void,
  onError?: (err: string) => void,
): AbortController {
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(`${ENGINE}/engine/llms/models/test-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ models, questions }),
        signal: controller.signal,
      })

      if (!res.ok || !res.body) {
        onError?.(`Batch test failed: ${res.status}`)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'running') {
              onRunning?.(data)
            } else if (data.type === 'result') {
              onResult(data)
            } else if (data.type === 'done') {
              onDone?.(data.total)
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError?.(err instanceof Error ? err.message : 'Batch test failed')
      }
    }
  })()

  return controller
}

