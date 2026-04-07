'use client'

/**
 * features/seed/SeedPage.tsx
 * Data seeding management page — uses SidebarLayout for module categorization.
 *
 * Sidebar categories:
 *   - 全部 (All)         — overview of all modules
 *   - 预置数据 (Preset)  — Users, LLMs, Prompts
 *   - Engine 同步 (Sync) — Books sync from Engine v2
 *
 * Each sidebar item maps to a seed module with:
 *   module name → target collection → record count → data summary
 */

import { useState, useMemo, Suspense, type ReactNode } from 'react'
import {
  Database, Loader2, CheckCircle2, XCircle, Brain,
  FileText, RefreshCw, BookOpen, UserCog, Sparkles,
  Layers, ArrowRight,
} from 'lucide-react'
import { SidebarLayout, type SidebarItem } from '@/features/shared/components/SidebarLayout'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import { useQueryState } from '@/features/shared/hooks/useQueryState'

// ── Types ───────────────────────────────────────────────────────────────────

interface SeedResult {
  slug: string
  label: string
  created: number
  updated: number
  skipped: number
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

// ── Seed module metadata ────────────────────────────────────────────────────

type SeedCategory = 'all' | 'preset' | 'sync'

interface SeedModuleMeta {
  id: string
  label: string
  labelZh: string
  icon: React.ElementType
  category: SeedCategory
  targetCollection: string
  targetCollectionLabel: string
  description: string
  descriptionZh: string
  recordCount?: number
  dataSummary: string
  dataSummaryZh: string
}

const SEED_MODULES: SeedModuleMeta[] = [
  {
    id: 'users',
    label: 'Admin Users',
    labelZh: '管理员账户',
    icon: UserCog,
    category: 'preset',
    targetCollection: 'users',
    targetCollectionLabel: 'Users',
    description: 'Default admin account (reads SEED_ADMIN_EMAIL/PASSWORD from .env)',
    descriptionZh: '默认管理员账户（从 .env 读取 SEED_ADMIN_EMAIL/PASSWORD）',
    recordCount: 1,
    dataSummary: '1 admin user with configurable credentials',
    dataSummaryZh: '1 个管理员，凭证通过环境变量配置',
  },
  {
    id: 'llms',
    label: 'LLM Models',
    labelZh: 'LLM 模型',
    icon: Brain,
    category: 'preset',
    targetCollection: 'llms',
    targetCollectionLabel: 'Llms',
    description: '5 preset model configs: Qwen, Llama, DeepSeek, GPT-4o Mini, GPT-4o',
    descriptionZh: '预置 5 个模型：Qwen、Llama、DeepSeek、GPT-4o Mini、GPT-4o',
    recordCount: 5,
    dataSummary: '3 Ollama local + 2 Azure OpenAI cloud',
    dataSummaryZh: '3 个 Ollama 本地 + 2 个 Azure OpenAI 云',
  },
  {
    id: 'prompts',
    label: 'Prompt Modes',
    labelZh: '回答模式',
    icon: FileText,
    category: 'preset',
    targetCollection: 'prompts',
    targetCollectionLabel: 'Prompts (type=mode)',
    description: '7 answer modes: Default, Learning, Analysis, Concise, Detailed, Academic, QGen',
    descriptionZh: '7 种模式：默认、学习、分析、简洁、详细、学术、问题生成',
    recordCount: 7,
    dataSummary: 'System prompts controlling LLM answer style',
    dataSummaryZh: '控制 LLM 回答风格的系统提示词',
  },
  {
    id: 'prompts',
    label: 'Query Templates',
    labelZh: '查询模板',
    icon: FileText,
    category: 'preset',
    targetCollection: 'prompts',
    targetCollectionLabel: 'Prompts (type=template)',
    description: '4 templates: Disambiguation, Scope, Format, Follow-up',
    descriptionZh: '4 个模板：歧义消解、范围缩窄、格式引导、深入理解',
    recordCount: 4,
    dataSummary: 'Trigger patterns + suggested follow-up questions',
    dataSummaryZh: '触发模式 + 建议后续问题',
  },
  {
    id: 'books',
    label: 'Books (Engine)',
    labelZh: '书籍 (Engine)',
    icon: BookOpen,
    category: 'sync',
    targetCollection: 'books',
    targetCollectionLabel: 'Books',
    description: 'Scan Engine v2 filesystem and sync book metadata to Payload',
    descriptionZh: '扫描 Engine v2 文件系统，同步书籍元数据到 Payload',
    dataSummary: 'Title, author, PDF path, chapters from mineru_output/',
    dataSummaryZh: '书名、作者、PDF 路径、章节数，来自 mineru_output/',
  },
]

// ── Component ───────────────────────────────────────────────────────────────

export default function SeedPage() {
  return (
    <Suspense>
      <SeedPageInner />
    </Suspense>
  )
}

function SeedPageInner() {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // UI state
  const [filter, setFilter] = useQueryState('filter', 'all')

  // Seed state
  const [loading, setLoading] = useState<string | null>(null)
  const [results, setResults] = useState<SeedResult[]>([])
  const [error, setError] = useState<string | null>(null)

  // Sync state
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  // ── Sidebar items ───────────────────────────────────────────────────────

  const presetModules = SEED_MODULES.filter((m) => m.category === 'preset')
  const syncModules = SEED_MODULES.filter((m) => m.category === 'sync')
  const presetCount = presetModules.reduce((s, m) => s + (m.recordCount ?? 0), 0)

  const sidebarItems = useMemo<SidebarItem[]>(() => [
    {
      key: 'all',
      label: isZh ? '全部模块' : 'All Modules',
      count: SEED_MODULES.length,
      icon: <Layers className="h-4 w-4 shrink-0" />,
    },
    {
      key: 'preset',
      label: isZh ? '预置数据' : 'Preset Data',
      count: presetCount,
      icon: <Sparkles className="h-4 w-4 shrink-0 text-amber-400" />,
      dividerBefore: true,
    },
    ...presetModules.map((m) => {
      const Icon = m.icon
      return {
        key: `preset::${m.id}::${m.label}`,
        label: isZh ? m.labelZh : m.label,
        count: m.recordCount,
        indent: true,
        icon: <Icon className="h-4 w-4 shrink-0" />,
      }
    }),
    {
      key: 'sync',
      label: isZh ? 'Engine 同步' : 'Engine Sync',
      count: syncModules.length,
      icon: <RefreshCw className="h-4 w-4 shrink-0 text-emerald-400" />,
      dividerBefore: true,
    },
    ...syncModules.map((m) => {
      const Icon = m.icon
      return {
        key: `sync::${m.id}`,
        label: isZh ? m.labelZh : m.label,
        indent: true,
        icon: <Icon className="h-4 w-4 shrink-0" />,
      }
    }),
  ], [isZh, presetCount])

  // ── Filter logic ──────────────────────────────────────────────────────────

  const displayModules = useMemo(() => {
    if (filter === 'all') return SEED_MODULES
    if (filter === 'preset') return presetModules
    if (filter === 'sync') return syncModules
    // Sub-item: "preset::users::Admin Users" or "sync::books"
    const parts = filter.split('::')
    const moduleId = parts[1]
    const moduleLabel = parts[2] // for disambiguating prompts
    if (moduleLabel) {
      return SEED_MODULES.filter((m) => m.id === moduleId && m.label === moduleLabel)
    }
    return SEED_MODULES.filter((m) => m.id === moduleId)
  }, [filter, presetModules, syncModules])

  // ── Handlers ──────────────────────────────────────────────────────────────

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
      const res = await fetch('/api/books/sync-engine', {
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

  // ── Helpers ───────────────────────────────────────────────────────────────

  function getModuleResult(mod: SeedModuleMeta): SeedResult | null {
    const matching = results.filter((r) => r.slug === mod.id)
    if (matching.length === 0) return null
    return {
      ...matching[0],
      created: matching.reduce((s, r) => s + r.created, 0),
      updated: matching.reduce((s, r) => s + r.updated, 0),
      skipped: matching.reduce((s, r) => s + (r.skipped || 0), 0),
      errors: matching.flatMap((r) => r.errors),
    }
  }

  function renderResultBadge(result: SeedResult | null): ReactNode {
    if (!result) return null
    return (
      <div className="flex items-center gap-1.5 text-xs">
        {result.errors.length === 0 ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        ) : (
          <XCircle className="h-3.5 w-3.5 text-red-500" />
        )}
        <span className="text-muted-foreground">
          {result.created > 0 && <span className="text-emerald-500">+{result.created}</span>}
          {result.created > 0 && (result.updated > 0 || result.skipped > 0) && ' / '}
          {result.updated > 0 && <span className="text-blue-500">↻{result.updated}</span>}
          {result.updated > 0 && result.skipped > 0 && ' / '}
          {result.skipped > 0 && <span className="text-amber-500">⊘{result.skipped}</span>}
          {result.errors.length > 0 && (
            <span className="text-red-500 ml-1">✗{result.errors.length}</span>
          )}
        </span>
      </div>
    )
  }

  // ── Should show preset section vs sync section ────────────────────────────

  const showPreset = filter === 'all' || filter === 'preset' || filter.startsWith('preset::')
  const showSync = filter === 'all' || filter === 'sync' || filter.startsWith('sync::')

  const presetToShow = displayModules.filter((m) => m.category === 'preset')
  const syncToShow = displayModules.filter((m) => m.category === 'sync')

  return (
    <SidebarLayout
      title={isZh ? '数据管理' : 'Data Management'}
      icon={<Database className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={setFilter}
      subtitle={isZh ? '数据初始化 · Engine 同步' : 'Seed preset data · Sync from Engine'}
      sidebarFooter={
        <div className="space-y-1">
          <p className="text-[10px] text-muted-foreground">
            {isZh ? `${presetModules.length} 个预置模块` : `${presetModules.length} preset modules`}
          </p>
          <p className="text-[10px] text-muted-foreground">
            {isZh ? `${syncModules.length} 个同步模块` : `${syncModules.length} sync modules`}
          </p>
        </div>
      }
      toolbar={
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleSeed()}
            disabled={loading !== null || syncing}
            className="px-3 py-1.5 rounded-lg text-xs font-medium
              bg-brand-500 hover:bg-brand-600 text-white
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors flex items-center gap-1.5"
          >
            {loading === 'all' ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Database className="h-3 w-3" />
            )}
            {isZh ? '全部初始化' : 'Seed All'}
          </button>
        </div>
      }
    >
      {/* ═══════ Global status banners ═══════ */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <XCircle className="h-4 w-4 inline mr-2" />
          {error}
        </div>
      )}
      {results.length > 0 && !error && (
        <div className="mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
          <CheckCircle2 className="h-4 w-4 inline mr-2" />
          {isZh ? '完成！' : 'Done!'}{' '}
          {isZh ? '创建' : 'Created'} {results.reduce((s, r) => s + r.created, 0)},{' '}
          {isZh ? '更新' : 'Updated'} {results.reduce((s, r) => s + r.updated, 0)}
          {results.reduce((s, r) => s + (r.skipped || 0), 0) > 0 &&
            `${isZh ? '，跳过' : ', Skipped'} ${results.reduce((s, r) => s + (r.skipped || 0), 0)}`
          }
        </div>
      )}

      {/* ═══════ Preset Data section ═══════ */}
      {showPreset && presetToShow.length > 0 && (
        <section className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="h-4 w-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-foreground">
              {isZh ? '预置数据 (Seed)' : 'Preset Data (Seed)'}
            </h2>
            <span className="text-[10px] text-muted-foreground">
              {isZh
                ? '一键写入预置数据，已存在记录自动更新'
                : 'Initialize preset data, existing records auto-update'}
            </span>
          </div>

          <div className="space-y-2">
            {presetToShow.map((mod) => {
              const Icon = mod.icon
              const result = getModuleResult(mod)
              const isLoading = loading === mod.id || loading === 'all'

              return (
                <div
                  key={`${mod.id}-${mod.label}`}
                  className="p-4 rounded-xl border border-border bg-card hover:border-border/80 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    {/* Left: icon + info */}
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="w-9 h-9 rounded-lg bg-secondary flex items-center justify-center shrink-0 mt-0.5">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-medium text-foreground">
                          {isZh ? mod.labelZh : mod.label}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {isZh ? mod.descriptionZh : mod.description}
                        </p>
                        {/* Data mapping info */}
                        <div className="flex items-center gap-3 mt-2 text-[11px]">
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <ArrowRight className="h-3 w-3" />
                            <span className="font-mono text-foreground/80">{mod.targetCollectionLabel}</span>
                          </span>
                          {mod.recordCount !== undefined && (
                            <span className="text-muted-foreground">
                              {mod.recordCount} {isZh ? '条记录' : 'records'}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground/70 mt-1">
                          {isZh ? mod.dataSummaryZh : mod.dataSummary}
                        </p>
                      </div>
                    </div>

                    {/* Right: result + action */}
                    <div className="flex items-center gap-3 shrink-0">
                      {renderResultBadge(result)}
                      <button
                        onClick={() => handleSeed([mod.id])}
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
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* ═══════ Engine Sync section ═══════ */}
      {showSync && syncToShow.length > 0 && (
        <section className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-foreground">
                {isZh ? 'Engine 数据同步' : 'Engine Data Sync'}
              </h2>
              <span className="text-[10px] text-muted-foreground">
                {isZh
                  ? '扫描 Engine v2 已解析的数据，同步到前端数据库'
                  : 'Scan Engine v2 parsed data, sync to Payload DB'}
              </span>
            </div>
            <button
              onClick={handleSync}
              disabled={syncing || loading !== null}
              className="px-3 py-1.5 rounded-lg text-xs font-medium
                bg-emerald-600 hover:bg-emerald-700 text-white
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors flex items-center gap-1.5"
            >
              {syncing ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
              {syncing
                ? (isZh ? '同步中...' : 'Syncing...')
                : (isZh ? '同步 Engine 数据' : 'Sync Engine Data')}
            </button>
          </div>

          <div className="space-y-2">
            {syncToShow.map((mod) => {
              const Icon = mod.icon
              return (
                <div
                  key={mod.id}
                  className="p-4 rounded-xl border border-border bg-card hover:border-border/80 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0 mt-0.5">
                      <Icon className="h-4 w-4 text-emerald-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-medium text-foreground">
                        {isZh ? mod.labelZh : mod.label}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {isZh ? mod.descriptionZh : mod.description}
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-[11px]">
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <ArrowRight className="h-3 w-3" />
                          <span className="font-mono text-foreground/80">{mod.targetCollectionLabel}</span>
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground/70 mt-1">
                        {isZh ? mod.dataSummaryZh : mod.dataSummary}
                      </p>
                    </div>

                    {/* Sync result */}
                    {syncResult && (
                      <div className="flex items-center gap-1.5 text-xs shrink-0">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                        <span className="text-muted-foreground">
                          {syncResult.created! > 0 && <span className="text-emerald-500">+{syncResult.created}</span>}
                          {syncResult.created! > 0 && syncResult.updated! > 0 && ' / '}
                          {syncResult.updated! > 0 && <span className="text-blue-500">↻{syncResult.updated}</span>}
                          <span className="ml-1">
                            {isZh ? `共 ${syncResult.total} 本` : `${syncResult.total} total`}
                          </span>
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
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
              {isZh
                ? `同步完成！创建 ${syncResult.created} 本，更新 ${syncResult.updated} 本。`
                : `Sync complete! Created ${syncResult.created}, updated ${syncResult.updated}.`}
              {syncResult.errors && syncResult.errors.length > 0 && (
                <span className="text-amber-400 ml-2">
                  ({syncResult.errors.length} {isZh ? '个错误' : 'errors'})
                </span>
              )}
            </div>
          )}
        </section>
      )}
    </SidebarLayout>
  )
}
