'use client'

import { useState, useEffect, useCallback, use } from 'react'
import Link from 'next/link'
import {
  ArrowLeft, Book, Layers, FileText, ChevronRight, ChevronDown,
  Loader2, Hash, MapPin, Type, Table2,
} from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'
import { cn } from '@/features/shared/utils'

interface BookInfo {
  id: number
  title: string
  authors: string
  category: string
  status: string
  chunkCount: number
  pipeline: {
    chunked: string
    stored: string
    vector: string
    fts: string
    toc: string
  }
}

interface Chapter {
  id: number
  chapterKey: string
  title: string
  contentType: string
}

interface Chunk {
  id: number
  chunkId: string
  text: string
  contentType: string
  pageNumber: number
  readingOrder: number
  vectorized: boolean
  chapter?: { id: number; title: string } | null
}

const CONTENT_TYPE_ICON: Record<string, typeof Type> = {
  text: Type,
  table: Table2,
  image: MapPin,
  equation: Hash,
  code: FileText,
}

function PipelineBadge({ stage, status }: { stage: string; status: string }) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
      status === 'done' ? 'bg-emerald-500/10 text-emerald-400' :
      status === 'error' ? 'bg-red-500/10 text-red-400' :
      'bg-muted text-muted-foreground'
    )}>
      {stage}: {status}
    </span>
  )
}

