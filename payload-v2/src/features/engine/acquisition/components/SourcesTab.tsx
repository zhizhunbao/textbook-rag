/**
 * SourcesTab — Data source registry with table view.
 *
 * Displays data sources grouped by Consulting Persona.
 * Table columns: Name, URL, Type, Schedule, Docs, Status, Actions.
 * Clicking [Discover] crawls the source URL via Engine API for PDF discovery.
 *
 * Layout:
 *  ┌────────────────────────────────────────────────────────────────┐
 *  │ 🎓 edu-school-planning (3 sources)                            │
 *  ├──────────┬─────────────────┬──────┬─────────┬─────┬──────────┤
 *  │ Name     │ URL             │ Type │ Schedule│ Docs│ Actions  │
 *  ├──────────┼─────────────────┼──────┼─────────┼─────┼──────────┤
 *  │ DLI List │ canada.ca/...   │ web  │ monthly │ 0/0 │[Discover]│
 *  └──────────┴─────────────────┴──────┴─────────┴─────┴──────────┘
 */

'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Globe, Search, Loader2, CheckCircle2, AlertCircle,
  Download, ChevronDown, ChevronRight, ExternalLink,
  RefreshCw, AlertTriangle,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'

const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Types
// ============================================================

interface DataSource {
  id: number
  nameEn: string
  nameZh: string
  description: string
  discoveryUrl: string
  type: string
  pdfPattern?: string
  enabled: boolean
  lastSynced?: string
  docsFound: number
  docsIngested: number
  persona?: { id: number; slug: string; name: string; icon?: string } | number | null
  autoSync?: boolean
  syncInterval?: string
}

interface DiscoveredPdf {
  url: string
  filename: string
  title: string
  already_imported: boolean
  unavailable?: boolean
}

interface DiscoverResult {
  success: boolean
  source_url: string
  total_found: number
  new_count: number
  existing_count: number
  pdfs: DiscoveredPdf[]
  error?: string
}

// (Legacy grouping constants removed — persona icon now comes from persona.icon)

// ============================================================
// Component
// ============================================================

interface SourcesTabProps {
  /** Called after importing PDFs to refresh the book list */
  onBooksRefresh?: () => void
}

