/**
 * SourcesTab — Data source registry with PDF discovery.
 *
 * Displays pre-configured data sources (seeded from project-brief.md Section 3).
 * Each source card shows: name, category, URL, sync stats, and a [Discover] button.
 * Clicking Discover crawls the source URL via Engine API and shows found PDFs.
 *
 * Layout:
 *  ┌───────────────────────────────────────────────────────┐
 *  │ 🏛️ City of Ottawa — ED Updates  [Discover] [Sync Now]│
 *  │    URL: ottawa.ca/...  │  Found: 16  │  Imported: 12  │
 *  │ ┌─ Discovered PDFs ──────────────────────────────────┐│
 *  │ │ ☑ economic_update_q1_2025.pdf       NEW            ││
 *  │ │ ☐ economic_update_q4_2024.pdf       ✅ imported    ││
 *  │ └───────────────────────────────────────────────────────┘
 *  └───────────────────────────────────────────────────────┘
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
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
  name: string
  shortName: string
  category: string
  discoveryUrl: string
  type: string
  pdfPattern?: string
  schedule: string
  icon: string
  description: string
  enabled: boolean
  lastSynced?: string
  docsFound: number
  docsIngested: number
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

// Category display config
const CATEGORY_CONFIG: Record<string, { label: string; color: string }> = {
  city: { label: 'City of Ottawa', color: 'text-blue-600 bg-blue-500/10' },
  real_estate: { label: 'Real Estate', color: 'text-emerald-600 bg-emerald-500/10' },
  tourism: { label: 'Tourism', color: 'text-purple-600 bg-purple-500/10' },
  commercial: { label: 'Commercial', color: 'text-amber-600 bg-amber-500/10' },
  research: { label: 'Research', color: 'text-cyan-600 bg-cyan-500/10' },
  news: { label: 'News', color: 'text-rose-600 bg-rose-500/10' },
}

// DataSource category → storage directory mapping (must match import-url.ts)
// DataSource category → raw_pdfs storage directory mapping
// Each category gets its own directory under data/raw_pdfs/
const CATEGORY_MAP: Record<string, string> = {
  city: 'ecdev',
  // real_estate, tourism, commercial, research, news → keep as-is
}

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
  // Per-file import status: 'waiting' | 'importing' | 'done' | 'error'
  const [fileImportStatus, setFileImportStatus] = useState<Record<string, 'waiting' | 'importing' | 'done' | 'error'>>({})

  // ── Fetch data sources from Payload ──
  const fetchSources = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/data-sources?limit=50&sort=category', {
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

  // ── Discover PDFs from a source ──
  const handleDiscover = useCallback(async (source: DataSource) => {
    setDiscoverState((prev) => ({
      ...prev,
      [source.id]: { loading: true },
    }))
    setExpandedId(source.id)

    try {
      // Get existing book IDs for dedup
      const booksRes = await fetch('/api/books?limit=500&depth=0', {
        credentials: 'include',
      })
      const booksData = await booksRes.json()
      const knownIds = (booksData.docs ?? []).map(
        (b: { engineBookId?: string }) => b.engineBookId ?? ''
      ).filter(Boolean)

      // Call engine discover API
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

      // Auto-select new PDFs
      if (result.success) {
        const newSelections: Record<string, boolean> = {};
        (result.pdfs ?? []).forEach((pdf) => {
          if (!pdf.already_imported && !pdf.unavailable) {
            newSelections[pdf.url] = true
          }
        })
        setSelectedPdfs(newSelections)

        // Update source stats in Payload
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
      console.error('[SourcesTab] discover error:', err)
      const msg = err instanceof Error
        ? err.message
        : typeof err === 'string'
          ? err
          : `Discovery failed: ${JSON.stringify(err)}`
      setDiscoverState((prev) => ({
        ...prev,
        [source.id]: {
          loading: false,
          error: msg,
        },
      }))
    }
  }, [])

  // ── Import selected PDFs via URL import ──
  const handleImportSelected = useCallback(async (source: DataSource) => {
    const urls = Object.entries(selectedPdfs)
      .filter(([, selected]) => selected)
      .map(([url]) => url)

    if (urls.length === 0) return

    setImporting(true)
    // Mark all selected as 'waiting'
    const initialStatus: Record<string, 'waiting' | 'importing' | 'done' | 'error'> = {}
    urls.forEach((url) => { initialStatus[url] = 'waiting' })
    setFileImportStatus(initialStatus)

    for (let i = 0; i < urls.length; i++) {
      const url = urls[i]
      setFileImportStatus((prev) => ({ ...prev, [url]: 'importing' }))

      try {
        // Map source category → storage category (city → ecdev)
        const storageCategory = CATEGORY_MAP[source.category] || source.category

        // Step 1: Download PDF to data/raw_pdfs/{storageCategory}/ via Engine
        const dlRes = await fetch(`${ENGINE_URL}/engine/sources/download-pdf`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url,
            category: storageCategory,
          }),
        })
        if (!dlRes.ok) {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
          continue
        }
        const dlData = await dlRes.json()
        if (!dlData.success) {
          console.error('[SourcesTab] download failed:', dlData.error)
          setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
          continue
        }

        // Step 2: Create Book record in Payload (with file size from download)
        const res = await fetch('/api/books/import-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            url,
            category: source.category,
            fileSize: dlData.size_bytes || 0,
          }),
        })
        if (res.ok) {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'done' }))
          // Uncheck imported PDF and mark as already_imported in result
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
          // Refresh sidebar after each successful import so books appear incrementally
          onBooksRefresh?.()
        } else {
          setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
        }
      } catch {
        setFileImportStatus((prev) => ({ ...prev, [url]: 'error' }))
      }
    }

    setImporting(false)
    // Clear per-file status after a short delay so user sees final state
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
        <button
          type="button"
          onClick={fetchSources}
          className="ml-3 text-xs underline hover:no-underline"
        >
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
          Run Seed → Data Sources to load pre-configured Ottawa data sources
        </p>
      </div>
    )
  }

  // Group by category
  const grouped = new Map<string, DataSource[]>()
  for (const s of sources) {
    const key = s.category || 'other'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(s)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            {sources.length} Data Sources
          </span>
          <span className="text-xs text-muted-foreground">
            from project-brief.md
          </span>
        </div>
        <button
          type="button"
          onClick={fetchSources}
          className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          title="Refresh"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Source cards grouped by category */}
      {Array.from(grouped.entries()).map(([category, catSources]) => {
        const cfg = CATEGORY_CONFIG[category] || { label: category, color: 'text-foreground bg-muted' }
        return (
          <div key={category} className="space-y-2">
            {/* Category header */}
            <div className="flex items-center gap-2">
              <span className={cn('text-xs font-semibold px-2 py-0.5 rounded-full', cfg.color)}>
                {cfg.label}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {catSources.length} source{catSources.length > 1 ? 's' : ''}
              </span>
            </div>

            {/* Source cards */}
            {catSources.map((source) => {
              const discover = discoverState[source.id]
              const isExpanded = expandedId === source.id
              const result = discover?.result

              return (
                <div
                  key={source.id}
                  className="rounded-xl border border-border bg-card overflow-hidden transition-colors hover:border-border/80"
                >
                  {/* Card header */}
                  <div className="flex items-center gap-3 px-4 py-3">
                    {/* Icon */}
                    <span className="text-lg shrink-0">{source.icon}</span>

                    {/* Info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-foreground truncate">
                          {source.name}
                        </h3>
                        {!source.enabled && (
                          <span className="text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                            Disabled
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                        {source.description}
                      </p>
                      <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                        <a
                          href={source.discoveryUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 hover:text-primary transition-colors"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink className="h-2.5 w-2.5" />
                          <span className="truncate max-w-[200px] underline decoration-dotted underline-offset-2">{source.discoveryUrl}</span>
                        </a>
                        <span className="font-mono">{source.type}</span>
                        <span>{source.schedule}</span>

                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {/* Discover button */}
                      <button
                        type="button"
                        onClick={() => handleDiscover(source)}
                        disabled={discover?.loading || !source.enabled}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                          'bg-primary text-primary-foreground hover:opacity-90',
                          'disabled:opacity-50 disabled:cursor-not-allowed',
                        )}
                      >
                        {discover?.loading ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Search className="h-3 w-3" />
                        )}
                        Discover
                      </button>

                      {/* Expand toggle */}
                      {result && (
                        <button
                          type="button"
                          onClick={() => setExpandedId(isExpanded ? null : source.id)}
                          className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronRight className="h-3.5 w-3.5" />
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Discovery result */}
                  {discover?.error && (
                    <div className="mx-4 mb-3 px-3 py-2 rounded-lg bg-destructive/5 border border-destructive/20 text-xs text-destructive">
                      <AlertCircle className="h-3 w-3 inline mr-1" />
                      {discover.error}
                    </div>
                  )}

                  {/* Expanded PDF list */}
                  {result && isExpanded && (
                    <div className="border-t border-border">
                      {/* Summary bar */}
                      <div className="flex items-center justify-between px-4 py-2 bg-muted/30">
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-foreground font-medium">
                            {result.total_found} PDFs found
                          </span>
                          {result.new_count > 0 && (
                            <span className="text-primary font-medium">
                              {result.new_count} new
                            </span>
                          )}
                          {result.existing_count > 0 && (
                            <span className="text-muted-foreground">
                              {result.existing_count} already imported
                            </span>
                          )}
                        </div>

                        {/* Import button (stays in place, no page navigation) */}
                        {importing ? (
                          <div className="flex items-center gap-2 text-xs text-emerald-500">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            <span className="font-medium">Importing…</span>
                          </div>
                        ) : result.new_count > 0 ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              handleImportSelected(source)
                            }}
                            disabled={Object.values(selectedPdfs).filter(Boolean).length === 0}
                            className={cn(
                              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                              'bg-emerald-600 text-white hover:bg-emerald-700',
                              'disabled:opacity-50 disabled:cursor-not-allowed',
                            )}
                          >
                            <Download className="h-3 w-3" />
                            Import Selected ({Object.values(selectedPdfs).filter(Boolean).length})
                          </button>
                        ) : null}
                      </div>

                      {/* PDF list */}
                      <div className="max-h-[300px] overflow-y-auto divide-y divide-border/50">
                        {(result.pdfs ?? []).map((pdf) => {
                          const fStatus = fileImportStatus[pdf.url]
                          return (
                            <div
                              key={pdf.url}
                              className={cn(
                                'flex items-center gap-3 px-4 py-2 text-xs transition-colors',
                                pdf.already_imported
                                  ? 'bg-muted/20 text-muted-foreground'
                                  : pdf.unavailable
                                    ? 'bg-amber-500/5 text-muted-foreground'
                                    : 'hover:bg-muted/30',
                              )}
                            >
                              {/* Checkbox */}
                              <input
                                type="checkbox"
                                checked={selectedPdfs[pdf.url] ?? false}
                                disabled={pdf.already_imported || pdf.unavailable || importing}
                                onChange={(e) => setSelectedPdfs((prev) => ({
                                  ...prev,
                                  [pdf.url]: e.target.checked,
                                }))}
                                className="h-3.5 w-3.5 rounded border-border text-primary accent-primary shrink-0"
                              />

                              {/* File info + per-file progress bar */}
                              <div className="min-w-0 flex-1">
                                <p className="font-medium text-foreground truncate">
                                  {pdf.title}
                                </p>
                                <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                                  {pdf.filename}
                                </p>
                                {/* Per-file progress bar — only shown during import batch */}
                                {fStatus && (
                                  <div className="mt-1.5 flex items-center gap-2">
                                    <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
                                      <div
                                        className={cn(
                                          'h-full rounded-full transition-all duration-500 ease-out',
                                          fStatus === 'waiting' && 'bg-muted-foreground/30 w-[15%] animate-pulse',
                                          fStatus === 'importing' && 'bg-primary w-[60%] animate-pulse',
                                          fStatus === 'done' && 'bg-emerald-500 w-full',
                                          fStatus === 'error' && 'bg-destructive w-full',
                                        )}
                                        style={{
                                          width: fStatus === 'waiting' ? '15%'
                                            : fStatus === 'importing' ? '60%'
                                            : '100%',
                                        }}
                                      />
                                    </div>
                                    <span className={cn(
                                      'text-[10px] font-medium shrink-0',
                                      fStatus === 'waiting' && 'text-muted-foreground',
                                      fStatus === 'importing' && 'text-primary',
                                      fStatus === 'done' && 'text-emerald-500',
                                      fStatus === 'error' && 'text-destructive',
                                    )}>
                                      {fStatus === 'waiting' && 'Queued'}
                                      {fStatus === 'importing' && 'Importing…'}
                                      {fStatus === 'done' && '✓ Done'}
                                      {fStatus === 'error' && '✗ Failed'}
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* Status badge */}
                              {pdf.already_imported ? (
                                <span className="flex items-center gap-1 text-[10px] text-emerald-500 shrink-0">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Imported
                                </span>
                              ) : pdf.unavailable ? (
                                <span className="flex items-center gap-1 text-[10px] text-amber-500 shrink-0" title="PDF not yet published by the source">
                                  <AlertTriangle className="h-3 w-3" />
                                  Not Published
                                </span>
                              ) : fStatus === 'importing' ? (
                                <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                              ) : fStatus === 'done' ? (
                                <span className="flex items-center gap-1 text-[10px] text-emerald-500 shrink-0">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Done
                                </span>
                              ) : fStatus === 'error' ? (
                                <span className="flex items-center gap-1 text-[10px] text-destructive shrink-0">
                                  <AlertCircle className="h-3 w-3" />
                                  Error
                                </span>
                              ) : (
                                <span className="text-[10px] text-primary font-medium shrink-0">
                                  NEW
                                </span>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
