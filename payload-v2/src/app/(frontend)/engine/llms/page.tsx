'use client'

import { useEffect, useState, useMemo, useCallback, Suspense, type ReactNode } from 'react'
import {
  Brain, Loader2, AlertCircle, RefreshCw, CheckCircle2, XCircle,
  Cpu, Globe, Zap, DollarSign, Calendar,
  Search, Wifi, WifiOff, HardDrive, Clock, Trash2, Plus, Star,
  BookOpen, FlaskConical, Download, Package, MessageSquare, Code, Lightbulb, Feather,
  Microscope, Compass, ChevronDown,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type ViewMode, type SidebarItem } from '@/features/shared/components/SidebarLayout'
import { useModels } from '@/features/engine/llms/useModels'
import type { CatalogModel, ModelProvider, PullProgress } from '@/features/engine/llms/types'
import { PROVIDER_CONFIGS } from '@/features/engine/llms/types'
import { fetchCatalogFromDB, pullModel, registerModel } from '@/features/engine/llms/api'
import { useQueryState } from '@/features/shared/hooks/useQueryState'
import { useI18n } from '@/features/shared/i18n'
import { BenchmarkConsole } from '@/features/engine/llms/components/BenchmarkConsole'

type FilterKey = 'all' | 'installed' | 'benchmark' | string // string for family keys

// ── Role-based persona filter ────────────────────────────────────────────────
// 系统角色：按使用者身份筛选最合适的模型
// System personas: filter models by who is using the system
interface RoleOption {
  key: string
  label: string
  labelZh: string
  labelFr: string
  icon: ReactNode
  keywords: string[]  // matched against bestFor tags (case-insensitive)
}

const ROLE_OPTIONS: RoleOption[] = [
  { key: 'all', label: 'All Roles', labelZh: '全部角色', labelFr: 'Tous', icon: <BookOpen className="h-3.5 w-3.5" />, keywords: [] },
  { key: 'analyst', label: 'Analyst', labelZh: '分析师', labelFr: 'Analyste', icon: <FlaskConical className="h-3.5 w-3.5" />, keywords: ['analysis', 'summarization', 'rag', 'report', 'data analysis', 'insight'] },
  { key: 'student', label: 'Student', labelZh: '学生', labelFr: 'Étudiant', icon: <BookOpen className="h-3.5 w-3.5" />, keywords: ['study', 'learning', 'q&a', 'chat', 'tutoring', 'homework', 'student'] },
  { key: 'auditor', label: 'Compliance Auditor', labelZh: '合规审计员', labelFr: 'Auditeur conformité', icon: <Compass className="h-3.5 w-3.5" />, keywords: ['compliance', 'audit', 'regulation', 'verification', 'policy', 'governance'] },
  { key: 'math', label: 'Math / Reasoning', labelZh: '数学学习', labelFr: 'Maths / Raisonnement', icon: <Lightbulb className="h-3.5 w-3.5" />, keywords: ['math', 'reasoning', 'logic', 'step-by-step', 'proof', 'stem', 'calculation'] },
  { key: 'developer', label: 'Developer', labelZh: '开发者', labelFr: 'Développeur', icon: <Code className="h-3.5 w-3.5" />, keywords: ['code', 'debugging', 'refactoring', 'code review', 'development', 'api'] },
  { key: 'researcher', label: 'Researcher', labelZh: '研究员', labelFr: 'Chercheur', icon: <Microscope className="h-3.5 w-3.5" />, keywords: ['research', 'paper', 'embedding', 'semantic search', 'retrieval', 'literature'] },
  { key: 'writer', label: 'Content Writer', labelZh: '内容创作', labelFr: 'Rédacteur', icon: <Feather className="h-3.5 w-3.5" />, keywords: ['writing', 'content', 'translation', 'long-form', 'creative', 'multilingual'] },
]

// ── Source filter options ────────────────────────────────────────────────────
interface SourceOption {
  key: string
  label: string
  labelZh: string
  labelFr: string
}

