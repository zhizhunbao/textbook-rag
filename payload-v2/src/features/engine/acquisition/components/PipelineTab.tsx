/**
 * PipelineTab — 3-column pipeline status + execution + output viewer.
 *
 * Layout: Pipeline Stepper (220px) │ Execute Panel (~300px) │ Output Panel (~400px)
 *
 * Data source: Payload CMS
 *   - Books.pipeline (parse / ingest)
 *   - IngestTasks collection — task progress / log / error
 *   - Engine API — trigger ingest
 *
 * 2-stage pipeline:
 *   - Parse:  MinerU PDF parsing → content_list.json
 *   - Ingest: Reader → Chunking → Embedding → ChromaDB → Payload sync
 *
 * Ref: AQ-08 — Pipeline Tab (v6 two-stage design)
 */

'use client'

import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  Play,
  RefreshCw,
  Copy,
  Zap,
  FileSearch,
  Database,
  Square,
  Activity,
  ChevronDown,
  ChevronRight,
  Radio,
  Maximize2,
  Minimize2,
  CheckSquare,
  SquareDashedBottom,
  Layers,
  SkipForward,
  BookOpen,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { cn } from '@/features/shared/utils'
import { authFetch } from '@/features/shared/authFetch'
import type { BookBase, PipelineStage, PipelineInfo } from '@/features/shared/books'

// ============================================================
// Constants
// ============================================================
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'
const POLL_TASKS_MS = 1500

// ============================================================
// Types
// ============================================================
type PipelineKey = 'parse' | 'ingest'

interface IngestTask {
  id: number
  taskType: string
  book: { id: number; title: string } | number | null
  status: 'queued' | 'running' | 'done' | 'error'
  progress: number
  log: string | null
  error: string | null
  startedAt: string | null
  finishedAt: string | null
}

// ============================================================
// Props
// ============================================================
interface PipelineTabProps {
  books: BookBase[]
  filter: string
  /** Callback to re-fetch books list from DB (ensures pipeline status persists). */
  onBooksRefresh?: () => void
}

// ============================================================
// Stage config
// ============================================================
interface StepDetail {
  label: string
  labelFr: string
  input: string
  inputZh: string
  output: string | string[]
  outputZh: string | string[]
}

interface StageConfig {
  key: PipelineKey
  label: string
  labelFr: string
  icon: React.ElementType
  description: string
  descriptionZh: string
  steps: StepDetail[]
}

const STAGES: StageConfig[] = [
  {
    key: 'parse',
    label: 'Parse', labelFr: '解析',
    icon: FileSearch,
    description: 'MinerU parses PDF into structured content_list.json.',
    descriptionZh: 'MinerU 将 PDF 解析为结构化 content_list.json。',
    steps: [
      {
        label: 'Run MinerU (layout + OCR)',
        labelFr: '运行 MinerU（版面分析 + OCR）',
        input: 'data/raw_pdfs/{category}/{filename}.pdf',
        inputZh: 'data/raw_pdfs/{category}/{filename}.pdf',
        output: 'mineru_output/{category}/{book}/auto/',
        outputZh: 'mineru_output/{category}/{book}/auto/',
      },
      {
        label: 'Generate content_list.json',
        labelFr: '生成 content_list.json',
        input: 'MinerU layout analysis results',
        inputZh: 'MinerU 版面分析结果',
        output: ['{book}_content_list.json', '{book}.md', 'images/'],
        outputZh: ['{book}_content_list.json', '{book}.md', 'images/'],
      },
    ],
  },
  {
    key: 'ingest',
    label: 'Ingest', labelFr: '入库',
    icon: Database,
    description: 'LlamaIndex pipeline: chunk → embed → ChromaDB → Payload sync.',
    descriptionZh: 'LlamaIndex 流水线：分块 → 嵌入 → ChromaDB → Payload 同步。',
    steps: [
      {
        label: 'Read MinerU output → Document[]',
        labelFr: '读取 MinerU 输出 → Document[]',
        input: '{book}_content_list.json',
        inputZh: '{book}_content_list.json',
        output: 'LlamaIndex Document[] (N docs)',
        outputZh: 'LlamaIndex Document[] (N 篇)',
      },
      {
        label: 'Chunking + embedding via IngestionPipeline',
        labelFr: '通过 IngestionPipeline 分块 + 嵌入',
        input: 'Document[] + HuggingFace model',
        inputZh: 'Document[] + HuggingFace 模型',
        output: 'TextNode[] with embeddings',
        outputZh: '带嵌入向量的 TextNode[]',
      },
      {
        label: 'Upsert vectors into ChromaDB',
        labelFr: '向量 upsert 到 ChromaDB',
        input: 'TextNode[] with embeddings',
        inputZh: '带嵌入向量的 TextNode[]',
        output: 'ChromaDB collection updated',
        outputZh: 'ChromaDB collection 已更新',
      },
      {
        label: 'Push chunk metadata to Payload CMS',
        labelFr: '推送 chunk 元数据到 Payload CMS',
        input: 'TextNode[] metadata',
        inputZh: 'TextNode[] 元数据',
        output: 'Payload chunks collection',
        outputZh: 'Payload chunks collection',
      },
    ],
  },
]

