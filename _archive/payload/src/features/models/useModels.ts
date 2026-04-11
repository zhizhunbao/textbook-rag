/**
 * features/models/useModels.ts
 * 模型管理 React Hook
 *
 * 提供:
 *   - 自动加载已注册模型
 *   - 自动/手动触发可用性检测
 *   - 定期轮询保持状态最新
 *   - 按 provider 分组、过滤
 *
 * Provides:
 *   - Auto-load registered models
 *   - Auto/manual availability checks
 *   - Periodic polling to keep status fresh
 *   - Group/filter by provider
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import type {
  RuntimeModel,
  ProviderHealth,
  ModelProvider,
  ModelOption,
  AvailabilityStatus,
  DiscoveredLocalModel,
  ModelDiscoveryResult,
} from './types'
import {
  fetchEnabledModels,
  checkAllModels,
  checkOllamaModels,
  checkCloudProviders,
  discoverAllModels,
  deleteModel as apiDeleteModel,
  registerModel as apiRegisterModel,
  removeOllamaModel as apiRemoveOllamaModel,
} from './api'
import type { LlmModel } from './types'

// ── 默认轮询间隔 / Default polling interval ────────────────────────────────────
const DEFAULT_POLL_INTERVAL_MS = 60_000 // 1 分钟 / 1 minute

export interface UseModelsOptions {
  /** 是否自动加载 / Auto-load on mount */
  autoLoad?: boolean
  /** 是否自动检测可用性 / Auto-check availability */
  autoCheck?: boolean
  /** 轮询间隔(ms)，0=不轮询 / Polling interval in ms, 0=disabled */
  pollInterval?: number
  /** 只加载启用的模型 / Only load enabled models */
  enabledOnly?: boolean
}

export interface UseModelsReturn {
  /** 所有模型（含可用性信息）/ All models with availability info */
  models: RuntimeModel[]
  /** 是否正在加载 / Loading state */
  loading: boolean
  /** 是否正在检测可用性 / Checking availability */
  checking: boolean
  /** 错误信息 / Error message */
  error: string | null

  /** Provider 健康状态 / Provider health status */
  providerHealth: Map<ModelProvider, ProviderHealth>

  /** 可用的模型选项（供下拉选择）/ Available model options for select */
  availableOptions: ModelOption[]
  /** 所有模型选项 / All model options */
  allOptions: ModelOption[]

  /** 自动探测到的本地未注册模型 / Auto-discovered unregistered local models */
  discovered: DiscoveredLocalModel[]
  /** 是否正在探测 / Running discovery */
  discovering: boolean

  /** 手动刷新模型列表 / Manual refresh model list */
  refresh: () => Promise<void>
  /** 手动触发可用性检测 / Manual trigger availability check */
  checkAvailability: () => Promise<void>
  /** 运行完整探测（含本地模型发现）/ Run full discovery (including local model detection) */
  runDiscovery: () => Promise<ModelDiscoveryResult | null>
  /** 按 provider 过滤 / Filter by provider */
  getModelsByProvider: (provider: ModelProvider) => RuntimeModel[]
  /** 获取默认模型 / Get default model */
  getDefaultModel: () => RuntimeModel | null
  /** 按名称查找模型 / Find model by name */
  findModel: (name: string) => RuntimeModel | undefined
  /** 删除不可用的模型 / Delete an unavailable model from CMS */
  deleteModel: (modelId: number) => Promise<void>
  /** 注册发现的模型到 CMS / Register a discovered model into CMS */
  registerDiscoveredModel: (name: string) => Promise<LlmModel | null>
  /** 从 Ollama 移除本地模型 / Remove a model from local Ollama */
  removeOllamaModel: (name: string) => Promise<void>
  /** 设为默认模型 / Set a model as the default */
  setDefaultModel: (modelId: number) => Promise<void>
}