const SOURCE_OPTIONS: SourceOption[] = [
  { key: 'all', label: 'All Sources', labelZh: '全部来源', labelFr: 'Toutes les sources' },
  { key: 'ollama', label: 'Ollama', labelZh: 'Ollama', labelFr: 'Ollama' },
  { key: 'huggingface', label: 'HuggingFace', labelZh: 'HuggingFace', labelFr: 'HuggingFace' },
]

// ── Type filter options ──────────────────────────────────────────────────────
interface TypeOption {
  key: string
  label: string
  labelZh: string
  labelFr: string
}

const TYPE_OPTIONS: TypeOption[] = [
  { key: 'all', label: 'All Types', labelZh: '全部类型', labelFr: 'Tous les types' },
  { key: 'chat', label: 'Chat / LLM', labelZh: '对话生成 (LLM)', labelFr: 'Chat / LLM' },
  { key: 'embedding', label: 'Embedding', labelZh: '向量嵌入 (Embedding)', labelFr: 'Embedding' },
  { key: 'vision', label: 'Vision / VLM', labelZh: '视觉看图 (VLM)', labelFr: 'Vision / VLM' },
]
// ── Family descriptions (shown as info bar when a family is selected) ─────────
const FAMILY_INFO: Record<string, { en: string; zh: string; badge: string }> = {
  qwen: {
    badge: '🇨🇳 Alibaba',
    en: 'Qwen (Tongyi Qianwen) is Alibaba\'s flagship LLM family. Strong at Chinese + English, long context (128K+), tool calling, and RAG workloads. Qwen3 is the latest dense series; Qwen3.6 is a MoE variant.',
    zh: 'Qwen（通义千问）是阿里巴巴旗舰大模型系列。中英文双语能力突出，支持长上下文（128K+）、工具调用与 RAG。Qwen3 为最新密集版，Qwen3.6 为 MoE 架构。',
  },
  llama: {
    badge: '🇺🇸 Meta',
    en: 'LLaMA (Large Language Model Meta AI) is Meta\'s open-weight model series. Llama 3.x is the current generation, widely used as a base for fine-tuning and research.',
    zh: 'LLaMA 是 Meta 开源权重大模型系列。Llama 3.x 是现役版本，被广泛用于微调和学术研究。',
  },
  gemma: {
    badge: '🇺🇸 Google',
    en: 'Gemma is Google\'s family of lightweight open models. Gemma 4 supports multimodal inputs and is optimised for on-device and edge deployment.',
    zh: 'Gemma 是 Google 的轻量级开放模型系列。Gemma 4 支持多模态输入，针对本地和边缘设备部署优化。',
  },
  phi: {
    badge: '🇺🇸 Microsoft',
    en: 'Phi is Microsoft\'s small-but-capable model family. Phi-4 achieves near-frontier reasoning at 14B parameters, making it ideal for resource-constrained environments.',
    zh: 'Phi 是微软的高性能小模型系列。Phi-4 以 140 亿参数实现接近前沿的推理能力，适合资源受限场景。',
  },
  deepseek: {
    badge: '🇨🇳 DeepSeek',
    en: 'DeepSeek is a Chinese AI lab\'s model series. DeepSeek-R1 excels at step-by-step reasoning and math, rivaling much larger models in benchmarks.',
    zh: 'DeepSeek 是中国 AI 实验室发布的模型系列。DeepSeek-R1 在数学推理和逐步思考方面表现突出，性能媲美更大的模型。',
  },
  mistral: {
    badge: '🇫🇷 Mistral AI',
    en: 'Mistral AI is a French startup specialising in efficient transformer models. Known for strong instruction-following and multilingual performance at smaller parameter counts.',
    zh: 'Mistral AI 是法国 AI 创业公司，专注高效 Transformer 模型，以较少参数实现强指令跟随和多语言能力。',
  },
  llava: {
    badge: '👁️ Vision',
    en: 'LLaVA (Large Language and Vision Assistant) is a multimodal model series that connects vision encoders with language models for image understanding.',
    zh: 'LLaVA 是连接视觉编码器与语言模型的多模态系列，支持图片理解和视觉问答。',
  },
  nomic: {
    badge: '🔢 Embedding',
    en: 'Nomic Embed is a high-performance text embedding model optimised for RAG retrieval. Supports 8K token context — much longer than most embedding models.',
    zh: 'Nomic Embed 是专为 RAG 检索优化的高性能文本嵌入模型，支持 8K token 上下文，远超大多数 Embedding 模型。',
  },
  bge: {
    badge: '🔢 Embedding',
    en: 'BGE (BAAI General Embedding) is BAAI\'s embedding model series. BGE-M3 supports 100+ languages and multiple retrieval modes (dense, sparse, multi-vector).',
    zh: 'BGE（BAAI 通用嵌入）是北京人工智能研究院的 Embedding 系列。BGE-M3 支持 100+ 语言和多种检索模式。',
  },
  mxbai: {
    badge: '🔢 Embedding',
    en: 'mxbai-embed by Mixedbread AI is a state-of-the-art embedding model that outperforms OpenAI text-embedding-3-large on MTEB at a fraction of the cost.',
    zh: 'mxbai-embed 由 Mixedbread AI 开发，在 MTEB 基准上超越 OpenAI text-embedding-3-large，成本极低。',
  },
}