export default function Page({ params }: { params: Promise<{ bookId: string }> }) {
  const resolvedParams = use(params)
  const bookId = resolvedParams.bookId
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  const [book, setBook] = useState<BookInfo | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [chunks, setChunks] = useState<Chunk[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set())
  const [selectedChunk, setSelectedChunk] = useState<Chunk | null>(null)
  const [chunkPage, setChunkPage] = useState(1)
  const [totalChunks, setTotalChunks] = useState(0)
  const CHUNKS_PER_PAGE = 50

  const fetchBook = useCallback(async () => {
    setLoading(true)
    try {
      const [bookRes, chapRes, chunkRes] = await Promise.all([
        fetch(`/api/books/${bookId}`),
        fetch(`/api/chapters?where[book][equals]=${bookId}&limit=200&sort=chapterKey`),
        fetch(`/api/chunks?where[book][equals]=${bookId}&limit=${CHUNKS_PER_PAGE}&page=${chunkPage}&sort=readingOrder`),
      ])

      if (bookRes.ok) {
        const b = await bookRes.json()
        setBook({
          id: b.id, title: b.title ?? '', authors: b.authors ?? '',
          category: b.category ?? '', status: b.status ?? 'pending',
          chunkCount: b.chunkCount ?? 0,
          pipeline: {
            chunked: b.pipeline?.chunked ?? 'pending',
            stored: b.pipeline?.stored ?? 'pending',
            vector: b.pipeline?.vector ?? 'pending',
            fts: b.pipeline?.fts ?? 'pending',
            toc: b.pipeline?.toc ?? 'pending',
          },
        })
      }

      if (chapRes.ok) {
        const data = await chapRes.json()
        setChapters((data.docs ?? []).map((c: any) => ({
          id: c.id, chapterKey: c.chapterKey ?? '', title: c.title ?? '',
          contentType: c.contentType ?? 'text',
        })))
      }

      if (chunkRes.ok) {
        const data = await chunkRes.json()
        setTotalChunks(data.totalDocs ?? 0)
        setChunks((data.docs ?? []).map((c: any) => ({
          id: c.id, chunkId: c.chunkId ?? '', text: c.text ?? '',
          contentType: c.contentType ?? 'text', pageNumber: c.pageNumber ?? 0,
          readingOrder: c.readingOrder ?? 0, vectorized: c.vectorized ?? false,
          chapter: c.chapter ? { id: c.chapter.id ?? c.chapter, title: c.chapter.title ?? '' } : null,
        })))
      }
    } catch {}
    setLoading(false)
  }, [bookId, chunkPage])

  useEffect(() => { fetchBook() }, [fetchBook])

  const toggleChapter = (key: string) => {
    setExpandedChapters(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const chapterChunks = (chapterId: number) =>
    chunks.filter(c => c.chapter?.id === chapterId)

  const totalPages = Math.ceil(totalChunks / CHUNKS_PER_PAGE)

  if (loading && !book) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!book) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Book not found</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-border bg-card/30 px-6 py-4">
        <div className="flex items-center gap-3 mb-3">
          <Link href="/library" className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <Book className="h-5 w-5 text-primary" />
          <h1 className="text-base font-semibold text-foreground">{book.title}</h1>
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {book.authors && <span>{book.authors}</span>}
          <span className="text-muted-foreground/50">·</span>
          <span>{book.chunkCount} chunks</span>
          <span className="text-muted-foreground/50">·</span>
          <span>{chapters.length} {isZh ? '章节' : 'chapters'}</span>
        </div>

        <div className="flex items-center gap-2 mt-2">
          <PipelineBadge stage="Chunk" status={book.pipeline.chunked} />
          <PipelineBadge stage="Store" status={book.pipeline.stored} />
          <PipelineBadge stage="Vector" status={book.pipeline.vector} />
          <PipelineBadge stage="FTS" status={book.pipeline.fts} />
          <PipelineBadge stage="TOC" status={book.pipeline.toc} />
        </div>
      </div>

      {/* Body: 2-panel layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left: TOC / Chapter Tree */}
        <aside className="w-80 shrink-0 border-r border-border bg-card/50 flex flex-col">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
            <Layers className="h-4 w-4 text-blue-400" />
            <span className="text-xs font-semibold text-foreground">
              {isZh ? '目录结构' : 'Table of Contents'}
            </span>
          </div>

          <nav className="flex-1 overflow-y-auto py-2 px-2">
            {chapters.map((ch) => {
              const isExpanded = expandedChapters.has(ch.chapterKey)
              const chChunks = chapterChunks(ch.id)
              return (
                <div key={ch.id} className="mb-0.5">
                  <button
                    type="button"
                    onClick={() => toggleChapter(ch.chapterKey)}
                    className="flex items-center gap-2 w-full rounded-md px-2 py-1.5 text-left text-xs hover:bg-secondary transition-colors"
                  >
                    {isExpanded
                      ? <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
                      : <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                    }
                    <span className="font-mono text-[10px] text-muted-foreground w-10 shrink-0">{ch.chapterKey}</span>
                    <span className="font-medium text-foreground truncate">{ch.title}</span>
                    {chChunks.length > 0 && (
                      <span className="ml-auto text-[10px] text-muted-foreground shrink-0">{chChunks.length}</span>
                    )}
                  </button>

                  {isExpanded && chChunks.length > 0 && (
                    <div className="ml-5 pl-3 border-l border-border/50 mt-0.5 mb-1">
                      {chChunks.map((chunk) => {
                        const Icon = CONTENT_TYPE_ICON[chunk.contentType] ?? FileText
                        return (
                          <button
                            key={chunk.id}
                            type="button"
                            onClick={() => setSelectedChunk(chunk)}
                            className={cn(
                              'flex items-center gap-2 w-full rounded-md px-2 py-1 text-left text-[11px] transition-colors',
                              selectedChunk?.id === chunk.id
                                ? 'bg-primary/10 text-primary'
                                : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
                            )}
                          >
                            <Icon className="h-3 w-3 shrink-0" />
                            <span className="truncate">p.{chunk.pageNumber} — {chunk.text.slice(0, 50)}…</span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}

            {chapters.length === 0 && (
              <p className="text-[11px] text-muted-foreground text-center py-4">
                {isZh ? '暂无章节数据' : 'No chapters yet'}
              </p>
            )}
          </nav>
        </aside>

        {/* Right: Chunk Detail / Stats */}
        <div className="flex-1 min-w-0 flex flex-col">
          {selectedChunk ? (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground">Chunk: {selectedChunk.chunkId}</h3>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'text-[10px] rounded-full px-2 py-0.5 font-medium',
                    selectedChunk.vectorized ? 'bg-emerald-500/10 text-emerald-400' : 'bg-muted text-muted-foreground'
                  )}>
                    {selectedChunk.vectorized ? (isZh ? '已向量化' : 'Vectorized') : (isZh ? '未向量化' : 'Not vectorized')}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-3 mb-4 text-xs">
                <div className="rounded-lg border border-border bg-muted/30 p-3">
                  <span className="text-muted-foreground">{isZh ? '页码' : 'Page'}</span>
                  <p className="font-medium text-foreground">{selectedChunk.pageNumber}</p>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-3">
                  <span className="text-muted-foreground">{isZh ? '类型' : 'Type'}</span>
                  <p className="font-medium text-foreground capitalize">{selectedChunk.contentType}</p>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-3">
                  <span className="text-muted-foreground">{isZh ? '排序' : 'Order'}</span>
                  <p className="font-medium text-foreground">{selectedChunk.readingOrder}</p>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-3">
                  <span className="text-muted-foreground">{isZh ? '字符数' : 'Chars'}</span>
                  <p className="font-medium text-foreground">{selectedChunk.text.length}</p>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-muted/20 p-4">
                <label className="block text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">
                  {isZh ? '文本内容' : 'Content'}
                </label>
                <pre className="text-xs text-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-[60vh] overflow-y-auto">
                  {selectedChunk.text}
                </pre>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-6">
              {/* Statistics overview */}
              <h3 className="text-sm font-semibold text-foreground mb-4">
                {isZh ? '数据统计' : 'Statistics'}
              </h3>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="rounded-lg border border-border bg-card p-4">
                  <p className="text-2xl font-bold text-primary">{chapters.length}</p>
                  <p className="text-xs text-muted-foreground">{isZh ? '章节' : 'Chapters'}</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-4">
                  <p className="text-2xl font-bold text-emerald-400">{totalChunks}</p>
                  <p className="text-xs text-muted-foreground">{isZh ? '文本块' : 'Chunks'}</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-4">
                  <p className="text-2xl font-bold text-blue-400">{chunks.filter(c => c.vectorized).length}/{chunks.length}</p>
                  <p className="text-xs text-muted-foreground">{isZh ? '已向量化（本页）' : 'Vectorized (this page)'}</p>
                </div>
              </div>

              {/* Chunk list */}
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {isZh ? '所有文本块' : 'All Chunks'} ({totalChunks})
                </h4>
                {totalPages > 1 && (
                  <div className="flex items-center gap-1.5">
                    <button disabled={chunkPage <= 1} onClick={() => setChunkPage(p => p - 1)}
                      className="px-2 py-1 text-[10px] rounded border border-border bg-background text-foreground disabled:opacity-30">
                      ←
                    </button>
                    <span className="text-[10px] text-muted-foreground">{chunkPage}/{totalPages}</span>
                    <button disabled={chunkPage >= totalPages} onClick={() => setChunkPage(p => p + 1)}
                      className="px-2 py-1 text-[10px] rounded border border-border bg-background text-foreground disabled:opacity-30">
                      →
                    </button>
                  </div>
                )}
              </div>

              <div className="space-y-1">
                {chunks.map((chunk) => {
                  const Icon = CONTENT_TYPE_ICON[chunk.contentType] ?? FileText
                  return (
                    <button
                      key={chunk.id}
                      type="button"
                      onClick={() => setSelectedChunk(chunk)}
                      className="flex items-center gap-3 w-full rounded-md px-3 py-2 text-left text-xs hover:bg-secondary transition-colors border border-transparent hover:border-border"
                    >
                      <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <span className="font-mono text-[10px] text-muted-foreground w-8 shrink-0">p.{chunk.pageNumber}</span>
                      <span className="text-foreground truncate flex-1">{chunk.text.slice(0, 100)}</span>
                      <span className={cn(
                        'text-[9px] shrink-0',
                        chunk.vectorized ? 'text-emerald-400' : 'text-muted-foreground/50'
                      )}>
                        {chunk.vectorized ? '●' : '○'}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
