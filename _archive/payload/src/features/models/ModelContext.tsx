/**
 * features/models/ModelContext.tsx
 * 全局模型状态上下文
 *
 * 在应用顶层挂载，所有组件都可以通过 useModelContext() 访问模型状态
 * Mount at app top-level; all components can access model state via useModelContext()
 */
'use client'

import {
  createContext,
  useContext,
  type ReactNode,
} from 'react'
import { useModels, type UseModelsReturn, type UseModelsOptions } from './useModels'

// ── Context ──────────────────────────────────────────────────────────────────

const ModelContext = createContext<UseModelsReturn | null>(null)

// ── Provider ─────────────────────────────────────────────────────────────────

interface ModelProviderProps {
  children: ReactNode
  /** useModels 选项 / useModels options */
  options?: UseModelsOptions
}

export function ModelProvider({ children, options }: ModelProviderProps) {
  const modelsState = useModels(options)

  return (
    <ModelContext.Provider value={modelsState}>
      {children}
    </ModelContext.Provider>
  )
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useModelContext(): UseModelsReturn {
  const ctx = useContext(ModelContext)
  if (!ctx) {
    throw new Error('useModelContext must be used within a <ModelProvider>')
  }
  return ctx
}
