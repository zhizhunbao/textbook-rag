'use client'

import { useState } from 'react'
import {
  Settings, Database, Loader2, CheckCircle2, XCircle, Brain,
  FileText, HelpCircle, RefreshCw, BookOpen,
} from 'lucide-react'

interface SeedResult {
  slug: string
  label: string
  created: number
  updated: number
  errors: string[]
}

interface SeedResponse {
  success: boolean
  results?: SeedResult[]
  error?: string
}

interface SyncResponse {
  success: boolean
  created?: number
  updated?: number
  total?: number
  errors?: string[]
  error?: string
}

const SEED_COLLECTIONS = [
  { slug: 'llm-models', label: 'LLM Models', icon: Brain, description: '预置 5 个模型配置（Qwen、Llama、DeepSeek、GPT-4o）' },
  { slug: 'prompt-modes', label: 'Prompt Modes', icon: FileText, description: '预置 4 种回答模式（Default、Learning、Analysis、Concise）' },
  { slug: 'query-templates', label: 'Query Templates', icon: HelpCircle, description: '预置 4 个问题引导模板（定义、范围、步骤、深入理解）' },
]

export default function Page() {
  // Seed state
  const [loading, setLoading] = useState<string | null>(null)
  const [results, setResults] = useState<SeedResult[]>([])
  const [error, setError] = useState<string | null>(null)

  // Sync state
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  async function handleSeed(collections?: string[]) {
    const key = collections ? collections[0] : 'all'
    setLoading(key)
    setError(null)
    setResults([])

    try {
      const res = await fetch('/api/seed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: collections ? JSON.stringify({ collections }) : '{}',
      })
      const data: SeedResponse = await res.json()

      if (data.success && data.results) {
        setResults(data.results)
      } else {
        setError(data.error || 'Unknown error')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setLoading(null)
    }
  }

  async function handleSync() {
    setSyncing(true)
    setSyncResult(null)
    setSyncError(null)

    try {
      const res = await fetch('/api/sync-engine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data: SyncResponse = await res.json()

      if (data.success) {
        setSyncResult(data)
      } else {
        setSyncError(data.error || 'Sync failed')
      }
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Page header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Settings className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">设置</h1>
          <p className="text-sm text-muted-foreground">系统管理 · 数据初始化 · 数据同步</p>
        </div>
      </div>

      {/* ═══════ Engine Sync section ═══════ */}
      <section className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-emerald-400" />
              Engine 数据同步
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              将 Engine 已处理的书籍同步到前端数据库。已存在的记录自动更新。
            </p>
          </div>
          <button
            onClick={handleSync}
            disabled={syncing || loading !== null}
            className="px-4 py-2 rounded-lg text-sm font-medium
              bg-emerald-600 hover:bg-emerald-700 text-white
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors flex items-center gap-2"
          >
            {syncing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {syncing ? '同步中...' : '同步 Engine 数据'}
          </button>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
              <BookOpen className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-medium text-foreground">Books</h3>
              <p className="text-xs text-muted-foreground">
                从 Engine SQLite 同步书籍元数据、Pipeline 状态到 Payload
              </p>
            </div>
            {syncResult && (
              <div className="flex items-center gap-1.5 text-xs shrink-0">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                <span className="text-muted-foreground">
                  {syncResult.created! > 0 && <span className="text-emerald-500">+{syncResult.created}</span>}
                  {syncResult.created! > 0 && syncResult.updated! > 0 && ' / '}
                  {syncResult.updated! > 0 && <span className="text-blue-500">↻{syncResult.updated}</span>}
                  <span className="ml-1">共 {syncResult.total} 本</span>
                </span>
              </div>
            )}
          </div>
        </div>

        {syncError && (
          <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <XCircle className="h-4 w-4 inline mr-2" />
            {syncError}
          </div>
        )}

        {syncResult && !syncError && (
          <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
            <CheckCircle2 className="h-4 w-4 inline mr-2" />
            同步完成！创建 {syncResult.created} 本，更新 {syncResult.updated} 本。
            {syncResult.errors && syncResult.errors.length > 0 && (
              <span className="text-amber-400 ml-2">
                ({syncResult.errors.length} 个错误)
              </span>
            )}
          </div>
        )}
      </section>

      {/* ═══════ Seed section ═══════ */}
      <section className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Database className="h-4 w-4 text-brand-400" />
              数据初始化 (Seed)
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              一键写入预置数据。已存在的记录会自动更新，不会产生重复。
            </p>
          </div>
          <button
            onClick={() => handleSeed()}
            disabled={loading !== null || syncing}
            className="px-4 py-2 rounded-lg text-sm font-medium
              bg-brand-500 hover:bg-brand-600 text-white
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors flex items-center gap-2"
          >
            {loading === 'all' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Database className="h-4 w-4" />
            )}
            全部初始化
          </button>
        </div>

        {/* Collection cards */}
        <div className="space-y-3">
          {SEED_COLLECTIONS.map((col) => {
            const result = results.find((r) => r.slug === col.slug)
            const isLoading = loading === col.slug || loading === 'all'

            return (
              <div
                key={col.slug}
                className="p-4 rounded-xl border border-border bg-card
                  flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                    <col.icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-medium text-foreground">{col.label}</h3>
                    <p className="text-xs text-muted-foreground truncate">{col.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {result && (
                    <div className="flex items-center gap-1.5 text-xs">
                      {result.errors.length === 0 ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-red-500" />
                      )}
                      <span className="text-muted-foreground">
                        {result.created > 0 && <span className="text-emerald-500">+{result.created}</span>}
                        {result.created > 0 && result.updated > 0 && ' / '}
                        {result.updated > 0 && <span className="text-blue-500">↻{result.updated}</span>}
                        {result.errors.length > 0 && (
                          <span className="text-red-500 ml-1">✗{result.errors.length}</span>
                        )}
                      </span>
                    </div>
                  )}

                  <button
                    onClick={() => handleSeed([col.slug])}
                    disabled={loading !== null || syncing}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium
                      border border-border bg-secondary hover:bg-muted
                      text-foreground disabled:opacity-50 disabled:cursor-not-allowed
                      transition-colors flex items-center gap-1.5"
                  >
                    {isLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      'Seed'
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <XCircle className="h-4 w-4 inline mr-2" />
            {error}
          </div>
        )}

        {results.length > 0 && !error && (
          <div className="mt-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
            <CheckCircle2 className="h-4 w-4 inline mr-2" />
            完成！共创建 {results.reduce((s, r) => s + r.created, 0)} 条，
            更新 {results.reduce((s, r) => s + r.updated, 0)} 条。
          </div>
        )}
      </section>

      {/* Placeholder */}
      <section className="mt-10 pt-6 border-t border-border">
        <p className="text-xs text-muted-foreground text-center">
          更多设置（用户偏好、API 密钥管理）即将上线
        </p>
      </section>
    </div>
  )
}
