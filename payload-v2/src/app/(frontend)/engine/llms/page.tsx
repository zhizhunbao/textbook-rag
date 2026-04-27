'use client'

import { useEffect, useState, useMemo, useCallback, Suspense, type ReactNode } from 'react'
import {
  Brain, Loader2, AlertCircle, RefreshCw, CheckCircle2, XCircle,
  Cpu, Globe, Zap, DollarSign, Calendar,
  Search, Wifi, WifiOff, HardDrive, Clock, Trash2, Plus, Star,
  BookOpen, FlaskConical, Download, Package, MessageSquare, Code, Lightbulb, Feather,
  Sparkles, Dog, Fish, Gem, Microscope, Wind, Compass, Wheat, Mouse, BookText, Cog,
  ChevronDown,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type ViewMode, type SidebarItem } from '@/features/shared/components/SidebarLayout'
import { useModels } from '@/features/engine/llms/useModels'
import type { CatalogModel, ModelProvider, PullProgress } from '@/features/engine/llms/types'
import { PROVIDER_CONFIGS } from '@/features/engine/llms/types'
import { searchLibrary, pullModel, registerModel } from '@/features/engine/llms/api'
import { useQueryState } from '@/features/shared/hooks/useQueryState'
import { useI18n } from '@/features/shared/i18n'
import { CatalogCard } from '@/features/engine/llms/components/CatalogCard'
import { BenchmarkConsole } from '@/features/engine/llms/components/BenchmarkConsole'

// ── Family display configs (SVG icons from Lucide) ───────────────────────────
interface FamilyConfig { label: string; icon: ReactNode; color: string }

const FAMILY_CONFIGS: Record<string, FamilyConfig> = {
  qwen: { label: 'Qwen', icon: <Sparkles className="h-4 w-4" />, color: 'text-blue-400' },
  llama: { label: 'Llama', icon: <Dog className="h-4 w-4" />, color: 'text-orange-400' },
  deepseek: { label: 'DeepSeek', icon: <Fish className="h-4 w-4" />, color: 'text-cyan-400' },
  gemma: { label: 'Gemma', icon: <Gem className="h-4 w-4" />, color: 'text-pink-400' },
  phi: { label: 'Phi', icon: <Microscope className="h-4 w-4" />, color: 'text-emerald-400' },
  mistral: { label: 'Mistral', icon: <Wind className="h-4 w-4" />, color: 'text-indigo-400' },
  nomic: { label: 'Nomic', icon: <Compass className="h-4 w-4" />, color: 'text-teal-400' },
  mxbai: { label: 'MixedBread', icon: <Wheat className="h-4 w-4" />, color: 'text-amber-400' },
  smollm2: { label: 'SmolLM', icon: <Mouse className="h-4 w-4" />, color: 'text-violet-400' },
  reader: { label: 'Jina', icon: <BookText className="h-4 w-4" />, color: 'text-rose-400' },
}

const DEFAULT_FAMILY_CONFIG: FamilyConfig = { label: 'Other', icon: <Cog className="h-4 w-4" />, color: 'text-gray-400' }

/** Normalize family key for grouping (e.g. "qwen3" → "qwen", "llama32" → "llama") */
function normalizeFamily(family: string): string {
  const f = family.toLowerCase().replace(/[^a-z]/g, '')
  if (f.startsWith('qwen')) return 'qwen'
  if (f.startsWith('llama')) return 'llama'
  if (f.startsWith('gemma')) return 'gemma'
  if (f.startsWith('phi')) return 'phi'
  if (f.startsWith('deepseek')) return 'deepseek'
  if (f.startsWith('mistral') || f.startsWith('devstral')) return 'mistral'
  if (f.startsWith('nomic')) return 'nomic'
  if (f.startsWith('mxbai')) return 'mxbai'
  if (f.startsWith('smollm')) return 'smollm2'
  if (f.startsWith('reader')) return 'reader'
  return f
}