export default function Page() {
  return (
    <Suspense>
      <LlmsPageInner />
    </Suspense>
  )
}

function LlmsPageInner() {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  const {
    models,
    loading,
    checking,
    error,
    refresh,
    removeOllamaModel,
    setDefaultModel,
  } = useModels({ autoLoad: true, autoCheck: true, pollInterval: 0 })

  const [filter, setFilter] = useQueryState('filter', 'all') as [FilterKey, (v: string) => void]
  const [role, setRole] = useState('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')

  // ── Catalog state ──────────────────────────────────────────────────────────
  const [catalog, setCatalog] = useState<CatalogModel[]>([])
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogLoaded, setCatalogLoaded] = useState(false)

  // Load catalog on mount — reads directly from Payload CMS DB, no Engine API call.
  useEffect(() => {
    if (catalogLoaded || catalogLoading) return
    setCatalogLoading(true)
    fetchCatalogFromDB()
      .then((data) => {
        setCatalog(data)
        setCatalogLoaded(true)
      })
      .catch(() => { })
      .finally(() => setCatalogLoading(false))
  }, [catalogLoaded, catalogLoading])

  // Reload catalog (e.g. after Sync CMS, pull, or remove).
  const reloadCatalog = useCallback(() => {
    setCatalogLoading(true)
    fetchCatalogFromDB()
      .then(setCatalog)
      .catch(() => { })
      .finally(() => setCatalogLoading(false))
  }, [])

  // ── Sync catalog → Payload CMS ─────────────────────────────────────────────
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const handleSync = useCallback(async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await fetch('/api/llms/sync-catalog', { method: 'POST', credentials: 'include' })
      const data = await res.json()
      if (data.success) {
        const prunedPart = data.pruned > 0 ? ` · ${data.pruned} pruned` : ''
        setSyncResult({ ok: true, msg: `+${data.created} created · ${data.updated} updated · ${data.skipped ?? 0} skipped${prunedPart}` })
        void refresh()       // refresh registered models count in sidebar
        reloadCatalog()      // reload catalog table from DB (now includes new models)
      } else {
        setSyncResult({ ok: false, msg: data.error || 'Sync failed' })
      }
    } catch (err) {
      setSyncResult({ ok: false, msg: err instanceof Error ? err.message : 'Network error' })
    } finally {
      setSyncing(false)
      // Auto-clear toast after 4s
      setTimeout(() => setSyncResult(null), 4000)
    }
  }, [refresh, reloadCatalog])

  // ── Computed: group catalog by normalized family ────────────────────────────
  const familyGroups = useMemo(() => {
    const groups = new Map<string, { label: string; count: number; installed: number }>()
    for (const m of catalog) {
      const key = m.family?.toLowerCase() || 'other'
      const label = m.family ? m.family.charAt(0).toUpperCase() + m.family.slice(1) : 'Other'
      const existing = groups.get(key)
      if (existing) {
        existing.count++
        if (m.installed) existing.installed++
      } else {
        groups.set(key, { label, count: 1, installed: m.installed ? 1 : 0 })
      }
    }
    // Sort by count (most models first)
    return Array.from(groups.entries()).sort((a, b) => b[1].count - a[1].count)
  }, [catalog])

  const installedCount = useMemo(() => catalog.filter((m) => m.installed).length, [catalog])
  const registeredNames = useMemo(() => new Set(models.map((m) => m.name)), [models])

  // ── Filter catalog models ──────────────────────────────────────────────────
  const displayModels = useMemo(() => {
    // Step 0: hide "generic alias" entries — uninstalled models without a concrete
    // parameter size (e.g. bare "qwen3.6" or "qwen3.6:latest" with no "7B" / "14B").
    // Installed models are always shown regardless.
    const hasConcreteSize = (m: CatalogModel) =>
      m.installed || (!!m.parameterSize && /\d/.test(m.parameterSize))
    const validCatalog = catalog.filter(hasConcreteSize)

    // Step 1: sidebar filter
    let filtered: CatalogModel[]
    if (filter === 'installed') {
      filtered = validCatalog.filter((m) => m.installed)
    } else if (filter === 'all' || filter === 'benchmark') {
      filtered = validCatalog
    } else {
      filtered = validCatalog.filter((m) => (m.family?.toLowerCase() || 'other') === filter)
    }
    // Step 2: persona/role filter
    if (role !== 'all') {
      const roleOpt = ROLE_OPTIONS.find((r) => r.key === role)
      if (roleOpt && roleOpt.keywords.length > 0) {
        const kws = roleOpt.keywords.map((k) => k.toLowerCase())
        filtered = filtered.filter((m) =>
          m.bestFor?.some((tag) => kws.some((kw) => tag.toLowerCase().includes(kw)))
        )
      }
    }
    // Step 3: source filter
    if (sourceFilter !== 'all') {
      filtered = filtered.filter((m) => m.source === sourceFilter)
    }
    // Step 4: type filter — use modelType field from DB directly
    if (typeFilter !== 'all') {
      filtered = filtered.filter((m) => m.modelType === typeFilter)
    }
    // Step 5: prefer locally pullable Ollama models, then newest/ranking.
    return [...filtered].sort((a, b) => {
      if (a.installed !== b.installed) return a.installed ? -1 : 1
      if (a.source !== b.source) return a.source === 'ollama' ? -1 : 1
      const dateA = Number((a.released || '').replace('-', '')) || 0
      const dateB = Number((b.released || '').replace('-', '')) || 0
      if (dateA !== dateB) return dateB - dateA
      return (b.likes || 0) - (a.likes || 0)
    })
  }, [catalog, filter, role, sourceFilter, typeFilter])

  // ── Sidebar items ──────────────────────────────────────────────────────────
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    const items: SidebarItem[] = [
      {
        key: 'all',
        label: isFr ? 'Tous les modèles' : 'All Models',
        count: catalog.length,
        icon: <BookOpen className="h-4 w-4 shrink-0 text-purple-400" />,
      },
      {
        key: 'installed',
        label: isFr ? 'Installés' : 'Installed',
        count: installedCount,
        icon: <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />,
        highlight: installedCount > 0,
      },
    ]

    // Add family groups
    if (familyGroups.length > 0) {
      let first = true
      for (const [key, group] of familyGroups) {
        items.push({
          key,
          label: group.label,
          count: group.count,
          dividerBefore: first,
        })
        first = false
      }
    }

    // Benchmark tab
    items.push({
      key: 'benchmark',
      label: isFr ? 'Test de performance' : 'Benchmark',
      dividerBefore: true,
      icon: <FlaskConical className="h-4 w-4 shrink-0 text-amber-400" />,
    })

    return items
  }, [catalog.length, installedCount, familyGroups, isFr])

  // ── Subtitle ───────────────────────────────────────────────────────────────
  const subtitle = useMemo(() => {
    if (filter === 'benchmark') return isFr ? 'Tester la performance des modèles' : 'Test model performance'
    const total = displayModels.length
    const inst = displayModels.filter((m) => m.installed).length
    const parts: string[] = []
    parts.push(isFr ? `${total} modèle(s)` : `${total} model(s)`)
    if (inst > 0) parts.push(isFr ? `${inst} installé(s)` : `${inst} installed`)
    if (checking) parts.push(isFr ? 'Vérification...' : 'Checking...')
    return parts.join(' · ')
  }, [filter, displayModels, checking, isFr])

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <SidebarLayout
      title={isFr ? 'Modèles' : 'Models'}
      icon={<Brain className="h-4 w-4 text-purple-400" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={(k) => setFilter(k as FilterKey)}
      sidebarFooter={
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-[10px]">
            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
            <span className="text-emerald-400">{installedCount} {isFr ? 'installé(s)' : 'installed'}</span>
            <span className="text-muted-foreground mx-1">·</span>
            <Package className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">{catalog.length - installedCount} {isFr ? 'disponible(s)' : 'available'}</span>
          </div>
          <p className="text-[10px] text-muted-foreground">
            {isFr ? `${models.length} enregistré(s) dans CMS` : `${models.length} registered in CMS`}
          </p>
        </div>
      }
      subtitle={subtitle}
      showViewToggle={false}
      toolbar={
        <div className="flex items-center gap-2">
          {/* Sync to CMS */}
          <div className="relative">
            <button
              onClick={handleSync}
              disabled={syncing}
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors border',
                syncing
                  ? 'opacity-60 cursor-not-allowed border-border text-muted-foreground'
                  : 'border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50',
              )}
              title={isFr ? 'Synchroniser vers Payload CMS' : 'Sync catalog to Payload CMS'}
            >
              {syncing
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <Package className="h-3.5 w-3.5" />}
              {isFr ? 'Sync CMS' : 'Sync CMS'}
            </button>
            {syncResult && (
              <div className={cn(
                'absolute right-0 top-full mt-1.5 z-50 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap shadow-lg border',
                syncResult.ok
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border-red-500/20',
              )}>
                {syncResult.ok
                  ? <><CheckCircle2 className="inline h-3 w-3 mr-1" />{syncResult.msg}</>
                  : <><XCircle className="inline h-3 w-3 mr-1" />{syncResult.msg}</>}
              </div>
            )}
          </div>
          {/* Refresh */}
          <button
            onClick={() => { reloadCatalog(); void refresh() }}
            className="p-2 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
            title={isFr ? 'Actualiser' : 'Refresh'}
          >
            <RefreshCw className={cn('h-4 w-4', (checking || catalogLoading) && 'animate-spin')} />
          </button>
        </div>
      }
      loading={(loading || catalogLoading) && catalog.length === 0}
      loadingText={isFr ? 'Chargement du catalogue...' : 'Loading catalog...'}
      error={error && catalog.length === 0 ? error : null}
      onRetry={() => { reloadCatalog(); void refresh() }}
    >
      {/* ── Benchmark view ── */}
      {filter === 'benchmark' ? (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <FlaskConical className="h-4 w-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-foreground">
              {isFr ? 'Test de performance des modèles' : 'Model Benchmark'}
            </h2>
          </div>
          <BenchmarkConsole models={models} isFr={isFr} />
        </div>
      ) : (
        /* ── Catalog view ── */
        <>
          {/* Filters: Persona, Source, Type as rows of pills */}
          <div className="flex flex-col gap-3 mb-5 bg-card/30 p-3 rounded-lg border border-border/50">
            {/* Persona row */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium text-muted-foreground w-14 shrink-0 uppercase tracking-wider">{isFr ? 'Persona' : 'Persona'}</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {ROLE_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    onClick={() => setRole(opt.key)}
                    className={cn(
                      'px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border',
                      role === opt.key
                        ? 'bg-primary/10 text-primary border-primary/20'
                        : 'bg-card/50 text-muted-foreground border-border hover:border-primary/30 hover:text-foreground'
                    )}
                  >
                    {isFr ? opt.labelFr : opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Source row */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium text-muted-foreground w-14 shrink-0 uppercase tracking-wider">{isFr ? 'Source' : 'Source'}</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {SOURCE_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    onClick={() => setSourceFilter(opt.key)}
                    className={cn(
                      'px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border',
                      sourceFilter === opt.key
                        ? 'bg-primary/10 text-primary border-primary/20'
                        : 'bg-card/50 text-muted-foreground border-border hover:border-primary/30 hover:text-foreground'
                    )}
                  >
                    {isFr ? opt.labelFr : opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Type row */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium text-muted-foreground w-14 shrink-0 uppercase tracking-wider">{isFr ? 'Type' : 'Type'}</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {TYPE_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    onClick={() => setTypeFilter(opt.key)}
                    className={cn(
                      'px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border',
                      typeFilter === opt.key
                        ? 'bg-primary/10 text-primary border-primary/20'
                        : 'bg-card/50 text-muted-foreground border-border hover:border-primary/30 hover:text-foreground'
                    )}
                  >
                    {isFr ? opt.labelFr : opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {catalogLoading && catalog.length > 0 && (
            <div className="flex items-center gap-2 mb-4 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {isFr ? 'Actualisation...' : 'Refreshing...'}
            </div>
          )}

          {/* Family info bar — shown when a specific family is selected */}
          {filter !== 'all' && filter !== 'installed' && filter !== 'benchmark' && FAMILY_INFO[filter] && (
            <div className="mb-4 flex items-start gap-3 px-4 py-3 rounded-lg bg-primary/5 border border-primary/15">
              <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-medium bg-primary/10 text-primary border border-primary/20">
                {FAMILY_INFO[filter].badge}
              </span>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {isFr ? FAMILY_INFO[filter].zh : FAMILY_INFO[filter].en}
              </p>
            </div>
          )}

          <CatalogTable
            models={displayModels}
            registeredNames={registeredNames}
            onPulled={reloadCatalog}
            onRemove={async (name) => {
              await removeOllamaModel(name)
              reloadCatalog()
            }}
            isFr={isFr}
          />

          {displayModels.length === 0 && !catalogLoading && (
            <div className="flex flex-col items-center py-20">
              <Brain className="h-10 w-10 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">
                {filter === 'installed'
                  ? (isFr ? 'Aucun modèle installé' : 'No installed models')
                  : (isFr ? 'Aucun modèle dans cette catégorie' : 'No models in this category')}
              </p>
            </div>
          )}
        </>
      )}
    </SidebarLayout>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════════════════════

/** Catalog table view */
function CatalogTable({
  models,
  registeredNames,
  onPulled,
  onRemove,
  isFr,
}: {
  models: CatalogModel[]
  registeredNames: Set<string>
  onPulled: () => void
  onRemove: (name: string) => Promise<void>
  isFr: boolean
}) {
  const TH = 'text-left px-4 py-2.5 text-xs font-medium text-muted-foreground lowercase tracking-wider'
  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-card/80 border-b border-border">
            <th className={TH}>{isFr ? 'modèle' : 'model'}</th>
            <th className={TH}>{isFr ? 'famille' : 'family'}</th>
            <th className={TH}>{isFr ? 'paramètres' : 'params'}</th>
            <th className={TH}>{isFr ? 'ram min.' : 'min ram'}</th>
            <th className={TH}>{isFr ? 'contexte' : 'context'}</th>
            <th className={TH}>{isFr ? 'téléchargements' : 'downloads'}</th>
            <th className={TH}>{isFr ? 'classement' : 'ranking'}</th>
            <th className={TH}>{isFr ? 'date' : 'date'}</th>
            <th className={TH}>{isFr ? 'source' : 'source'}</th>
            <th className={TH}>{isFr ? 'statut' : 'status'}</th>
            <th className={cn(TH, 'text-right')}>{isFr ? 'actions' : 'actions'}</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <CatalogTableRow
              key={m.name}
              model={m}
              isRegistered={registeredNames.has(m.name)}
              onPulled={onPulled}
              onRemove={onRemove}
              isFr={isFr}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Source badge component */
function SourceBadge({ source }: { source: string }) {
  const isOllama = source === 'ollama'
  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium',
      isOllama
        ? 'bg-blue-500/10 text-blue-400'
        : 'bg-amber-500/10 text-amber-400',
    )}>
      {isOllama ? (
        <HardDrive className="h-2.5 w-2.5" />
      ) : (
        <Globe className="h-2.5 w-2.5" />
      )}
      {isOllama ? 'Ollama' : 'HuggingFace'}
    </span>
  )
}

// ── Unified button style ─────────────────────────────────────────────────────
const BTN = 'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium transition-colors border'
const BTN_VARIANTS = {
  primary: `${BTN} bg-primary/10 text-primary hover:bg-primary/20 border-primary/20`,
  success: `${BTN} bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border-emerald-500/20`,
  danger: `${BTN} bg-red-500/10 text-red-400 hover:bg-red-500/15 border-red-500/20`,
  disabled: `${BTN} opacity-50 cursor-not-allowed border-border`,
}

// ── Status badge configs ─────────────────────────────────────────────────────
type ModelState = 'available' | 'pulling' | 'pulled' | 'registered'

const STATUS_CONFIGS: Record<ModelState, { icon: typeof CheckCircle2; label: string; labelFr: string; color: string }> = {
  available: { icon: Download, label: 'Available', labelFr: 'Disponible', color: 'text-muted-foreground' },
  pulling: { icon: Loader2, label: 'Pulling...', labelFr: 'Installation...', color: 'text-primary' },
  pulled: { icon: HardDrive, label: 'Pulled', labelFr: 'Téléchargé', color: 'text-amber-400' },
  registered: { icon: CheckCircle2, label: 'Registered', labelFr: 'Enregistré', color: 'text-emerald-400' },
}

function CatalogTableRow({
  model: m,
  isRegistered,
  onPulled,
  onRemove,
  isFr,
}: {
  model: CatalogModel
  isRegistered: boolean
  onPulled: () => void
  onRemove: (name: string) => Promise<void>
  isFr: boolean
}) {
  const [pulling, setPulling] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [progress, setProgress] = useState<PullProgress | null>(null)
  const [done, setDone] = useState(false)
  const [uninstalled, setUninstalled] = useState(false)
  const [justRegistered, setJustRegistered] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const percent = progress?.completed && progress?.total
    ? Math.round((progress.completed / progress.total) * 100)
    : 0

  // ── Determine current state ──
  const isActuallyInstalled = (m.installed || done) && !uninstalled

  const state: ModelState = pulling ? 'pulling'
    : (isRegistered || justRegistered) && isActuallyInstalled ? 'registered'
      : isActuallyInstalled ? 'pulled'
        : 'available'

  const statusCfg = STATUS_CONFIGS[state]
  const StatusIcon = statusCfg.icon

  // ── Handlers ──
  const handlePull = () => {
    if (pulling || isActuallyInstalled) return
    setPulling(true)
    setError(null)
    pullModel(
      m.name,
      (p: any) => setProgress(p),
      async () => {
        setPulling(false)
        setDone(true)
        setUninstalled(false)
        onPulled()
      },
      (err: string) => { setPulling(false); setError(err) },
    )
  }

  const handleRegister = async () => {
    setRegistering(true)
    try {
      await registerModel({ name: m.name, parameterSize: m.parameterSize, family: m.family })
      setJustRegistered(true)
      onPulled()
    } catch { /* */ }
    setRegistering(false)
  }

  const handleRemove = async () => {
    setRemoving(true)
    setError(null)
    try {
      await onRemove(m.name)
      setDone(false)
      setJustRegistered(false)
      setUninstalled(true)
    } catch (err: any) {
      setError(err.message || 'Failed to remove model')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <tr className="border-b border-border/50 hover:bg-card/50 transition-colors">
      {/* Model name + description */}
      <td className="px-4 py-3 max-w-[260px]">
        <div>
          <span className="text-sm font-medium text-foreground">{m.displayName}</span>
        </div>
        <code className="text-[11px] text-muted-foreground font-mono">{m.name}</code>
        {m.description && (
          <p className="mt-0.5 text-[11px] text-muted-foreground/70 leading-tight line-clamp-1">
            {m.description}
          </p>
        )}
        {pulling && progress && (
          <div className="mt-1">
            <div className="w-32 h-1 rounded-full bg-secondary overflow-hidden">
              <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${percent}%` }} />
            </div>
            <span className="text-[9px] text-muted-foreground">{progress.status} {percent}%</span>
          </div>
        )}
        {error && (
          <div className="mt-1 flex items-center gap-1 text-[10px] text-red-400">
            <XCircle className="h-3 w-3" />
            {error}
          </div>
        )}
      </td>
      {/* Family */}
      <td className="px-4 py-3 text-xs text-foreground capitalize">
        {m.family || 'Other'}
      </td>
      {/* Params */}
      <td className="px-4 py-3 text-xs text-foreground">{m.parameterSize || '—'}</td>
      {/* Min RAM */}
      <td className="px-4 py-3 text-xs text-foreground">
        {m.minRamGb ? `${m.minRamGb} GB` : '—'}
      </td>
      {/* Context */}
      <td className="px-4 py-3 text-xs text-foreground">
        {m.contextWindow >= 1000 ? `${(m.contextWindow / 1000).toFixed(0)}K` : m.contextWindow || '—'}
      </td>
      {/* Downloads */}
      <td className="px-4 py-3 text-xs text-foreground">
        {m.downloads > 1_000_000
          ? `${(m.downloads / 1_000_000).toFixed(1)}M`
          : m.downloads > 1_000
            ? `${(m.downloads / 1_000).toFixed(0)}K`
            : m.downloads || '—'}
      </td>
      {/* Ranking */}
      <td className="px-4 py-3 text-xs text-foreground">
        <span className="flex items-center gap-1">
          <Star className="h-3 w-3 text-amber-400" />
          {m.likes > 1_000_000
            ? `${(m.likes / 1_000_000).toFixed(1)}M`
            : m.likes > 1_000
              ? `${(m.likes / 1_000).toFixed(0)}K`
              : m.likes || '—'}
        </span>
      </td>
      {/* Date */}
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {m.released || '—'}
      </td>
      {/* Source */}
      <td className="px-4 py-3">
        <SourceBadge source={m.source} />
      </td>
      {/* Status */}
      <td className="px-4 py-3">
        <span className={cn('inline-flex items-center gap-1 text-xs', statusCfg.color)}>
          <StatusIcon className={cn('h-3 w-3', state === 'pulling' && 'animate-spin')} />
          {isFr ? statusCfg.labelFr : statusCfg.label}
        </span>
      </td>
      {/* Actions — always visible */}
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1.5">
          {state === 'available' && (
            <button onClick={handlePull} disabled={pulling} className={BTN_VARIANTS.primary}>
              <Download className="h-3 w-3" />
              Pull
            </button>
          )}
          {state === 'pulling' && (
            <button disabled className={BTN_VARIANTS.disabled}>
              <Loader2 className="h-3 w-3 animate-spin" />
              Pulling...
            </button>
          )}
          {state === 'pulled' && (
            <>
              <button onClick={handleRegister} disabled={registering} className={cn(BTN_VARIANTS.success, registering && 'opacity-50 cursor-not-allowed')}>
                {registering ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
                Register
              </button>
              <button onClick={handleRemove} disabled={removing} className={cn(BTN_VARIANTS.danger, removing && 'opacity-50 cursor-not-allowed')}>
                {removing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                Remove
              </button>
            </>
          )}
          {state === 'registered' && (
            <button onClick={handleRemove} disabled={removing} className={cn(BTN_VARIANTS.danger, removing && 'opacity-50 cursor-not-allowed')}>
              {removing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
              Remove
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}