export function useModels(options: UseModelsOptions = {}): UseModelsReturn {
  const {
    autoLoad = true,
    autoCheck = true,
    pollInterval = DEFAULT_POLL_INTERVAL_MS,
    enabledOnly = true,
  } = options

  const [models, setModels] = useState<RuntimeModel[]>([])
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [providerHealth, setProviderHealth] = useState<
    Map<ModelProvider, ProviderHealth>
  >(new Map())
  const [discovered, setDiscovered] = useState<DiscoveredLocalModel[]>([])
  const [discovering, setDiscovering] = useState(false)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)

  // ── 加载模型列表 + 检测可用性 / Load models + check availability ──────────
  const loadAndCheck = useCallback(async () => {
    if (!mountedRef.current) return
    setLoading(true)
    setError(null)

    try {
      // 一步到位: 拉取 Payload 注册模型 + 并行检测所有 provider
      // All-in-one: fetch Payload registered models + parallel check all providers
      const runtimeModels = await checkAllModels()
      if (!mountedRef.current) return
      setModels(runtimeModels)

      // 更新 provider 健康状态
      // Update provider health status
      const healthMap = new Map<ModelProvider, ProviderHealth>()
      const [ollamaH, cloudHArr] = await Promise.all([
        checkOllamaModels(),
        checkCloudProviders(),
      ])
      healthMap.set('ollama', ollamaH)
      for (const h of cloudHArr) {
        healthMap.set(h.provider, h)
      }
      if (mountedRef.current) {
        setProviderHealth(healthMap)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load models')
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  // ── 仅检测可用性（不重新加载列表）/ Check availability only ───────────────
  const checkAvailability = useCallback(async () => {
    if (!mountedRef.current) return
    setChecking(true)

    try {
      const runtimeModels = await checkAllModels()
      if (!mountedRef.current) return
      setModels(runtimeModels)
    } catch {
      // 静默失败，保留上次状态 / Silently fail, keep previous state
    } finally {
      if (mountedRef.current) {
        setChecking(false)
      }
    }
  }, [])

  // ── 完整探测（含本地模型发现）/ Full discovery (including local) ───────────
  const runDiscovery = useCallback(async (): Promise<ModelDiscoveryResult | null> => {
    if (!mountedRef.current) return null
    setDiscovering(true)

    try {
      const result = await discoverAllModels()
      if (!mountedRef.current) return null
      setModels(result.registered)
      setDiscovered(result.discovered)
      return result
    } catch {
      return null
    } finally {
      if (mountedRef.current) {
        setDiscovering(false)
      }
    }
  }, [])

  // ── 手动刷新 / Manual refresh ──────────────────────────────────────────────
  const refresh = useCallback(async () => {
    await loadAndCheck()
  }, [loadAndCheck])

  // ── 自动加载 / Auto-load ──────────────────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true
    if (autoLoad) {
      loadAndCheck()
    }
    return () => {
      mountedRef.current = false
    }
  }, [autoLoad, loadAndCheck])

  // ── 定期轮询 / Periodic polling ────────────────────────────────────────────
  useEffect(() => {
    if (pollInterval <= 0 || !autoCheck) return

    pollTimerRef.current = setInterval(() => {
      checkAvailability()
    }, pollInterval)

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [pollInterval, autoCheck, checkAvailability])

  // ── 计算属性 / Computed properties ─────────────────────────────────────────

  /** 转换为 ModelOption / Convert to ModelOption */
  const toOption = useCallback((m: RuntimeModel): ModelOption => ({
    name: m.name,
    displayName: m.displayName || m.name,
    provider: m.provider,
    isDefault: m.isDefault,
    isAvailable: m.availability.status === 'available',
    isFree: m.isFree,
    latencyMs: m.availability.latencyMs,
  }), [])

  const allOptions = useMemo(
    () => models.map(toOption),
    [models, toOption]
  )

  const availableOptions = useMemo(
    () => allOptions.filter((o) => o.isAvailable),
    [allOptions]
  )

  // ── 工具方法 / Utility methods ─────────────────────────────────────────────

  const getModelsByProvider = useCallback(
    (provider: ModelProvider) => models.filter((m) => m.provider === provider),
    [models]
  )

  const getDefaultModel = useCallback(
    () => {
      // 优先找可用的默认模型 / Prefer available default model
      const availDefault = models.find(
        (m) => m.isDefault && m.availability.status === 'available'
      )
      if (availDefault) return availDefault

      // 退而求其次：任何可用模型 / Fallback: any available model
      const anyAvailable = models.find(
        (m) => m.availability.status === 'available'
      )
      if (anyAvailable) return anyAvailable

      // 最后：任何默认模型 / Last resort: any default model
      return models.find((m) => m.isDefault) ?? models[0] ?? null
    },
    [models]
  )

  const findModel = useCallback(
    (name: string) => models.find((m) => m.name === name),
    [models]
  )

  // ── 删除模型 / Delete model ────────────────────────────────────────────────
  const deleteModel = useCallback(async (modelId: number) => {
    await apiDeleteModel(modelId)
    // 乐观更新：立即从本地状态移除 / Optimistic update: remove from local state
    if (mountedRef.current) {
      setModels((prev) => prev.filter((m) => m.id !== modelId))
    }
  }, [])

  // ── 注册发现的模型 / Register discovered model ───────────────────────────
  const registerDiscoveredModel = useCallback(async (name: string): Promise<LlmModel | null> => {
    // 从 discovered 列表中找到对应模型信息
    const disc = discovered.find((d) => d.name === name)
    try {
      const newModel = await apiRegisterModel({
        name,
        parameterSize: disc?.parameterSize ?? null,
        quantization: disc?.quantization ?? null,
        family: disc?.family ?? null,
        sizeBytes: disc?.sizeBytes ?? null,
      })
      if (mountedRef.current) {
        // 从 discovered 移除 / Remove from discovered
        setDiscovered((prev) => prev.filter((d) => d.name !== name))
        // 添加到 models 列表 / Add to registered models
        const newRuntime: RuntimeModel = {
          ...newModel,
          availability: { status: 'available', latencyMs: null, checkedAt: Date.now(), error: null },
        }
        setModels((prev) => [...prev, newRuntime])
      }
      return newModel
    } catch {
      return null
    }
  }, [discovered])

  // ── 从 Ollama 移除 / Remove from Ollama ────────────────────────────────
  const removeOllamaModel = useCallback(async (name: string) => {
    await apiRemoveOllamaModel(name)
    if (mountedRef.current) {
      // 从 discovered 移除 / Remove from discovered
      setDiscovered((prev) => prev.filter((d) => d.name !== name))
      // 如果已注册，也标记为不可用 / If registered, mark as unavailable
      setModels((prev) =>
        prev.map((m) =>
          m.name === name
            ? { ...m, availability: { status: 'unavailable' as const, latencyMs: null, checkedAt: Date.now(), error: 'Model removed from Ollama' } }
            : m
        )
      )
    }
  }, [])

  // ── 设为默认模型 / Set as default model ──────────────────────────────────
  const setDefaultModel = useCallback(async (modelId: number) => {
    // Optimistic update: set isDefault locally first
    setModels((prev) =>
      prev.map((m) => ({ ...m, isDefault: m.id === modelId }))
    )
    try {
      // Unset all other defaults, then set the new one
      const currentDefaults = models.filter((m) => m.isDefault && m.id !== modelId)
      await Promise.all(
        currentDefaults.map((m) =>
          fetch(`/api/llm-models/${m.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ isDefault: false }),
          })
        )
      )
      await fetch(`/api/llm-models/${modelId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ isDefault: true }),
      })
    } catch {
      // Revert on failure
      if (mountedRef.current) await loadAndCheck()
    }
  }, [models, loadAndCheck])

  return {
    models,
    loading,
    checking,
    error,
    providerHealth,
    availableOptions,
    allOptions,
    discovered,
    discovering,
    refresh,
    checkAvailability,
    runDiscovery,
    getModelsByProvider,
    getDefaultModel,
    findModel,
    deleteModel,
    registerDiscoveredModel,
    removeOllamaModel,
    setDefaultModel,
  }
}