// ============================================================
// Status config
// ============================================================
const STAGE_STATUS: Record<PipelineStage, {
  icon: React.ElementType
  color: string
  bg: string
  border: string
  label: string
  labelFr: string
}> = {
  done: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', label: 'Done', labelFr: '完成' },
  pending: { icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted/50', border: 'border-border', label: 'Pending', labelFr: '待处理' },
  error: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', label: 'Error', labelFr: '错误' },
}

const TASK_STATUS: Record<string, { icon: React.ElementType; color: string; label: string; labelFr: string }> = {
  queued: { icon: Clock, color: 'text-muted-foreground', label: 'Queued', labelFr: '排队中' },
  running: { icon: Loader2, color: 'text-amber-400', label: 'Running', labelFr: '运行中' },
  done: { icon: CheckCircle2, color: 'text-emerald-400', label: 'Done', labelFr: '完成' },
  error: { icon: AlertTriangle, color: 'text-red-400', label: 'Error', labelFr: '错误' },
}

// ============================================================
// Component
// ============================================================
export default function PipelineTab({ books, filter, onBooksRefresh }: PipelineTabProps) {
  const { locale } = useI18n()
  const isFr = locale === 'fr'

  // ==========================================================
  // State
  // ==========================================================
  const [activeStage, setActiveStage] = useState<PipelineKey>('parse')
  const [tasks, setTasks] = useState<IngestTask[]>([])
  const [loadingTasks, setLoadingTasks] = useState(false)
  const [triggerLoading, setTriggerLoading] = useState(false)
  const [cancelLoading, setCancelLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)
  const [expandedTasks, setExpandedTasks] = useState<Set<number>>(new Set())
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [inspectorTarget, setInspectorTarget] = useState<{
    stageKey: PipelineKey; stepIdx: number; direction: 'in' | 'out'
  } | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [inspectData, setInspectData] = useState<any>(null)
  const [inspectLoading, setInspectLoading] = useState(false)
  const logRef = useRef<HTMLPreElement>(null)
  const [sseLines, setSseLines] = useState<string[]>([])
  const sseRef = useRef<EventSource | null>(null)
  const [logExpanded, setLogExpanded] = useState(true)
  // SSE-driven live step tracking (which step is currently executing)
  const [liveStepIdx, setLiveStepIdx] = useState<number>(-1)

  // — Resizable panel widths (same pattern as EvaluationPage)
  const [stepperWidth, setStepperWidth] = useState(220)
  const [executeWidth, setExecuteWidth] = useState(320)

  // Local override for pipeline status (optimistic reset on re-run)
  const [pipelineOverride, setPipelineOverride] = useState<Partial<PipelineInfo> | null>(null)

  // ==========================================================
  // Selected book (from sidebar filter)
  // ==========================================================
  const selectedBook = useMemo(() => {
    if (filter === 'all' || !filter) return null
    if (filter.startsWith('book::')) {
      const bookId = filter.slice(6)
      return books.find((b) => b.book_id === bookId) ?? null
    }
    return null
  }, [books, filter])

  // Pipeline info from book (merged with local override for optimistic UI)
  const pipeline: PipelineInfo = useMemo(() => {
    const base = selectedBook?.pipeline || { parse: 'pending' as const, ingest: 'pending' as const }
    if (pipelineOverride) {
      return { ...base, ...pipelineOverride }
    }
    return base
  }, [selectedBook, pipelineOverride])

  // Auto-advance stepper when DB pipeline data changes
  useEffect(() => {
    // Clear optimistic override — real DB state has arrived
    setPipelineOverride(null)
    const bp = selectedBook?.pipeline
    if (bp?.parse === 'done' && bp?.ingest !== 'done') {
      setActiveStage('ingest')
    }
  }, [selectedBook?.pipeline])

  // Resolve template placeholders in step paths with actual book data
  const resolvePath = useCallback((tpl: string) => {
    if (!selectedBook) return tpl
    // Use engineBookId (engine's actual dir name) if available, otherwise derive from title
    // Unicode-aware: \p{L} matches any letter (Chinese, Korean, etc.), \p{N} any digit
    const bookDirName = selectedBook.book_id !== String(selectedBook.id)
      ? selectedBook.book_id
      : (selectedBook.title || '').toLowerCase()
        .replace(/[^\p{L}\p{N}\s_-]/gu, '')
        .replace(/[\s-]+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '') || `book_${selectedBook.id}`
    const pdfName = (selectedBook as any)?.pdfMedia?.filename || `${bookDirName}.pdf`
    return tpl
      .replace(/\{filename\}/g, pdfName.replace(/\.pdf$/i, ''))
      .replace(/\{category\}/g, selectedBook.category || 'textbook')
      .replace(/\{book\}/g, bookDirName)
  }, [selectedBook])

  // ==========================================================
  // Fetch IngestTasks
  // ==========================================================
  const fetchTasks = useCallback(async () => {
    if (!selectedBook) return
    setLoadingTasks(true)
    try {
      const params = new URLSearchParams({
        limit: '50',
        depth: '1',
        sort: '-createdAt',
        'where[book][equals]': selectedBook.id.toString(),
      })
      const res = await authFetch(`/api/ingest-tasks?${params}`)
      if (res.ok) {
        const data = await res.json()
        setTasks(data.docs ?? [])
      }
    } catch (e) {
      console.error('Failed to fetch ingest tasks:', e)
    } finally {
      setLoadingTasks(false)
    }
  }, [selectedBook])

  useEffect(() => { fetchTasks() }, [fetchTasks])

  // ==========================================================
  // Auto-poll when tasks are running
  // ==========================================================
  // Treat tasks older than 10 minutes as stale — they no longer block the button
  const STALE_MS = 10 * 60 * 1000
  const activeQueuedTasks = tasks.filter((t) => t.status === 'running' || t.status === 'queued')
  const hasRunning = activeQueuedTasks.some((t) => {
    const createdAt = (t as any).createdAt || t.startedAt
    if (!createdAt) return false
    return Date.now() - new Date(createdAt).getTime() < STALE_MS
  })
  // Stale tasks = queued/running but older than threshold
  const hasStale = activeQueuedTasks.length > 0 && !hasRunning

  useEffect(() => {
    if (!hasRunning) return
    const interval = setInterval(fetchTasks, POLL_TASKS_MS)
    return () => clearInterval(interval)
  }, [hasRunning, fetchTasks])

  // ==========================================================
  // Auto-scroll log
  // ==========================================================
  // Most recent task (running or latest completed) — for log display
  // Hide stale tasks when pipeline hasn't been started (both stages pending)
  const activeTask = tasks.find((t) => t.status === 'running')
  const pipelineNeverRun = pipeline.parse === 'pending' && pipeline.ingest === 'pending'
  const latestTask = activeTask || (pipelineNeverRun ? null : tasks[0]) || null
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [latestTask?.log, sseLines])

  // ==========================================================
  // SSE real-time log stream
  // ==========================================================
  useEffect(() => {
    if (!selectedBook || !hasRunning) {
      // Close SSE when not running
      if (sseRef.current) {
        sseRef.current.close()
        sseRef.current = null
      }
      return
    }

    // Already connected?
    if (sseRef.current) return

    // Clear previous lines and connect
    setSseLines([])
    const url = `${ENGINE_URL}/engine/ingest/stream/${selectedBook.id}`
    const es = new EventSource(url)
    sseRef.current = es

    es.onmessage = (ev) => {
      const line = ev.data as string
      setSseLines((prev) => {
        const next = [...prev, line]
        return next.length > 500 ? next.slice(-500) : next
      })

      // ── SSE-driven stage/step auto-tracking ──
      const msg = line.toLowerCase()

      // Parse stage: step 0 (Run MinerU)
      if (msg.includes('parsing pdf with mineru') || msg.includes('running mineru parse') || msg.includes('force re-parse')) {
        setPipelineOverride(prev => ({ ...prev, parse: 'pending' as const, ingest: 'pending' as const }))
        setActiveStage('parse')
        setLiveStepIdx(0)
        setExpandedSteps(prev => new Set([...prev, 'parse-0']))
      }
      // Parse stage: step 1 (content_list generated)
      else if (msg.includes('mineru parse complete') || msg.includes('mineru output found') || msg.includes('mineru output already exists')) {
        setLiveStepIdx(1)
        setExpandedSteps(prev => new Set([...prev, 'parse-1']))
      }
      // Ingest stage: step 0 (Reading MinerU output)
      else if (msg.includes('reading mineru output')) {
        setPipelineOverride({ parse: 'done' as const, ingest: 'pending' as const })
        setActiveStage('ingest')
        setLiveStepIdx(0)
        setExpandedSteps(prev => new Set([...prev, 'ingest-0']))
      }
      // Ingest stage: step 1 (Chunking + embedding)
      else if (msg.includes('read') && msg.includes('documents') || msg.includes('read') && msg.includes('chunks')) {
        setLiveStepIdx(1)
        setExpandedSteps(prev => new Set([...prev, 'ingest-1']))
      }
      // Ingest stage: step 2 (Upsert vectors into ChromaDB)
      else if (msg.includes('applying transformations') || msg.includes('ingested') && msg.includes('chromadb')) {
        setLiveStepIdx(2)
        setExpandedSteps(prev => new Set([...prev, 'ingest-2']))
      }
      // Ingest stage: step 3 (Push chunk metadata to Payload)
      else if (msg.includes('deleting') && msg.includes('chunks') || msg.includes('pushed batch') || msg.includes('chunk push complete')) {
        setLiveStepIdx(3)
        setExpandedSteps(prev => new Set([...prev, 'ingest-3']))
      }
      // Done — look for both "ingest complete" (from _notify to task log)
      // and "chunk push complete" (loguru message that IS in SSE stream)
      else if (msg.includes('ingest complete') || msg.includes('chunk push complete')) {
        setPipelineOverride({ parse: 'done' as const, ingest: 'done' as const })
        setLiveStepIdx(-1)
      }
    }

    es.addEventListener('done', () => {
      es.close()
      sseRef.current = null
      setLiveStepIdx(-1)
      // Mark pipeline as done (in case onmessage didn't catch it)
      setPipelineOverride({ parse: 'done' as const, ingest: 'done' as const })
      // Refresh tasks to get final status
      fetchTasks()

      // Sync pageCount + fileSize from engine → Payload metadata
      if (selectedBook) {
        ; (async () => {
          try {
            const engineRes = await fetch(`${ENGINE_URL}/engine/books`)
            if (engineRes.ok) {
              const engineBooks: Array<{ book_id: string; page_count?: number; chunk_count?: number; pdf_size_bytes?: number }> = await engineRes.json()
              const match = engineBooks.find((eb) => eb.book_id === selectedBook.book_id)
              if (match && (match.page_count || match.pdf_size_bytes)) {
                await authFetch(`/api/books/${selectedBook.id}`, {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    metadata: {
                      pageCount: match.page_count ?? 0,
                      fileSize: match.pdf_size_bytes ?? 0,
                    },
                    chunkCount: match.chunk_count ?? 0,
                  }),
                })
              }
            }
          } catch (e) {
            console.warn('Failed to sync engine metadata:', e)
          }
        })()
      }

      // Re-fetch books so DB pipeline status persists across page refreshes
      setTimeout(() => onBooksRefresh?.(), 1500)
    })

    es.addEventListener('error', () => {
      // EventSource auto-reconnects on network errors.
      // If it's a fatal error (stream closed), just clean up.
      if (es.readyState === EventSource.CLOSED) {
        sseRef.current = null
      }
    })

    return () => {
      es.close()
      sseRef.current = null
    }
  }, [selectedBook, hasRunning, fetchTasks])

  // ==========================================================
  // Fetch inspect data when target changes
  // ==========================================================
  useEffect(() => {
    if (!inspectorTarget || !selectedBook) {
      setInspectData(null)
      return
    }
    const { stageKey, stepIdx, direction } = inspectorTarget
    setInspectLoading(true)
    setInspectData(null)

    const fetchInspect = async () => {
      try {
        const bookId = selectedBook.id

        // Fetch book with depth=1 (includes pdfMedia + pipeline output)
        const bookRes = await authFetch(`/api/books/${bookId}?depth=1`)
        if (!bookRes.ok) return
        const doc = await bookRes.json()
        const po = doc.pipeline?.parseOutput
        const io = doc.pipeline?.ingestOutput
        const media = typeof doc.pdfMedia === 'object' ? doc.pdfMedia : null

        // ─── Parse stage (all data from DB: pipeline.parseOutput) ──
        if (stageKey === 'parse') {

          // Step 1: Run MinerU (layout + OCR)
          if (stepIdx === 0 && direction === 'in') {
            // IN: PDF file info (from Payload pdfMedia)
            setInspectData(media ? {
              _type: 'pdf',
              filename: media.filename,
              mimeType: media.mimeType,
              filesize: `${(media.filesize / 1048576).toFixed(2)} MB`,
              url: media.url,
            } : {
              _type: 'path',
              path: resolvePath('data/raw_pdfs/{category}/{filename}.pdf'),
              source: 'filesystem (not uploaded via Payload)',
              category: doc.category || 'textbook',
              title: doc.title,
            })
          } else if (stepIdx === 0 && direction === 'out') {
            // OUT: MinerU output directory (from DB: parseOutput.fileTree)
            setInspectData({
              _type: 'directory',
              outputPath: po?.outputPath || resolvePath('mineru_output/{category}/{book}/auto/'),
              contentListExists: po?.contentListExists,
              mdExists: po?.mdExists,
              imagesCount: po?.imagesCount,
              fileTree: po?.fileTree || [],
            })
          }

          // Step 2: Generate content_list.json
          else if (stepIdx === 1 && direction === 'in') {
            // IN: MinerU layout analysis (from DB: parseOutput)
            setInspectData({
              _type: 'directory',
              outputPath: po?.outputPath || resolvePath('mineru_output/{category}/{book}/auto/'),
              contentListCount: po?.contentListCount,
              imagesCount: po?.imagesCount,
              fileTree: po?.fileTree || [],
            })
          } else if (stepIdx === 1 && direction === 'out') {
            // OUT: content_list.json sample entries (from DB: parseOutput.sample)
            setInspectData(po ? {
              _type: 'json_sample',
              contentListCount: po.contentListCount,
              sample: po.sample,
            } : {
              _type: 'path',
              path: resolvePath('{book}_content_list.json'),
              status: doc.pipeline?.parse === 'done' ? 'generated' : 'waiting for parse',
            })
          }
        }

        // ─── Ingest stage ──────────────────────────────
        if (stageKey === 'ingest') {

          // Step 1: Read MinerU output → Document[]
          if (stepIdx === 0 && direction === 'in') {
            // IN: content_list.json (same as parse step 2 OUT)
            setInspectData(po ? {
              _type: 'json_sample',
              contentListCount: po.contentListCount,
              sample: po.sample,
            } : {
              _type: 'path',
              path: resolvePath('{book}_content_list.json'),
              status: doc.pipeline?.parse === 'done' ? 'available' : 'pending parse',
            })
          } else if (stepIdx === 0 && direction === 'out') {
            // OUT: LlamaIndex Document[] — show count + sample docs
            setInspectData(io ? {
              _type: 'documents',
              documentCount: io.nodeCount || '—',
              readerType: 'MinerUReader',
              metadataFields: ['book_id', 'category', 'content_type', 'page_idx', 'bbox', 'reading_order'],
            } : {
              _type: 'path',
              path: 'LlamaIndex Document[]',
              status: doc.pipeline?.ingest === 'done' ? 'available' : 'waiting for ingest',
            })
          }

          // Step 2: Chunking + embedding via IngestionPipeline
          else if (stepIdx === 1 && direction === 'in') {
            // IN: Document[] + model info
            setInspectData({
              _type: 'model_info',
              documentCount: io?.nodeCount || '—',
              embeddingModel: 'all-MiniLM-L6-v2',
              transformations: ['BBoxNormalizer', 'HuggingFaceEmbedding'],
              vectorDimensions: 384,
            })
          } else if (stepIdx === 1 && direction === 'out') {
            // OUT: TextNode[] with embeddings — sample from chunks
            const chunksRes = await authFetch(`/api/chunks?where[book][equals]=${bookId}&limit=3&depth=0`)
            const chunkData = chunksRes.ok ? await chunksRes.json() : null
            setInspectData({
              _type: 'text_nodes',
              totalNodes: chunkData?.totalDocs ?? io?.nodeCount ?? '—',
              embeddingDimensions: 384,
              embeddingModel: 'all-MiniLM-L6-v2',
              sample: chunkData?.docs?.slice(0, 3)?.map((d: any) => ({
                chunkId: d.chunkId,
                contentType: d.contentType,
                pageNumber: d.pageNumber,
                text: d.text?.slice(0, 150) + (d.text?.length > 150 ? '…' : ''),
                vectorized: d.vectorized,
              })),
            })
          }

          // Step 3: Upsert vectors into ChromaDB
          else if (stepIdx === 2 && direction === 'in') {
            // IN: TextNode[] with embeddings (stats)
            setInspectData({
              _type: 'text_nodes',
              totalNodes: io?.nodeCount ?? '—',
              embeddingDimensions: 384,
              embeddingModel: 'all-MiniLM-L6-v2',
            })
          } else if (stepIdx === 2 && direction === 'out') {
            // OUT: ChromaDB collection stats
            setInspectData({
              _type: 'chroma',
              chromaCollection: io?.chromaCollection || 'textbook_chunks',
              chromaPersistDir: io?.chromaPersistDir || 'data/chroma_persist',
              nodeCount: io?.nodeCount ?? '—',
              status: doc.pipeline?.ingest === 'done' ? 'synced' : 'pending',
            })
          }

          // Step 4: Push chunk metadata to Payload CMS
          else if (stepIdx === 3 && direction === 'in') {
            // IN: TextNode[] metadata (sample of what gets pushed)
            const chunksRes = await authFetch(`/api/chunks?where[book][equals]=${bookId}&limit=2&depth=0`)
            const chunkData = chunksRes.ok ? await chunksRes.json() : null
            setInspectData({
              _type: 'chunk_metadata',
              totalNodes: io?.nodeCount ?? '—',
              fieldsToSync: ['chunkId', 'book', 'text', 'contentType', 'pageNumber', 'sourceLocators', 'vectorized'],
              sample: chunkData?.docs?.slice(0, 2)?.map((d: any) => ({
                chunkId: d.chunkId,
                contentType: d.contentType,
                pageNumber: d.pageNumber,
                text: d.text?.slice(0, 100) + (d.text?.length > 100 ? '…' : ''),
              })),
            })
          } else if (stepIdx === 3 && direction === 'out') {
            // OUT: Payload chunks collection — final results
            const chunksRes = await authFetch(`/api/chunks?where[book][equals]=${bookId}&limit=3&depth=0`)
            if (chunksRes.ok) {
              const data = await chunksRes.json()
              setInspectData({
                _type: 'payload_chunks',
                totalChunks: data.totalDocs,
                chromaCollection: io?.chromaCollection,
                nodeCount: io?.nodeCount,
                sample: data.docs?.slice(0, 3)?.map((d: any) => ({
                  chunkId: d.chunkId,
                  contentType: d.contentType,
                  pageNumber: d.pageNumber,
                  text: d.text?.slice(0, 120) + (d.text?.length > 120 ? '…' : ''),
                  vectorized: d.vectorized,
                })),
              })
            }
          }
        }
      } catch (e) {
        setInspectData({ error: String(e) })
      } finally {
        setInspectLoading(false)
      }
    }
    fetchInspect()
  }, [inspectorTarget, selectedBook])

  // ==========================================================
  // Trigger action
  // ==========================================================
  const triggerAction = useCallback(async () => {
    if (!selectedBook) return

    // If parse already done, confirm re-parse with user
    let forceParse = false
    if (pipeline.parse === 'done') {
      const msg = isFr
        ? 'MinerU 解析结果已存在。\n是否删除缓存并重新解析？（耗时较长）'
        : 'MinerU parse output already exists.\nDelete cache and re-parse? (this may take a while)'
      forceParse = window.confirm(msg)
      if (!forceParse && pipeline.ingest === 'done') {
        // User declined re-parse, and ingest is also done — nothing to do
        return
      }
    }

    setTriggerLoading(true)
    setActiveStage('parse')
    setSseLines([])
    // Optimistically reset pipeline status so stepper shows "pending"
    setPipelineOverride({
      parse: forceParse ? 'pending' : pipeline.parse,
      ingest: 'pending',
    })
    try {
      // 1. Fetch book with pdfMedia populated to get filename
      const bookRes = await authFetch(`/api/books/${selectedBook.id}?depth=1`)
      if (!bookRes.ok) throw new Error(`Failed to fetch book: ${bookRes.status}`)
      const bookDoc = await bookRes.json()

      const pdfMedia = bookDoc.pdfMedia
      const pdfFilename: string | undefined =
        typeof pdfMedia === 'object' ? pdfMedia?.filename : undefined

      if (!pdfFilename) {
        console.warn('No PDF file linked to this book')
      }

      // 2. Create IngestTask for progress tracking
      const taskRes = await authFetch('/api/ingest-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskType: 'ingest',
          book: selectedBook.id,
          status: 'queued',
          progress: 0,
        }),
      })
      const taskDoc = taskRes.ok ? await taskRes.json() : null
      const taskId = taskDoc?.doc?.id ?? null

      // 3. POST to Engine
      const engineRes = await fetch(`${ENGINE_URL}/engine/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          book_id: selectedBook.id,
          pdf_filename: pdfFilename,
          title: selectedBook.title,
          category: selectedBook.category,
          task_id: taskId,
          force_parse: forceParse,
        }),
      })

      if (!engineRes.ok) {
        const errText = await engineRes.text()
        throw new Error(`Engine returned ${engineRes.status}: ${errText}`)
      }

      // 4. Refresh tasks after short delay
      setTimeout(() => fetchTasks(), 1000)
    } catch (e) {
      console.error('Failed to trigger pipeline:', e)
      // Revert optimistic override on error
      setPipelineOverride(null)
    } finally {
      setTriggerLoading(false)
    }
  }, [selectedBook, pipeline, isFr, fetchTasks])

  // ==========================================================
  // Cancel pipeline
  // ==========================================================
  const cancelPipeline = useCallback(async () => {
    if (!selectedBook) return
    setCancelLoading(true)
    try {
      const res = await fetch(`${ENGINE_URL}/engine/ingest/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: selectedBook.id }),
      })
      if (!res.ok) {
        console.error('Cancel failed:', await res.text())
      }
      // Refresh tasks after short delay to pick up status change
      setTimeout(() => fetchTasks(), 1500)
    } catch (e) {
      console.error('Failed to cancel pipeline:', e)
    } finally {
      setCancelLoading(false)
    }
  }, [selectedBook, fetchTasks])

  // ==========================================================
  // Reset stale tasks
  // ==========================================================
  const resetStaleTasks = useCallback(async () => {
    if (!selectedBook) return
    setResetLoading(true)
    try {
      const res = await fetch(`${ENGINE_URL}/engine/ingest/reset-tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: selectedBook.id }),
      })
      if (res.ok) {
        const data = await res.json()
        console.log(`Reset ${data.reset_count} stale tasks`)
      }
      // Refresh tasks immediately
      await fetchTasks()
    } catch (e) {
      console.error('Failed to reset stale tasks:', e)
    } finally {
      setResetLoading(false)
    }
  }, [selectedBook, fetchTasks])

  // ==========================================================
  // Resize drag handler (same pattern as EvaluationPage)
  // ==========================================================
  const createDragHandler = useCallback(
    (setter: React.Dispatch<React.SetStateAction<number>>, min: number, max: number) => {
      return (e: React.MouseEvent) => {
        e.preventDefault()
        const startX = e.clientX
        let startWidth = 0
        setter(w => { startWidth = w; return w })

        const onMove = (ev: MouseEvent) => {
          const delta = ev.clientX - startX
          setter(Math.min(max, Math.max(min, startWidth + delta)))
        }
        const onUp = () => {
          document.removeEventListener('mousemove', onMove)
          document.removeEventListener('mouseup', onUp)
          document.body.style.cursor = ''
          document.body.style.userSelect = ''
        }
        document.addEventListener('mousemove', onMove)
        document.addEventListener('mouseup', onUp)
        document.body.style.cursor = 'col-resize'
        document.body.style.userSelect = 'none'
      }
    },
    [],
  )

  // ==========================================================
  // Helpers
  // ==========================================================
  const copyText = (text: string) => navigator.clipboard.writeText(text)

  const fmtDate = (d: string | null) => {
    if (!d) return '—'
    return new Date(d).toLocaleString(isFr ? 'zh-CN' : 'en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  }

  const toggleTask = (id: number) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  // ==========================================================
  // No book selected → Batch Pipeline View
  // ==========================================================
  if (!selectedBook) {
    return (
      <BatchPipelineView
        books={books}
        filter={filter}
        isFr={isFr}
        onBooksRefresh={onBooksRefresh}
      />
    )
  }

  // ==========================================================
  // Active stage config
  // ==========================================================
  const stageConfig = STAGES.find((s) => s.key === activeStage)!
  const stageStatus: PipelineStage = pipeline[activeStage]
  const statusCfg = STAGE_STATUS[stageStatus]

  // All tasks (no stage filtering needed — both stages run as one ingest job)
  const stageTasks = tasks

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <div className="space-y-4">
      {/* ── Toolbar ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground">
                {isFr ? stageConfig.labelFr : stageConfig.label}
              </h3>
              <span className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium',
                statusCfg.bg, statusCfg.color,
              )}>
                {isFr ? statusCfg.labelFr : statusCfg.label}
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {isFr ? stageConfig.descriptionZh : stageConfig.description}
            </p>
          </div>
        </div>
        <button
          onClick={fetchTasks}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border
                     text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
        >
          <RefreshCw className={cn('h-3 w-3', loadingTasks && 'animate-spin')} />
          {isFr ? '刷新' : 'Refresh'}
        </button>
      </div>

      {/* ── 3-column layout (flex + resize handles, same as EvaluationPage) ── */}
      <div className="flex overflow-hidden rounded-lg border border-border" style={{ height: 'calc(100vh - 280px)', minHeight: '360px' }}>

        {/* ════════════════════════════════════════════════
            LEFT: Pipeline Stepper (2 stages)
            ════════════════════════════════════════════════ */}
        <div className="flex flex-col shrink-0 border-r border-border p-3" style={{ width: stepperWidth }}>
          <div className="flex-1">
            {STAGES.map((stage, idx) => {
              const st = pipeline[stage.key]
              const sc = STAGE_STATUS[st]
              const Icon = sc.icon
              const isActive = activeStage === stage.key
              const isLast = idx === STAGES.length - 1
              const isDone = st === 'done'
              const isError = st === 'error'

              return (
                <div key={stage.key}>
                  {/* Stage button */}
                  <button
                    type="button"
                    onClick={() => setActiveStage(stage.key)}
                    className={cn(
                      'w-full text-left px-2.5 py-2.5 rounded-lg transition-all duration-200 flex items-center gap-3',
                      isActive
                        ? 'bg-gradient-to-r from-primary/8 to-transparent border border-primary/20'
                        : 'hover:bg-secondary/40 border border-transparent',
                    )}
                  >
                    {/* Status circle */}
                    <div className={cn(
                      'w-7 h-7 rounded-full flex items-center justify-center shrink-0 ring-[1.5px]',
                      isDone ? 'bg-emerald-500/15 ring-emerald-500/30' :
                        isError ? 'bg-red-500/15 ring-red-500/30' :
                          isActive ? 'bg-primary/10 ring-primary/30' :
                            'bg-muted ring-border',
                    )}>
                      <Icon className={cn(
                        'h-3.5 w-3.5',
                        isDone ? 'text-emerald-500' :
                          isError ? 'text-red-500' :
                            isActive ? 'text-primary' :
                              'text-muted-foreground/50',
                      )} />
                    </div>

                    {/* Label + status */}
                    <div className="flex-1 min-w-0">
                      <span className={cn(
                        'text-[13px] font-semibold block leading-tight',
                        isActive ? 'text-foreground' : 'text-muted-foreground',
                      )}>
                        {isFr ? stage.labelFr : stage.label}
                      </span>
                      <span className={cn(
                        'text-[10px] font-medium mt-0.5 block',
                        isDone ? 'text-emerald-500' :
                          isError ? 'text-red-500' :
                            'text-muted-foreground/50',
                      )}>
                        {isFr ? sc.labelFr : sc.label}
                      </span>
                    </div>
                  </button>

                  {/* Connector line between stages */}
                  {!isLast && (
                    <div className="flex items-center pl-6 h-6">
                      <div className={cn(
                        'w-px h-full',
                        isDone ? 'bg-emerald-500/40' :
                          isError ? 'bg-red-500/30' :
                            'bg-border',
                      )} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Action buttons — Run / Cancel / Reset */}
          <div className="mt-4 space-y-1.5">
            {hasRunning ? (
              /* Cancel button — visible when pipeline is actively running */
              <button
                onClick={cancelPipeline}
                disabled={cancelLoading}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-md
                           bg-red-600 text-white text-xs font-medium
                           hover:bg-red-700 disabled:opacity-40 transition-colors"
              >
                {cancelLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}
                {isFr ? '取消 Pipeline' : 'Cancel Pipeline'}
              </button>
            ) : (
              /* Run / Re-run button — visible when idle */
              <button
                onClick={triggerAction}
                disabled={triggerLoading}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-md
                           bg-primary text-primary-foreground text-xs font-medium
                           hover:bg-primary/90 disabled:opacity-40 transition-colors"
              >
                {triggerLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                {pipeline.parse === 'done' && pipeline.ingest === 'done'
                  ? (isFr ? '重新运行' : 'Re-run Pipeline')
                  : (isFr ? '运行 Pipeline' : 'Run Pipeline')}
              </button>
            )}
            {/* Reset stale tasks — only show when there are stale (old) queued/running tasks */}
            {hasStale && !hasRunning && (
              <button
                onClick={resetStaleTasks}
                disabled={resetLoading}
                className="w-full inline-flex items-center gap-1.5 justify-center px-3 py-1.5 rounded-md
                           border border-border text-[10px] text-muted-foreground
                           hover:text-foreground hover:bg-secondary/50 disabled:opacity-40 transition-colors"
              >
                {resetLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                {isFr ? '清理僵尸任务' : 'Reset Stale Tasks'}
              </button>
            )}
          </div>
        </div>

        {/* Stepper ↔ Execute resize handle */}
        <div
          className="w-1 shrink-0 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors relative group"
          onMouseDown={createDragHandler(setStepperWidth, 160, 300)}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>

        {/* ════════════════════════════════════════════════
            MIDDLE: Execute Panel
            ════════════════════════════════════════════════ */}
        <div className="flex flex-col shrink-0 border-r border-border p-4 overflow-y-auto" style={{ width: executeWidth }}>

          {/* Steps list (expandable) */}
          <div className="space-y-0.5 mb-3">
            {stageConfig.steps.map((step, i) => {
              const stepDone = stageStatus === 'done'
              const stepError = stageStatus === 'error' && i === stageConfig.steps.length - 1
              const isExpanded = expandedSteps.has(`${activeStage}-${i}`)
              const toggleStep = () => {
                setExpandedSteps(prev => {
                  const next = new Set(prev)
                  const key = `${activeStage}-${i}`
                  next.has(key) ? next.delete(key) : next.add(key)
                  return next
                })
              }
              return (
                <div key={i}>
                  <button
                    type="button"
                    onClick={toggleStep}
                    className={cn(
                      'w-full text-left flex items-center gap-1.5 py-1 px-1.5 rounded transition-colors',
                      hasRunning && liveStepIdx === i
                        ? 'bg-primary/10 text-primary font-medium'
                        : stepDone ? 'text-foreground hover:bg-secondary/30' :
                          stepError ? 'text-red-400 hover:bg-secondary/30' :
                            'text-muted-foreground hover:bg-secondary/30',
                    )}
                  >
                    {hasRunning && liveStepIdx === i
                      ? <Loader2 className="h-3 w-3 shrink-0 animate-spin" />
                      : isExpanded
                        ? <ChevronDown className="h-3 w-3 shrink-0" />
                        : <ChevronRight className="h-3 w-3 shrink-0" />}
                    <span className="text-[11px] leading-relaxed">
                      <span className="text-muted-foreground/40 mr-1">{i + 1}.</span>
                      {isFr ? step.labelFr : step.label}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="ml-6 mt-0.5 mb-1.5 space-y-1 text-[10px]">
                      <button
                        type="button"
                        onClick={() => setInspectorTarget({ stageKey: activeStage, stepIdx: i, direction: 'in' })}
                        className={cn(
                          'flex items-start gap-1.5 w-full text-left rounded px-1 py-0.5 transition-colors',
                          inspectorTarget?.stageKey === activeStage && inspectorTarget?.stepIdx === i && inspectorTarget?.direction === 'in'
                            ? 'bg-primary/10' : 'hover:bg-secondary/30',
                        )}
                      >
                        <span className="text-muted-foreground/60 shrink-0 uppercase tracking-wider font-medium" style={{ fontSize: '9px' }}>IN</span>
                        <span className="text-muted-foreground font-mono">{resolvePath(isFr ? step.inputZh : step.input)}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setInspectorTarget({ stageKey: activeStage, stepIdx: i, direction: 'out' })}
                        className={cn(
                          'flex items-start gap-1.5 w-full text-left rounded px-1 py-0.5 transition-colors',
                          inspectorTarget?.stageKey === activeStage && inspectorTarget?.stepIdx === i && inspectorTarget?.direction === 'out'
                            ? 'bg-emerald-500/10' : 'hover:bg-secondary/30',
                        )}
                      >
                        <span className="text-emerald-500/60 shrink-0 uppercase tracking-wider font-medium" style={{ fontSize: '9px' }}>OUT</span>
                        {(() => {
                          const raw = isFr ? step.outputZh : step.output
                          const items = Array.isArray(raw) ? raw : [raw]
                          return (
                            <span className="text-muted-foreground font-mono flex flex-col">
                              {items.map((item, j) => (
                                <span key={j}>{resolvePath(item)}</span>
                              ))}
                            </span>
                          )
                        })()}
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Divider */}
          <div className="border-t border-border my-2" />

          {/* Progress bar (from latest task) */}
          {latestTask && (
            <div className="mb-3">
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    latestTask.status === 'error' ? 'bg-red-500' :
                      latestTask.status === 'done' ? 'bg-emerald-500' :
                        'bg-amber-400',
                  )}
                  style={{ width: `${latestTask.progress}%` }}
                />
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-muted-foreground tabular-nums">
                  {latestTask.progress}%
                </span>
                {latestTask.startedAt && (
                  <span className="text-[10px] text-muted-foreground">
                    {fmtDate(latestTask.startedAt)}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Task log (terminal style — shows SSE stream when live, task log when historical) */}
          <div className={cn('min-h-0', logExpanded ? 'flex-[3]' : 'flex-1')}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                {hasRunning && sseLines.length > 0 && (
                  <Radio className="h-2.5 w-2.5 text-emerald-400 animate-pulse" />
                )}
                {isFr ? '任务日志' : 'Task Log'}
                {hasRunning && sseLines.length > 0 && (
                  <span className="text-emerald-400 font-normal">LIVE</span>
                )}
              </span>
              <div className="flex items-center gap-1">
                {(sseLines.length > 0 || latestTask?.log) && (
                  <button
                    onClick={() => copyText(sseLines.length > 0 ? sseLines.join('\n') : latestTask?.log || '')}
                    className="text-muted-foreground hover:text-foreground p-0.5"
                    title={isFr ? '复制日志' : 'Copy log'}
                  >
                    <Copy className="h-2.5 w-2.5" />
                  </button>
                )}
                <button
                  onClick={() => setLogExpanded((v) => !v)}
                  className="text-muted-foreground hover:text-foreground p-0.5"
                  title={logExpanded ? (isFr ? '缩小' : 'Minimize') : (isFr ? '放大' : 'Maximize')}
                >
                  {logExpanded ? <Minimize2 className="h-2.5 w-2.5" /> : <Maximize2 className="h-2.5 w-2.5" />}
                </button>
              </div>
            </div>
            <pre
              ref={logRef}
              className={cn(
                'text-[10px] text-muted-foreground bg-[#0a0d14] rounded-md p-2.5',
                'whitespace-pre-wrap font-mono leading-relaxed',
                'min-h-[60px] overflow-auto border border-border/50 resize-y',
                logExpanded ? 'max-h-[300px] h-[200px]' : 'max-h-[160px]',
              )}
            >
              {sseLines.length > 0
                ? sseLines.join('\n')
                : latestTask?.log || (isFr ? '等待执行...' : 'Waiting for execution...')}
            </pre>
          </div>

          {/* Error display */}
          {latestTask?.error && (
            <div className="mt-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-red-400 font-medium">Error</span>
                <button onClick={() => copyText(latestTask.error!)} className="text-muted-foreground hover:text-foreground">
                  <Copy className="h-2.5 w-2.5" />
                </button>
              </div>
              <pre className="text-[10px] text-red-400 bg-red-500/5 rounded-md p-2 whitespace-pre-wrap max-h-20 overflow-auto border border-red-500/20 font-mono">
                {latestTask.error}
              </pre>
            </div>
          )}

        </div>

        {/* Execute ↔ Results resize handle */}
        <div
          className="w-1 shrink-0 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors relative group"
          onMouseDown={createDragHandler(setExecuteWidth, 240, 800)}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>

        {/* ════════════════════════════════════════════════
            RIGHT: Data Inspector Panel
            ════════════════════════════════════════════════ */}
        <div className="flex-1 flex flex-col p-4 overflow-y-auto">
          {inspectorTarget ? (() => {
            const tStage = STAGES.find(s => s.key === inspectorTarget.stageKey)
            const tStep = tStage?.steps[inspectorTarget.stepIdx]
            if (!tStage || !tStep) return null
            const isIn = inspectorTarget.direction === 'in'
            const rawPath = isIn ? (isFr ? tStep.inputZh : tStep.input) : (isFr ? tStep.outputZh : tStep.output)
            const bookDirName = (selectedBook?.title || '').toLowerCase().replace(/[^a-z0-9_]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '') || `book_${selectedBook?.id}`
            const pdfName = (selectedBook as any)?.pdfMedia?.filename || (selectedBook as any)?.pdfFilename || `${bookDirName}.pdf`
            const rawPathStr = Array.isArray(rawPath) ? rawPath.join('\n') : rawPath
            const path = rawPathStr
              .replace(/\{filename\}/g, pdfName.replace(/\.pdf$/i, ''))
              .replace(/\{category\}/g, selectedBook?.category || 'textbook')
              .replace(/\{book\}/g, bookDirName)
            const stepLabel = isFr ? tStep.labelFr : tStep.label

            return (
              <>
                {/* Inspector header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded',
                      isIn ? 'text-muted-foreground bg-muted' : 'text-emerald-400 bg-emerald-500/10',
                    )}>
                      {isIn ? 'INPUT' : 'OUTPUT'}
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {isFr ? tStage.labelFr : tStage.label} › {stepLabel}
                    </span>
                  </div>
                  <button
                    onClick={() => setInspectorTarget(null)}
                    className="text-muted-foreground hover:text-foreground text-xs"
                  >✕</button>
                </div>

                {/* Path */}
                <div className="mb-4">
                  <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-medium block mb-1">
                    {isFr ? '路径' : 'Path'}
                  </span>
                  <div className="flex items-start gap-2">
                    <div className="text-[11px] font-mono text-foreground bg-muted/50 px-2 py-1 rounded border border-border/50 flex-1 flex flex-col gap-0.5">
                      {path.split('\n').map((p, i) => (
                        <span key={i}>{p}</span>
                      ))}
                    </div>
                    <button onClick={() => copyText(path)} className="text-muted-foreground hover:text-foreground shrink-0 mt-1">
                      <Copy className="h-3 w-3" />
                    </button>
                  </div>
                </div>

                {/* Live data — always JSON */}
                <div className="flex-1 min-h-0">
                  <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-medium block mb-1">
                    {isFr ? '实际数据' : 'Live Data'}
                  </span>
                  {inspectLoading ? (
                    <div className="flex items-center justify-center py-10">
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : inspectData ? (
                    <pre className="text-[10px] text-muted-foreground bg-[#0a0d14] rounded-md p-3
                                    whitespace-pre-wrap font-mono leading-relaxed
                                    overflow-auto border border-border/50 max-h-[320px]">
                      {JSON.stringify(inspectData, null, 2)}
                    </pre>
                  ) : (
                    <div className="text-[10px] text-muted-foreground/40 py-4 text-center">
                      {isFr ? '无数据' : 'No data available'}
                    </div>
                  )}
                </div>
              </>
            )
          })() : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
              <FileSearch className="h-8 w-8 mb-3 opacity-30" />
              <span className="text-xs font-medium">
                {isFr ? '数据检查器' : 'Data Inspector'}
              </span>
              <span className="text-[10px] text-muted-foreground/60 mt-1 text-center max-w-[200px]">
                {isFr
                  ? '展开步骤并点击 IN 或 OUT 查看实际数据'
                  : 'Expand a step and click IN or OUT to inspect live data'}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// BatchPipelineView — batch pipeline execution for directories
// ============================================================

type BatchBookStatus = 'idle' | 'queued' | 'running' | 'done' | 'error' | 'skipped'

// ── Module-level batch state cache (survives component unmount/remount) ──
interface BatchCache {
  running: boolean
  log: string[]
  statusMap: Map<number, BatchBookStatus>
  progress: { done: number; total: number }
  currentBookId: number | null
  filterKey: string
  /** Writable refs that the async loop uses to push updates */
  setters: {
    setBatchRunning: (v: boolean) => void
    setBatchStatus: (fn: (prev: Map<number, BatchBookStatus>) => Map<number, BatchBookStatus>) => void
    setBatchLog: (fn: (prev: string[]) => string[]) => void
    setBatchProgress: (v: { done: number; total: number }) => void
    setCurrentBookId: (v: number | null) => void
  } | null
}

let _batchCache: BatchCache | null = null

interface BatchPipelineViewProps {
  books: BookBase[]
  filter: string
  isFr: boolean
  onBooksRefresh?: () => void
}

function BatchPipelineView({ books, filter, isFr, onBooksRefresh }: BatchPipelineViewProps) {
  const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

  // ── State (initialise from cache if available) ──
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [batchRunning, setBatchRunning] = useState(() => _batchCache?.running ?? false)
  const [batchStatus, setBatchStatus] = useState<Map<number, BatchBookStatus>>(
    () => _batchCache?.statusMap ?? new Map(),
  )
  const [batchLog, setBatchLog] = useState<string[]>(() => _batchCache?.log ?? [])
  const [currentBookId, setCurrentBookId] = useState<number | null>(
    () => _batchCache?.currentBookId ?? null,
  )
  const [batchProgress, setBatchProgress] = useState(
    () => _batchCache?.progress ?? { done: 0, total: 0 },
  )
  const [skipDone, setSkipDone] = useState(true)
  const cancelRef = useRef(false)
  const logRef = useRef<HTMLPreElement>(null)

  // ── Re-attach setters so the running async loop can push to THIS component instance ──
  useEffect(() => {
    if (_batchCache) {
      _batchCache.setters = {
        setBatchRunning,
        setBatchStatus,
        setBatchLog,
        setBatchProgress,
        setCurrentBookId,
      }
    }
    return () => {
      // Detach setters on unmount (loop will write to cache only)
      if (_batchCache) _batchCache.setters = null
    }
  }, [])

  // Auto-select pending books on mount; reconnect to active engine pipelines
  const reconnectSSERef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (books.length === 0) return

    // Cleanup on unmount
    return () => {
      if (reconnectSSERef.current) {
        reconnectSSERef.current.close()
        reconnectSSERef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (books.length === 0) return

    const bookIds = books.map(b => b.id)
    const checkRunning = async () => {
      try {
        const res = await authFetch(
          `/api/ingest-tasks?where[status][in]=running,queued&where[book][in]=${bookIds.join(',')}&limit=20&sort=-createdAt&depth=1`,
        )
        if (!res.ok) return

        const data = await res.json()
        const runningTasks = (data.docs || []).filter(
          (t: any) => t.status === 'running' || t.status === 'queued',
        )

        if (runningTasks.length > 0) {
          const runningBookIds = runningTasks
            .map((t: any) => (typeof t.book === 'object' ? t.book?.id : t.book))
            .filter(Boolean) as number[]

          setBatchRunning(true)
          const statusMap = new Map<number, BatchBookStatus>()
          for (const bid of runningBookIds) {
            statusMap.set(bid, 'running')
          }
          setBatchStatus(statusMap)
          setSelected(new Set(runningBookIds))
          setBatchProgress({ done: 0, total: runningBookIds.length })
          pushLog(() => [`🔄 Reconnected to ${runningBookIds.length} active pipeline(s)...`])

          // Try to reconnect SSE for the first running book
          const activeBookId = runningBookIds[0]
          if (activeBookId) {
            setCurrentBookId(activeBookId)

            // First, check if engine actually has an active stream (avoid loop)
            try {
              const probe = await fetch(`${ENGINE_URL}/engine/ingest/stream/${activeBookId}`, {
                headers: { 'Accept': 'text/event-stream' },
                signal: AbortSignal.timeout(3000),
              })
              // Read a bit to see if it's a valid stream or an error
              const reader = probe.body?.getReader()
              if (reader) {
                const { value } = await reader.read()
                const text = new TextDecoder().decode(value)
                reader.releaseLock()
                probe.body?.cancel()

                if (text.includes('No active pipeline')) {
                  // Pipeline already finished — clean up stale tasks in Payload
                  pushLog(prev => [...prev, `ℹ️ Pipeline already finished`])

                  // Mark stale running/queued tasks as done
                  for (const bid of runningBookIds) {
                    try {
                      const staleRes = await authFetch(
                        `/api/ingest-tasks?where[book][equals]=${bid}&where[status][in]=running,queued&limit=10`,
                      )
                      if (staleRes.ok) {
                        const staleData = await staleRes.json()
                        for (const doc of staleData.docs || []) {
                          await authFetch(`/api/ingest-tasks/${doc.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: 'done', progress: 100 }),
                          }).catch(() => {})
                        }
                      }
                    } catch { /* ignore */ }
                  }

                  // Update batch status to done for all reconnected books
                  setBatchStatus(prev => {
                    const next = new Map(prev)
                    for (const bid of runningBookIds) next.set(bid, 'done')
                    return next
                  })
                  setBatchRunning(false)
                  setCurrentBookId(null)
                  setTimeout(() => onBooksRefresh?.(), 1000)
                  return
                }
              }
            } catch {
              // Probe failed — pipeline not running, clean up stale tasks
              pushLog(prev => [...prev, `ℹ️ Could not reconnect to stream`])

              for (const bid of runningBookIds) {
                try {
                  const staleRes = await authFetch(
                    `/api/ingest-tasks?where[book][equals]=${bid}&where[status][in]=running,queued&limit=10`,
                  )
                  if (staleRes.ok) {
                    const staleData = await staleRes.json()
                    for (const doc of staleData.docs || []) {
                      await authFetch(`/api/ingest-tasks/${doc.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: 'done', progress: 100 }),
                      }).catch(() => {})
                    }
                  }
                } catch { /* ignore */ }
              }

              setBatchStatus(prev => {
                const next = new Map(prev)
                for (const bid of runningBookIds) next.set(bid, 'done')
                return next
              })
              setBatchRunning(false)
              setCurrentBookId(null)
              setTimeout(() => onBooksRefresh?.(), 1000)
              return
            }

            // Stream is active, connect properly via EventSource
            const url = `${ENGINE_URL}/engine/ingest/stream/${activeBookId}`
            const es = new EventSource(url)
            reconnectSSERef.current = es

            let noDataDetected = false

            es.onmessage = (ev) => {
              const msg = ev.data as string
              if (msg && msg.trim()) {
                // Detect "No active pipeline" message and stop
                if (msg.includes('No active pipeline')) {
                  noDataDetected = true
                  es.close()
                  reconnectSSERef.current = null
                  pushLog(prev => [...prev, `ℹ️ Pipeline finished`])
                  setBatchRunning(false)
                  setCurrentBookId(null)
                  setTimeout(() => onBooksRefresh?.(), 1000)
                  return
                }
                pushLog(prev => {
                  const next = [...prev, `  ${msg}`]
                  return next.length > 800 ? next.slice(-800) : next
                })
              }
            }

            es.addEventListener('done', () => {
              es.close()
              reconnectSSERef.current = null
              pushStatus(prev => new Map(prev).set(activeBookId, 'done'))
              pushLog(prev => [...prev, `✅ Pipeline completed`])
              setBatchRunning(false)
              setCurrentBookId(null)
              setTimeout(() => onBooksRefresh?.(), 2000)
            })

            es.addEventListener('error', () => {
              // Always close to prevent auto-reconnect loop
              es.close()
              reconnectSSERef.current = null
              if (!noDataDetected) {
                pushLog(prev => [...prev, `ℹ️ Stream ended`])
                setBatchRunning(false)
                setCurrentBookId(null)
                setTimeout(() => onBooksRefresh?.(), 2000)
              }
            })
          }
          return
        }
      } catch {
        // Silently ignore
      }

      // No running tasks — auto-select pending books
      if (!batchRunning && selected.size === 0) {
        const pendingIds = books
          .filter(b => !b.pipeline || b.pipeline.ingest !== 'done')
          .map(b => b.id)
        setSelected(new Set(pendingIds.length > 0 ? pendingIds : books.map(b => b.id)))
      }
    }

    checkRunning()
  }, [books.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [batchLog])

  // ── Derived label for the current filter ──
  const filterLabel = useMemo(() => {
    if (filter === 'all') return isFr ? '全部' : 'All'
    if (filter.includes('::')) {
      const [cat, sub] = filter.split('::')
      return sub || cat
    }
    return filter.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }, [filter, isFr])

  // ── Selection helpers ──
  const toggleSelect = useCallback((id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  const selectAll = useCallback(() => {
    setSelected(new Set(books.map(b => b.id)))
  }, [books])

  const selectNone = useCallback(() => {
    setSelected(new Set())
  }, [])

  const selectPending = useCallback(() => {
    setSelected(new Set(
      books.filter(b => !b.pipeline || b.pipeline.ingest !== 'done').map(b => b.id)
    ))
  }, [books])

  // ── Helper: update both React state AND cache ──
  const pushLog = useCallback((fn: (prev: string[]) => string[]) => {
    if (_batchCache) {
      _batchCache.log = fn(_batchCache.log)
      _batchCache.setters?.setBatchLog(() => [..._batchCache!.log])
    } else {
      setBatchLog(fn)
    }
  }, [])

  const pushStatus = useCallback((fn: (prev: Map<number, BatchBookStatus>) => Map<number, BatchBookStatus>) => {
    if (_batchCache) {
      _batchCache.statusMap = fn(_batchCache.statusMap)
      _batchCache.setters?.setBatchStatus(() => new Map(_batchCache!.statusMap))
    } else {
      setBatchStatus(fn)
    }
  }, [])

  const pushProgress = useCallback((v: { done: number; total: number }) => {
    if (_batchCache) {
      _batchCache.progress = v
      _batchCache.setters?.setBatchProgress(v)
    } else {
      setBatchProgress(v)
    }
  }, [])

  const pushCurrentBook = useCallback((v: number | null) => {
    if (_batchCache) {
      _batchCache.currentBookId = v
      _batchCache.setters?.setCurrentBookId(v)
    } else {
      setCurrentBookId(v)
    }
  }, [])

  const pushRunning = useCallback((v: boolean) => {
    if (_batchCache) {
      _batchCache.running = v
      _batchCache.setters?.setBatchRunning(v)
    } else {
      setBatchRunning(v)
    }
  }, [])

  // ── Batch run — sequential execution ──
  const runBatch = useCallback(async () => {
    if (selected.size === 0) return
    cancelRef.current = false

    // Initialise module-level cache
    _batchCache = {
      running: true,
      log: [],
      statusMap: new Map(),
      progress: { done: 0, total: 0 },
      currentBookId: null,
      filterKey: filter,
      setters: {
        setBatchRunning,
        setBatchStatus,
        setBatchLog,
        setBatchProgress,
        setCurrentBookId,
      },
    }

    pushRunning(true)
    pushLog(() => [])

    const booksToRun = books.filter(b => selected.has(b.id))
    const initialStatus = new Map<number, BatchBookStatus>()

    // Mark selected books as queued, skip already-done if flag is set
    for (const b of booksToRun) {
      if (skipDone && b.pipeline?.parse === 'done' && b.pipeline?.ingest === 'done') {
        initialStatus.set(b.id, 'skipped')
      } else {
        initialStatus.set(b.id, 'queued')
      }
    }
    pushStatus(() => initialStatus)

    const toProcess = booksToRun.filter(b => initialStatus.get(b.id) === 'queued')
    const skippedCount = booksToRun.length - toProcess.length
    pushProgress({ done: skippedCount, total: booksToRun.length })

    if (skippedCount > 0) {
      pushLog(prev => [...prev,
      `⏩ ${isFr ? `跳过 ${skippedCount} 本已完成的书` : `Skipped ${skippedCount} already-completed book(s)`}`
      ])
    }

    let completed = skippedCount
    for (const book of toProcess) {
      if (cancelRef.current) {
        pushStatus(prev => {
          const next = new Map(prev)
          for (const [id, st] of next) {
            if (st === 'queued') next.set(id, 'idle')
          }
          return next
        })
        pushLog(prev => [...prev, `⛔ ${isFr ? '批量处理已取消' : 'Batch cancelled by user'}`])
        break
      }

      pushCurrentBook(book.id)
      pushStatus(prev => new Map(prev).set(book.id, 'running'))
      pushLog(prev => [...prev,
      `\n━━━ [${completed + 1}/${booksToRun.length}] ${book.title} ━━━`
      ])

      try {
        // 1. Fetch book with pdfMedia populated
        const bookRes = await authFetch(`/api/books/${book.id}?depth=1`)
        if (!bookRes.ok) throw new Error(`Failed to fetch book: ${bookRes.status}`)
        const bookDoc = await bookRes.json()
        // Resolve PDF filename: pdfMedia (uploaded) → metadata.pdfFilename (URL-imported)
        const pdfFilename = (typeof bookDoc.pdfMedia === 'object' ? bookDoc.pdfMedia?.filename : undefined)
          || bookDoc.metadata?.pdfFilename
          || undefined

        // 2. Create IngestTask
        const taskRes = await authFetch('/api/ingest-tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            taskType: 'ingest',
            book: book.id,
            status: 'queued',
            progress: 0,
          }),
        })
        const taskDoc = taskRes.ok ? await taskRes.json() : null
        const taskId = taskDoc?.doc?.id ?? null

        pushLog(prev => [...prev, `📋 Task created: #${taskId}`])

        // 3. POST to Engine
        const engineRes = await fetch(`${ENGINE_URL}/engine/ingest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            book_id: book.id,
            pdf_filename: pdfFilename,
            title: book.title,
            category: book.category,
            task_id: taskId,
            force_parse: false,
          }),
        })

        if (!engineRes.ok) {
          throw new Error(`Engine returned ${engineRes.status}`)
        }

        pushLog(prev => [...prev, `🚀 ${isFr ? '流水线已启动，等待完成...' : 'Pipeline started, waiting for completion...'}`])

        // 4. Wait for engine thread to register its log queue, then connect SSE
        await new Promise<void>((r) => setTimeout(r, 1500))

        // Track whether the pipeline reported errors via SSE
        let sseHadError = false

        await new Promise<void>((resolve) => {
          const url = `${ENGINE_URL}/engine/ingest/stream/${book.id}`
          let resolved = false
          let retryCount = 0
          const maxRetries = 2

          const connectSSE = () => {
            const es = new EventSource(url)

            const timeout = setTimeout(() => {
              if (!resolved) {
                resolved = true
                es.close()
                pushLog(prev => [...prev, `⏱️ ${isFr ? '超时，继续下一本' : 'Timeout, moving to next book'}`])
                resolve()
              }
            }, 30 * 60 * 1000) // 30 minutes max per book

            es.onmessage = (ev) => {
              const msg = ev.data as string
              // Show all SSE messages in real-time
              if (msg && msg.trim()) {
                // Detect real error messages from engine pipeline
                // Match log-level errors like "| ERROR |" and specific failure patterns
                // but NOT benign strings like "0 errors" or "errors so far)"
                if (
                  /\|\s*ERROR\s*\|/.test(msg)
                  || msg.includes('No PDF found')
                  || msg.includes('Pipeline failed')
                  || msg.includes('Traceback')
                ) {
                  sseHadError = true
                }
                pushLog(prev => {
                  const next = [...prev, `  ${msg}`]
                  return next.length > 800 ? next.slice(-800) : next
                })
              }
            }

            es.addEventListener('done', () => {
              if (!resolved) {
                resolved = true
                clearTimeout(timeout)
                es.close()
                resolve()
              }
            })

            es.addEventListener('error', () => {
              if (es.readyState === EventSource.CLOSED && !resolved) {
                es.close()
                clearTimeout(timeout)
                // Retry if engine queue wasn't ready yet
                if (retryCount < maxRetries) {
                  retryCount++
                  pushLog(prev => [...prev, `  ⟳ ${isFr ? '重连 SSE...' : 'Reconnecting SSE...'}`])
                  setTimeout(connectSSE, 2000)
                } else {
                  resolved = true
                  resolve()
                }
              }
            })
          }

          connectSSE()
        })

        // Determine outcome based on SSE error detection
        if (sseHadError) {
          pushStatus(prev => new Map(prev).set(book.id, 'error'))
          pushLog(prev => [...prev, `❌ ${book.title} ${isFr ? '失败（引擎报错）' : 'failed (engine error)'}`])
        } else {
          pushStatus(prev => new Map(prev).set(book.id, 'done'))
          pushLog(prev => [...prev, `✅ ${book.title} ${isFr ? '完成' : 'completed'}`])
        }
        completed++

      } catch (e) {
        pushStatus(prev => new Map(prev).set(book.id, 'error'))
        pushLog(prev => [...prev, `❌ ${book.title}: ${e instanceof Error ? e.message : String(e)}`])
        completed++
      }

      pushProgress({ done: completed, total: booksToRun.length })
    }

    pushCurrentBook(null)
    pushRunning(false)
    pushLog(prev => [...prev, `\n🏁 ${isFr ? '批量处理完成' : 'Batch processing finished'}`])
    // Refresh book list to pick up pipeline status changes
    setTimeout(() => onBooksRefresh?.(), 2000)
  }, [selected, books, skipDone, isFr, onBooksRefresh, filter])

  const cancelBatch = useCallback(() => {
    cancelRef.current = true
  }, [])

  // ── Pipeline status badge ──
  const StatusBadge = ({ stage }: { stage?: PipelineStage }) => {
    const s = stage || 'pending'
    const cfg = STAGE_STATUS[s]
    const Icon = cfg.icon
    return (
      <span className={cn(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium',
        cfg.bg, cfg.color,
      )}>
        <Icon className="h-2.5 w-2.5" />
        {isFr ? cfg.labelFr : cfg.label}
      </span>
    )
  }

  const BatchStatusBadge = ({ status }: { status?: BatchBookStatus }) => {
    if (!status || status === 'idle') return null
    const cfgMap: Record<BatchBookStatus, { icon: React.ElementType; color: string; bg: string; label: string; labelFr: string }> = {
      idle: { icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted/50', label: '', labelFr: '' },
      queued: { icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted/50', label: 'Queued', labelFr: '排队中' },
      running: { icon: Loader2, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Running', labelFr: '运行中' },
      done: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Done', labelFr: '完成' },
      error: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Error', labelFr: '错误' },
      skipped: { icon: SkipForward, color: 'text-muted-foreground', bg: 'bg-muted/50', label: 'Skipped', labelFr: '跳过' },
    }
    const c = cfgMap[status]
    const Icon = c.icon
    return (
      <span className={cn(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium',
        c.bg, c.color,
      )}>
        <Icon className={cn('h-2.5 w-2.5', status === 'running' && 'animate-spin')} />
        {isFr ? c.labelFr : c.label}
      </span>
    )
  }

  // ── Summary stats ──
  const stats = useMemo(() => {
    let pending = 0, done = 0, error = 0
    for (const b of books) {
      if (b.pipeline?.ingest === 'done') done++
      else if (b.pipeline?.ingest === 'error' || b.pipeline?.parse === 'error') error++
      else pending++
    }
    return { pending, done, error, total: books.length }
  }, [books])

  // ── Render ──
  return (
    <div className="space-y-4">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Layers className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              {isFr ? '批量 Pipeline' : 'Batch Pipeline'}
            </h3>
            <p className="text-[10px] text-muted-foreground">
              {filterLabel} · {books.length} {isFr ? '本' : 'book(s)'}
            </p>
          </div>
        </div>

        {/* Summary badges */}
        <div className="flex items-center gap-2">
          {stats.done > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-500/10 text-[10px] font-medium text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              {stats.done} {isFr ? '已完成' : 'done'}
            </span>
          )}
          {stats.pending > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-muted text-[10px] font-medium text-muted-foreground">
              <Clock className="h-3 w-3" />
              {stats.pending} {isFr ? '待处理' : 'pending'}
            </span>
          )}
          {stats.error > 0 && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-red-500/10 text-[10px] font-medium text-red-400">
              <AlertTriangle className="h-3 w-3" />
              {stats.error} {isFr ? '错误' : 'error'}
            </span>
          )}
        </div>
      </div>

      {/* ── Controls bar ── */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5">
          <button
            onClick={selectAll}
            disabled={batchRunning}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-border
                       text-[10px] text-muted-foreground hover:text-foreground hover:bg-secondary/50
                       disabled:opacity-40 transition-colors"
          >
            <CheckSquare className="h-3 w-3" />
            {isFr ? '全选' : 'All'}
          </button>
          <button
            onClick={selectPending}
            disabled={batchRunning}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-border
                       text-[10px] text-muted-foreground hover:text-foreground hover:bg-secondary/50
                       disabled:opacity-40 transition-colors"
          >
            <Clock className="h-3 w-3" />
            {isFr ? '待处理' : 'Pending'}
          </button>
          <button
            onClick={selectNone}
            disabled={batchRunning}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-border
                       text-[10px] text-muted-foreground hover:text-foreground hover:bg-secondary/50
                       disabled:opacity-40 transition-colors"
          >
            <SquareDashedBottom className="h-3 w-3" />
            {isFr ? '取消全选' : 'None'}
          </button>
          <div className="h-4 w-px bg-border mx-1" />
          <label className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={skipDone}
              onChange={(e) => setSkipDone(e.target.checked)}
              disabled={batchRunning}
              className="rounded border-border"
            />
            {isFr ? '跳过已完成' : 'Skip completed'}
          </label>
        </div>

        <div className="flex items-center gap-2">
          {batchRunning ? (
            <button
              onClick={cancelBatch}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md
                         bg-red-600 text-white text-xs font-medium
                         hover:bg-red-700 transition-colors"
            >
              <Square className="h-3.5 w-3.5" />
              {isFr ? '取消批量' : 'Cancel Batch'}
            </button>
          ) : (
            <button
              onClick={runBatch}
              disabled={selected.size === 0}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md
                         bg-primary text-primary-foreground text-xs font-medium
                         hover:bg-primary/90 disabled:opacity-40 transition-colors"
            >
              <Play className="h-3.5 w-3.5" />
              {isFr
                ? `批量运行 (${selected.size})`
                : `Run Batch (${selected.size})`}
            </button>
          )}
        </div>
      </div>

      {/* ── Batch progress bar ── */}
      {batchRunning && (
        <div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${batchProgress.total > 0 ? (batchProgress.done / batchProgress.total) * 100 : 0}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {batchProgress.done} / {batchProgress.total}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {isFr ? '处理中...' : 'Processing...'}
            </span>
          </div>
        </div>
      )}

      {/* ── Book table + log ── */}
      <div className="flex gap-3" style={{ height: 'calc(100vh - 380px)', minHeight: '300px' }}>

        {/* LEFT: Book selection table */}
        <div className="flex-1 overflow-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-secondary/80 backdrop-blur z-10">
              <tr>
                <th className="w-8 px-2 py-2">
                  <input
                    type="checkbox"
                    checked={selected.size === books.length && books.length > 0}
                    onChange={() => selected.size === books.length ? selectNone() : selectAll()}
                    disabled={batchRunning}
                    className="rounded border-border"
                  />
                </th>
                <th className="text-left px-2 py-2 font-medium text-muted-foreground">
                  {isFr ? '书名' : 'Title'}
                </th>
                <th className="text-center px-2 py-2 font-medium text-muted-foreground w-20">
                  Parse
                </th>
                <th className="text-center px-2 py-2 font-medium text-muted-foreground w-20">
                  Ingest
                </th>
                {batchRunning && (
                  <th className="text-center px-2 py-2 font-medium text-muted-foreground w-24">
                    {isFr ? '批量状态' : 'Batch'}
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[...books].sort((a, b) => {
                // Natural sort: extract year + quarter (e.g. "Q3 2024" → 2024.3)
                const re = /Q(\d)\s*(\d{4})/i
                const ma = re.exec(a.title)
                const mb = re.exec(b.title)
                if (ma && mb) {
                  const va = Number(ma[2]) * 10 + Number(ma[1])
                  const vb = Number(mb[2]) * 10 + Number(mb[1])
                  return vb - va
                }
                return b.title.localeCompare(a.title)
              }).map((book) => {
                const isRunning = currentBookId === book.id
                const bs = batchStatus.get(book.id)
                return (
                  <tr
                    key={book.id}
                    className={cn(
                      'transition-colors',
                      isRunning ? 'bg-primary/5' : 'hover:bg-secondary/30',
                      bs === 'done' && 'bg-emerald-500/3',
                      bs === 'error' && 'bg-red-500/3',
                    )}
                  >
                    <td className="px-2 py-1.5 text-center">
                      <input
                        type="checkbox"
                        checked={selected.has(book.id)}
                        onChange={() => toggleSelect(book.id)}
                        disabled={batchRunning}
                        className="rounded border-border"
                      />
                    </td>
                    <td className="px-2 py-1.5">
                      <div className="flex items-center gap-1.5">
                        <BookOpen className="h-3 w-3 text-muted-foreground/50 shrink-0" />
                        <span className={cn(
                          'text-[11px] truncate max-w-[200px]',
                          isRunning ? 'font-semibold text-primary' : 'text-foreground',
                        )}>
                          {book.title}
                        </span>
                        {isRunning && <Loader2 className="h-3 w-3 text-primary animate-spin shrink-0" />}
                      </div>
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <StatusBadge stage={book.pipeline?.parse} />
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      <StatusBadge stage={book.pipeline?.ingest} />
                    </td>
                    {batchRunning && (
                      <td className="px-2 py-1.5 text-center">
                        <BatchStatusBadge status={bs} />
                      </td>
                    )}
                  </tr>
                )
              })}
              {books.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-8 text-muted-foreground text-xs">
                    {isFr ? '此目录下没有书籍' : 'No books in this directory'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* RIGHT: Batch log */}
        {batchLog.length > 0 && (
          <div className="w-[340px] shrink-0 flex flex-col rounded-lg border border-border overflow-hidden">
            <div className="flex items-center justify-between px-3 py-1.5 bg-secondary/50 border-b border-border">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                {batchRunning && <Radio className="h-2.5 w-2.5 text-emerald-400 animate-pulse" />}
                {isFr ? '批量日志' : 'Batch Log'}
                {batchRunning && <span className="text-emerald-400 font-normal">LIVE</span>}
              </span>
              <button
                onClick={() => navigator.clipboard.writeText(batchLog.join('\n'))}
                className="text-muted-foreground hover:text-foreground p-0.5"
                title={isFr ? '复制日志' : 'Copy log'}
              >
                <Copy className="h-2.5 w-2.5" />
              </button>
            </div>
            <pre
              ref={logRef}
              className="flex-1 text-[10px] text-muted-foreground bg-[#0a0d14] p-2.5
                         whitespace-pre-wrap font-mono leading-relaxed overflow-auto"
            >
              {batchLog.join('\n')}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