export default function SourcesTab({ onBooksRefresh }: SourcesTabProps) {
  const [sources, setSources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [discoverState, setDiscoverState] = useState<Record<number, {
    loading: boolean
    result?: DiscoverResult
    error?: string
  }>>({})
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [selectedPdfs, setSelectedPdfs] = useState<Record<string, boolean>>({})
  const [importing, setImporting] = useState(false)
  const [fileImportStatus, setFileImportStatus] = useState<Record<string, 'waiting' | 'importing' | 'done' | 'error'>>({})
  const [activeCategory, setActiveCategory] = useState<string>('all')

  // ── Category definitions ──
  const CATEGORIES = [
    { key: 'all',          label: 'All',           color: 'text-foreground',    bg: 'bg-secondary',        activeBg: 'bg-primary/15 border-primary/30 text-primary' },
    { key: 'immigration',  label: 'Immigration',   color: 'text-blue-400',      bg: 'bg-blue-500/10',      activeBg: 'bg-blue-500/20 border-blue-400/40 text-blue-400' },
    { key: 'education',    label: 'Education',     color: 'text-violet-400',    bg: 'bg-violet-500/10',    activeBg: 'bg-violet-500/20 border-violet-400/40 text-violet-400' },
    { key: 'career',       label: 'Career',        color: 'text-amber-400',     bg: 'bg-amber-500/10',     activeBg: 'bg-amber-500/20 border-amber-400/40 text-amber-400' },
    { key: 'finance',      label: 'Finance',       color: 'text-emerald-400',   bg: 'bg-emerald-500/10',   activeBg: 'bg-emerald-500/20 border-emerald-400/40 text-emerald-400' },
    { key: 'healthcare',   label: 'Healthcare',    color: 'text-rose-400',      bg: 'bg-rose-500/10',      activeBg: 'bg-rose-500/20 border-rose-400/40 text-rose-400' },
    { key: 'settlement',   label: 'Settlement',    color: 'text-sky-400',       bg: 'bg-sky-500/10',       activeBg: 'bg-sky-500/20 border-sky-400/40 text-sky-400' },
    { key: 'legal',        label: 'Legal',         color: 'text-orange-400',    bg: 'bg-orange-500/10',    activeBg: 'bg-orange-500/20 border-orange-400/40 text-orange-400' },
  ] as const

  // Persona slug prefix → category
  const slugToCategory = useCallback((slug: string): string => {
    if (slug.startsWith('imm-'))     return 'immigration'
    if (slug.startsWith('edu-'))     return 'education'
    if (slug.startsWith('career-'))  return 'career'
    if (slug.startsWith('fin-'))     return 'finance'
    if (slug.startsWith('health-'))  return 'healthcare'
    if (slug.startsWith('life-'))    return 'settlement'
    if (slug.startsWith('legal-'))   return 'legal'
    return 'other'
  }, [])

  // ── Fetch data sources from Payload (depth=1 to populate persona) ──
  const fetchSources = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/data-sources?limit=200&sort=nameEn&depth=1', {
        credentials: 'include',
      })
      const data = await res.json()
      setSources(data.docs ?? [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchSources() }, [fetchSources])

  // ── Category counts ──
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: sources.length }
    for (const s of sources) {
      if (s.persona && typeof s.persona === 'object') {
        const cat = slugToCategory(s.persona.slug)
        counts[cat] = (counts[cat] || 0) + 1
      }
    }
    return counts
  }, [sources, slugToCategory])

  // ── Filtered sources (flat list) ──
  const filteredSources = useMemo(() => {
    if (activeCategory === 'all') return sources
    return sources.filter((s) => {
      if (!s.persona || typeof s.persona !== 'object') return false
      return slugToCategory(s.persona.slug) === activeCategory
    })
  }, [sources, activeCategory, slugToCategory])

  // ── Discover PDFs from a source ──
  const handleDiscover = useCallback(async (source: DataSource) => {
    setDiscoverState((prev) => ({
      ...prev,
      [source.id]: { loading: true },
    }))
    setExpandedId(source.id)

    try {
      const booksRes = await fetch('/api/books?limit=500&depth=0', {
        credentials: 'include',
      })
      const booksData = await booksRes.json()
      const knownIds = (booksData.docs ?? []).map(
        (b: { engineBookId?: string }) => b.engineBookId ?? ''
      ).filter(Boolean)

      const pdfPattern = typeof source.pdfPattern === 'string' && source.pdfPattern
        ? source.pdfPattern
        : undefined
      const discoverRes = await fetch(`${ENGINE_URL}/engine/sources/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: source.discoveryUrl,
          pdf_pattern: pdfPattern,
          type: source.type,
          known_book_ids: knownIds,
        }),
      })

      if (!discoverRes.ok) {
        const text = await discoverRes.text()
        throw new Error(`Engine returned ${discoverRes.status}: ${text.slice(0, 200)}`)
      }

      const result: DiscoverResult = await discoverRes.json()

      setDiscoverState((prev) => ({
        ...prev,
        [source.id]: { loading: false, result },
      }))

      if (result.success) {
        const newSelections: Record<string, boolean> = {};
        (result.pdfs ?? []).forEach((pdf) => {
          if (!pdf.already_imported && !pdf.unavailable) {
            newSelections[pdf.url] = true
          }
        })
        setSelectedPdfs(newSelections)

        fetch(`/api/data-sources/${source.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            docsFound: result.total_found,
            docsIngested: result.existing_count,
            lastSynced: new Date().toISOString(),
          }),
        }).catch(() => { })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error
        ? err.message
        : typeof err === 'string'
          ? err
          : `Discovery failed: ${JSON.stringify(err)}`
      setDiscoverState((prev) => ({
        ...prev,
        [source.id]: { loading: false, error: msg },
      }))
    }
  }, [])

  // ── Import selected PDFs ──
  const handleImportSelected = useCallback(async (source: DataSource) => {
    const urls = Object.entries(selectedPdfs)
      .filter(([, selected]) => selected)
      .map(([url]) => url)

    if (urls.length === 0) return

    setImporting(true)
    const initialStatus: Record<string, 'waiting' | 'importing' | 'done' | 'error'> = {}
    urls.forEach((url) => { initialStatus[url] = 'waiting' })
    setFileImportStatus(initialStatus)

    for (let i = 0; i < urls.length; i++) {
      const url = urls[i]
      setFileImportStatus((prev) => ({ ...prev, [url]: 'importing' }))

      try {
        const storageCategory = (source.persona && typeof source.persona === 'object')
          ? `ca_${source.persona.slug}`
          : 'general'

        const dlRes = await fetch(`${ENGINE_URL}/engine/sources/download-pdf`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, category: storageCategory }),
        })
        if (!dlRes.ok) {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
          continue
        }
        const dlData = await dlRes.json()
        if (!dlData.success) {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
          continue
        }

        const res = await fetch('/api/books/import-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            url,
            category: storageCategory,
            fileSize: dlData.size_bytes || 0,
          }),
        })
        if (res.ok) {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'done' }))
          setSelectedPdfs((prev) => ({ ...prev, [url]: false }))
          setDiscoverState((prev) => {
            const state = prev[source.id]
            if (!state?.result) return prev
            return {
              ...prev,
              [source.id]: {
                ...state,
                result: {
                  ...state.result,
                  existing_count: state.result.existing_count + 1,
                  new_count: Math.max(0, state.result.new_count - 1),
                  pdfs: state.result.pdfs.map((p) =>
                    p.url === url ? { ...p, already_imported: true } : p
                  ),
                },
              },
            }
          })
          onBooksRefresh?.()
        } else {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
        }
      } catch {
        setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
      }
    }

    setImporting(false)
    setTimeout(() => setFileImportStatus({}), 2000)
  }, [selectedPdfs, onBooksRefresh])

  // ── Render ──
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading data sources…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertCircle className="h-4 w-4 inline mr-2" />
        {error}
        <button type="button" onClick={fetchSources} className="ml-3 text-xs underline hover:no-underline">
          Retry
        </button>
      </div>
    )
  }

  if (sources.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
        <Globe className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">No data sources configured</p>
        <p className="text-xs text-muted-foreground/70">
          Run Seed to load persona-linked data sources
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header + Category buttons */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          {CATEGORIES.map((cat) => {
            const count = categoryCounts[cat.key] || 0
            const isActive = activeCategory === cat.key
            return (
              <button
                key={cat.key}
                type="button"
                onClick={() => setActiveCategory(cat.key)}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border transition-all',
                  isActive
                    ? cat.activeBg
                    : 'border-transparent text-muted-foreground hover:bg-secondary hover:text-foreground',
                )}
              >
                {cat.label}
                <span className={cn(
                  'text-[10px] px-1.5 py-0 rounded-full font-normal',
                  isActive ? 'bg-white/10' : 'bg-muted text-muted-foreground',
                )}>
                  {count}
                </span>
              </button>
            )
          })}
        </div>
        <button
          type="button"
          onClick={fetchSources}
          className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors shrink-0"
          title="Refresh"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Single flat table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-muted-foreground">
                <th className="text-left px-3 py-2 font-medium whitespace-nowrap">Persona</th>
                <th className="text-left px-3 py-2 font-medium whitespace-nowrap">Name</th>
                <th className="text-left px-3 py-2 font-medium">URL</th>
                <th className="text-left px-3 py-2 font-medium whitespace-nowrap w-[70px]">Sync</th>
                <th className="text-center px-3 py-2 font-medium whitespace-nowrap w-[50px]">Docs</th>
                <th className="text-right px-3 py-2 font-medium whitespace-nowrap w-[70px]">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {filteredSources.map((source) => {
                const discover = discoverState[source.id]
                const isExpanded = expandedId === source.id
                const result = discover?.result

                return (
                  <SourceRow
                    key={source.id}
                    source={source}
                    discover={discover}
                    isExpanded={isExpanded}
                    result={result}
                    selectedPdfs={selectedPdfs}
                    importing={importing}
                    fileImportStatus={fileImportStatus}
                    onDiscover={() => handleDiscover(source)}
                    onToggleExpand={() => setExpandedId(isExpanded ? null : source.id)}
                    onSelectPdf={(url, checked) => setSelectedPdfs((prev) => ({ ...prev, [url]: checked }))}
                    onImportSelected={() => handleImportSelected(source)}
                  />
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}


// ============================================================
// SourceRow — Table row + expandable discovery panel
// ============================================================

interface SourceRowProps {
  source: DataSource
  discover?: { loading: boolean; result?: DiscoverResult; error?: string }
  isExpanded: boolean
  result?: DiscoverResult
  selectedPdfs: Record<string, boolean>
  importing: boolean
  fileImportStatus: Record<string, 'waiting' | 'importing' | 'done' | 'error'>
  onDiscover: () => void
  onToggleExpand: () => void
  onSelectPdf: (url: string, checked: boolean) => void
  onImportSelected: () => void
}

function SourceRow({
  source, discover, isExpanded, result,
  selectedPdfs, importing, fileImportStatus,
  onDiscover, onToggleExpand, onSelectPdf, onImportSelected,
}: SourceRowProps) {
  return (
    <>
      {/* Main row */}
      <tr className={cn(
        'transition-colors',
        !source.enabled && 'opacity-50',
        isExpanded && 'bg-muted/20',
      )}>
        {/* Persona */}
        <td className="px-3 py-2 whitespace-nowrap">
          {source.persona && typeof source.persona === 'object' ? (
            <span className="text-[11px] font-mono text-muted-foreground" title={source.persona.name}>
              {source.persona.slug}
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground/40">—</span>
          )}
        </td>

        {/* Name */}
        <td className="px-3 py-2">
          <div className="flex flex-col gap-0.5">
            <span className="font-medium text-foreground" title={source.description}>
              {source.nameEn}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {source.nameZh}
            </span>
            {!source.enabled && (
              <span className="text-[9px] text-muted-foreground bg-muted rounded px-1 py-0.5 w-fit">OFF</span>
            )}
          </div>
        </td>

        {/* URL — full, no truncation */}
        <td className="px-3 py-2">
          <a
            href={source.discoveryUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-muted-foreground hover:text-primary transition-colors group break-all"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-2.5 w-2.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
            <span>{source.discoveryUrl}</span>
          </a>
        </td>

        {/* Sync */}
        <td className="px-3 py-2 text-muted-foreground">
          {source.autoSync ? (
            <span className="text-primary">{source.syncInterval || 'weekly'}</span>
          ) : (
            <span>manual</span>
          )}
        </td>

        {/* Docs count */}
        <td className="px-3 py-2 text-center">
          {source.docsIngested > 0 ? (
            <span className="text-emerald-400">{source.docsIngested}/{source.docsFound}</span>
          ) : source.docsFound > 0 ? (
            <span className="text-muted-foreground">0/{source.docsFound}</span>
          ) : (
            <span className="text-muted-foreground/40">—</span>
          )}
        </td>

        {/* Actions */}
        <td className="px-3 py-2 text-right">
          <div className="flex items-center justify-end gap-1">
            <button
              type="button"
              onClick={onDiscover}
              disabled={discover?.loading || !source.enabled}
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-colors',
                'bg-primary/10 text-primary hover:bg-primary/20',
                'disabled:opacity-40 disabled:cursor-not-allowed',
              )}
            >
              {discover?.loading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Search className="h-3 w-3" />
              )}
            </button>
            {result && (
              <button
                type="button"
                onClick={onToggleExpand}
                className="p-1 rounded-md text-muted-foreground hover:bg-secondary transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
              </button>
            )}
          </div>
        </td>
      </tr>

      {/* Error row */}
      {discover?.error && (
        <tr>
          <td colSpan={6} className="px-4 py-2">
            <div className="px-3 py-2 rounded-lg bg-destructive/5 border border-destructive/20 text-xs text-destructive">
              <AlertCircle className="h-3 w-3 inline mr-1" />
              {discover.error}
            </div>
          </td>
        </tr>
      )}

      {/* Expanded discovery panel */}
      {result && isExpanded && (
        <tr>
          <td colSpan={6} className="px-0 py-0 bg-muted/10">
            <div className="border-t border-border/50">
              {/* Summary bar */}
              <div className="flex items-center justify-between px-4 py-2 bg-muted/20">
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-foreground font-medium">
                    {result.total_found} PDFs found
                  </span>
                  {result.new_count > 0 && (
                    <span className="text-primary font-medium">{result.new_count} new</span>
                  )}
                  {result.existing_count > 0 && (
                    <span className="text-muted-foreground">{result.existing_count} imported</span>
                  )}
                </div>

                {importing ? (
                  <div className="flex items-center gap-2 text-xs text-emerald-500">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span className="font-medium">Importing…</span>
                  </div>
                ) : result.new_count > 0 ? (
                  <button
                    type="button"
                    onClick={(e) => { e.preventDefault(); onImportSelected() }}
                    disabled={Object.values(selectedPdfs).filter(Boolean).length === 0}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      'bg-emerald-600 text-white hover:bg-emerald-700',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                    )}
                  >
                    <Download className="h-3 w-3" />
                    Import ({Object.values(selectedPdfs).filter(Boolean).length})
                  </button>
                ) : null}
              </div>

              {/* PDF list */}
              <div className="max-h-[240px] overflow-y-auto divide-y divide-border/30">
                {(result.pdfs ?? []).map((pdf) => {
                  const fStatus = fileImportStatus[pdf.url]
                  return (
                    <div
                      key={pdf.url}
                      className={cn(
                        'flex items-center gap-3 px-4 py-1.5 text-xs transition-colors',
                        pdf.already_imported
                          ? 'bg-muted/10 text-muted-foreground'
                          : pdf.unavailable
                            ? 'bg-amber-500/5 text-muted-foreground'
                            : 'hover:bg-muted/20',
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedPdfs[pdf.url] ?? false}
                        disabled={pdf.already_imported || pdf.unavailable || importing}
                        onChange={(e) => onSelectPdf(pdf.url, e.target.checked)}
                        className="h-3.5 w-3.5 rounded border-border text-primary accent-primary shrink-0"
                      />

                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-foreground truncate">{pdf.title}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{pdf.filename}</p>
                        {fStatus && (
                          <div className="mt-1 flex items-center gap-2">
                            <div className="h-1 flex-1 bg-muted rounded-full overflow-hidden">
                              <div
                                className={cn(
                                  'h-full rounded-full transition-all duration-500',
                                  fStatus === 'waiting' && 'bg-muted-foreground/30 animate-pulse',
                                  fStatus === 'importing' && 'bg-primary animate-pulse',
                                  fStatus === 'done' && 'bg-emerald-500',
                                  fStatus === 'error' && 'bg-destructive',
                                )}
                                style={{
                                  width: fStatus === 'waiting' ? '15%'
                                    : fStatus === 'importing' ? '60%' : '100%',
                                }}
                              />
                            </div>
                            <span className={cn(
                              'text-[10px] font-medium shrink-0',
                              fStatus === 'done' && 'text-emerald-500',
                              fStatus === 'error' && 'text-destructive',
                              fStatus === 'importing' && 'text-primary',
                            )}>
                              {fStatus === 'waiting' && 'Queued'}
                              {fStatus === 'importing' && 'Importing…'}
                              {fStatus === 'done' && '✓'}
                              {fStatus === 'error' && '✗'}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Status badge */}
                      {pdf.already_imported ? (
                        <CheckCircle2 className="h-3 w-3 text-emerald-500 shrink-0" />
                      ) : pdf.unavailable ? (
                        <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />
                      ) : fStatus === 'importing' ? (
                        <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                      ) : (
                        <span className="text-[10px] text-primary font-medium shrink-0">NEW</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
