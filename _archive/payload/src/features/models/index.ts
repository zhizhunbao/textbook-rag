/**
 * features/models/index.ts
 * 模型模块统一出口 / Models module barrel export
 */

// Types
export type {
  ModelProvider,
  AvailabilityStatus,
  AvailabilityResult,
  LlmModel,
  RuntimeModel,
  ProviderHealth,
  ModelOption,
  ProviderConfig,
  DiscoveredLocalModel,
  ModelDiscoveryResult,
} from './types'

export { PROVIDER_CONFIGS } from './types'

// API
export {
  fetchRegisteredModels,
  fetchEnabledModels,
  checkOllamaModels,
  checkCloudProviders,
  checkAllModels,
  fetchAvailableModels,
  discoverLocalModels,
  discoverAllModels,
  deleteModel,
  registerModel,
  removeOllamaModel,
} from './api'

// Hook
export { useModels } from './useModels'
export type { UseModelsOptions, UseModelsReturn } from './useModels'

// Context
export { ModelProvider as ModelStateProvider, useModelContext } from './ModelContext'