function getFamilyConfig(family: string): FamilyConfig {
  const key = normalizeFamily(family)
  return FAMILY_CONFIGS[key] || DEFAULT_FAMILY_CONFIG
}

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
  const [viewMode, setViewMode] = useQueryState('view', 'table') as [ViewMode, (v: string) => void]
  const [role, setRole] = useState('all')
  const [sourceFilter, setSourceFilter] = useState('all')

  // ── Catalog state ──────────────────────────────────────────────────────────
  const [catalog, setCatalog] = useState<CatalogModel[]>([])
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogLoaded, setCatalogLoaded] = useState(false)

  // Load catalog on mount (not lazily)
  useEffect(() => {
    if (catalogLoaded || catalogLoading) return
    setCatalogLoading(true)
    searchLibrary()
      .then((data) => {
        setCatalog(data)
        setCatalogLoaded(true)
      })
      .catch(() => { })
      .finally(() => setCatalogLoading(false))
  }, [catalogLoaded, catalogLoading])

  // Reload catalog when models change (e.g. after pull)
  const reloadCatalog = useCallback(() => {
    setCatalogLoading(true)
    searchLibrary()
      .then(setCatalog)
      .catch(() => { })
      .finally(() => setCatalogLoading(false))
  }, [])

  // ── Computed: group catalog by normalized family ────────────────────────────
  const familyGroups = useMemo(() => {
    const groups = new Map<string, FamilyConfig & { count: number; installed: number }>()
    for (const m of catalog) {
      const key = normalizeFamily(m.family)
      const cfg = getFamilyConfig(m.family)
      const existing = groups.get(key)
      if (existing) {
        existing.count++
        if (m.installed) existing.installed++
      } else {
        groups.set(key, { ...cfg, count: 1, installed: m.installed ? 1 : 0 })
      }
    }
    // Sort by count (most models first)
    return Array.from(groups.entries()).sort((a, b) => b[1].count - a[1].count)
  }, [catalog])

  const installedCount = useMemo(() => catalog.filter((m) => m.installed).length, [catalog])
  const registeredNames = useMemo(() => new Set(models.map((m) => m.name)), [models])

  // ── Filter catalog models ──────────────────────────────────────────────────
  const displayModels = useMemo(() => {
    // Step 1: sidebar filter
    let filtered: CatalogModel[]
    if (filter === 'installed') {
      filtered = catalog.filter((m) => m.installed)
    } else if (filter === 'all' || filter === 'benchmark') {
      filtered = catalog
    } else {
      filtered = catalog.filter((m) => normalizeFamily(m.family) === filter)
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
    return filtered
  }, [catalog, filter, role, sourceFilter])

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
          icon: <span className={cn('shrink-0', group.color)}>{group.icon}</span>,
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
      showViewToggle={filter !== 'benchmark'}
      viewMode={viewMode}
      onViewModeChange={setViewMode}
      toolbar={
        <div className="flex items-center gap-2">
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
          {/* Filter dropdowns: Persona + Source / 角色 + 来源 筛选 */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            {/* Persona dropdown / 角色下拉框 */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">
                {isFr ? 'Persona' : 'Persona'}
              </span>
              <div className="relative">
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className={cn(
                    'appearance-none pl-3 pr-7 py-1.5 rounded-lg text-xs font-medium transition-all border cursor-pointer',
                    'bg-card/80 text-foreground border-border hover:border-primary/40 focus:border-primary/60',
                    'focus:outline-none focus:ring-1 focus:ring-primary/30',
                    role !== 'all' && 'border-primary/30 bg-primary/10 text-primary',
                  )}
                >
                  {ROLE_OPTIONS.map((opt) => (
                    <option key={opt.key} value={opt.key}>
                      {isFr ? opt.labelFr : opt.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
              </div>
            </div>

            {/* Source dropdown / 来源下拉框 */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">
                {isFr ? 'Source' : 'Source'}
              </span>
              <div className="relative">
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className={cn(
                    'appearance-none pl-3 pr-7 py-1.5 rounded-lg text-xs font-medium transition-all border cursor-pointer',
                    'bg-card/80 text-foreground border-border hover:border-primary/40 focus:border-primary/60',
                    'focus:outline-none focus:ring-1 focus:ring-primary/30',
                    sourceFilter !== 'all' && 'border-primary/30 bg-primary/10 text-primary',
                  )}
                >
                  {SOURCE_OPTIONS.map((opt) => (
                    <option key={opt.key} value={opt.key}>
                      {isFr ? opt.labelFr : opt.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
              </div>
            </div>

            {/* Active filter count badge */}
            {(role !== 'all' || sourceFilter !== 'all') && (
              <button
                onClick={() => { setRole('all'); setSourceFilter('all') }}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              >
                <XCircle className="h-3 w-3" />
                {isFr ? 'Réinitialiser' : 'Clear filters'}
              </button>
            )}
          </div>

          {catalogLoading && catalog.length > 0 && (
            <div className="flex items-center gap-2 mb-4 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {isFr ? 'Actualisation...' : 'Refreshing...'}
            </div>
          )}

          {viewMode === 'cards' ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {displayModels.map((cm) => (
                <CatalogCard
                  key={cm.name}
                  model={cm}
                  isRegistered={registeredNames.has(cm.name)}
                  onPulled={reloadCatalog}
                  isFr={isFr}
                />
              ))}
            </div>
          ) : (
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
          )}

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
  const TH = 'text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider'
  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-card/80 border-b border-border">
            <th className={TH}>{isFr ? 'Modèle' : 'Model'}</th>
            <th className={TH}>{isFr ? 'Famille' : 'Family'}</th>
            <th className={TH}>{isFr ? 'Paramètres' : 'Params'}</th>
            <th className={TH}>{isFr ? 'RAM min.' : 'Min RAM'}</th>
            <th className={TH}>{isFr ? 'Contexte' : 'Context'}</th>
            <th className={TH}>Downloads</th>
            <th className={TH}>{isFr ? 'Publié' : 'Released'}</th>
            <th className={TH}>Source</th>
            <th className={TH}>{isFr ? 'Statut' : 'Status'}</th>
            <th className={cn(TH, 'text-right')}>{isFr ? 'Actions' : 'Actions'}</th>
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
  const familyCfg = getFamilyConfig(m.family)
  const [pulling, setPulling] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [progress, setProgress] = useState<PullProgress | null>(null)
  const [done, setDone] = useState(false)
  const [justRegistered, setJustRegistered] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const percent = progress?.completed && progress?.total
    ? Math.round((progress.completed / progress.total) * 100)
    : 0

  // ── Determine current state ──
  const state: ModelState = pulling ? 'pulling'
    : (isRegistered || justRegistered) ? 'registered'
      : (m.installed || done) ? 'pulled'
        : 'available'

  const statusCfg = STATUS_CONFIGS[state]
  const StatusIcon = statusCfg.icon

  // ── Handlers ──
  const handlePull = () => {
    if (pulling || m.installed || done) return
    setPulling(true)
    setError(null)
    pullModel(
      m.name,
      (p: any) => setProgress(p),
      async () => {
        setPulling(false)
        setDone(true)
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
    try {
      await onRemove(m.name)
    } catch { /* */ }
    setRemoving(false)
  }

  return (
    <tr className="border-b border-border/50 hover:bg-card/50 transition-colors">
      {/* Model name */}
      <td className="px-4 py-3">
        <div>
          <span className="text-sm font-medium text-foreground">{m.displayName}</span>
        </div>
        <code className="text-[11px] text-muted-foreground font-mono">{m.name}</code>
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
      <td className="px-4 py-3">
        <span className="inline-flex items-center gap-1.5 text-xs">
          <span className={cn('shrink-0', familyCfg.color)}>{familyCfg.icon}</span>
          <span className={familyCfg.color}>{familyCfg.label}</span>
        </span>
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
      {/* Released */}
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
