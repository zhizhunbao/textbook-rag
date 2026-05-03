'use client'

/**
 * LiveQAPage — Full-screen live broadcast Q&A demo page.
 *
 * G7-03: Main page for "程序员聊留学移民" WeChat live stream.
 * G7-04: Preset question sidebar with category grouping.
 * G7-05: Brand watermark overlay.
 * G7-09: PDF source jump (reuses CitationChip from chat module).
 *
 * i18n: Uses next-intl useTranslations('live') for all UI text.
 *       Questions are externalized to messages/{locale}/live.json.
 *
 * Features:
 *   - Full-screen dark theme, optimized for 1080p streaming
 *   - Dual input: clickable preset questions + manual input
 *   - Streaming typewriter effect via SSE
 *   - Source citations with PDF jump capability
 *   - Session logging to localStorage for post-stream analysis
 *   - Ctrl+H to toggle sidebar
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import { queryConsultingStream } from '@/features/shared/consultingApi'
import type { SourceInfo } from '@/features/shared/types'
import type { LlmTelemetry } from '@/features/engine/query_engine/types'
import { useAppDispatch } from '@/features/shared/AppContext'
import { useSmoothText } from '@/features/shared/hooks/useSmoothText'
import Markdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'

import './live.css'

// ============================================================
// Types
// ============================================================

interface LiveMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  timestamp: string
  latencyMs?: number
  telemetry?: LlmTelemetry
}

interface PresetQuestion {
  id: string
  category: string
  categoryKey: string
  question: string
  answered: boolean
}

interface SessionLogEntry {
  timestamp: string
  question: string
  answer: string
  sources: SourceInfo[]
  latencyMs: number
}

// ============================================================
// Question definitions (keys match messages/{locale}/live.json)
// ============================================================

const QUESTION_DEFS: { id: string; categoryKey: string; questionKey: string }[] = [
  // Immigration
  { id: 'imm-1', categoryKey: 'immigration', questionKey: 'imm1' },
  { id: 'imm-2', categoryKey: 'immigration', questionKey: 'imm2' },
  { id: 'imm-3', categoryKey: 'immigration', questionKey: 'imm3' },
  { id: 'imm-4', categoryKey: 'immigration', questionKey: 'imm4' },
  { id: 'imm-5', categoryKey: 'immigration', questionKey: 'imm5' },
  { id: 'imm-6', categoryKey: 'immigration', questionKey: 'imm6' },
  { id: 'imm-7', categoryKey: 'immigration', questionKey: 'imm7' },
  // Education
  { id: 'edu-1', categoryKey: 'education', questionKey: 'edu1' },
  { id: 'edu-2', categoryKey: 'education', questionKey: 'edu2' },
  { id: 'edu-3', categoryKey: 'education', questionKey: 'edu3' },
  { id: 'edu-4', categoryKey: 'education', questionKey: 'edu4' },
  { id: 'edu-5', categoryKey: 'education', questionKey: 'edu5' },
  { id: 'edu-6', categoryKey: 'education', questionKey: 'edu6' },
  // Cross-Domain
  { id: 'mix-1', categoryKey: 'crossDomain', questionKey: 'mix1' },
  { id: 'mix-2', categoryKey: 'crossDomain', questionKey: 'mix2' },
  { id: 'mix-3', categoryKey: 'crossDomain', questionKey: 'mix3' },
  { id: 'mix-4', categoryKey: 'crossDomain', questionKey: 'mix4' },
  { id: 'mix-5', categoryKey: 'crossDomain', questionKey: 'mix5' },
  { id: 'mix-6', categoryKey: 'crossDomain', questionKey: 'mix6' },
  { id: 'mix-7', categoryKey: 'crossDomain', questionKey: 'mix7' },
]

// ============================================================
// Constants
// ============================================================

const LIVE_PERSONA = 'live-study-immigration'

// ============================================================
// Component
// ============================================================

export default function LiveQAPage() {
  const t = useTranslations('live')
  const dispatch = useAppDispatch()

  // Build presets from i18n keys
  const [presets, setPresets] = useState<PresetQuestion[]>(() =>
    QUESTION_DEFS.map((def) => ({
      id: def.id,
      categoryKey: def.categoryKey,
      category: t(`categories.${def.categoryKey}`),
      question: t(`questions.${def.questionKey}`),
      answered: false,
    })),
  )

  const [messages, setMessages] = useState<LiveMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingSources, setStreamingSources] = useState<SourceInfo[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sessionLog, setSessionLog] = useState<SessionLogEntry[]>([])

  const answerAreaRef = useRef<HTMLDivElement>(null)
  const tokenBufferRef = useRef('')
  const rafIdRef = useRef<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Smooth text reveal
  const { displayText: smoothedText } = useSmoothText({
    text: streamingContent,
    isStreaming,
    speed: 15,
  })

  // ── Ctrl+H toggle sidebar ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'h') {
        e.preventDefault()
        setSidebarOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── Auto-scroll answer area ──
  useEffect(() => {
    const el = answerAreaRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, smoothedText])

  // ── Submit question ──
  const submitQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      if (!trimmed || loading) return

      setInput('')
      setLoading(true)
      setStreamingContent('')
      setStreamingSources([])
      tokenBufferRef.current = ''
      setIsStreaming(true)

      // Add user message
      const userMsg: LiveMessage = {
        role: 'user',
        content: trimmed,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])

      // Mark preset as answered
      setPresets((prev) =>
        prev.map((p) =>
          p.question === trimmed ? { ...p, answered: true } : p,
        ),
      )

      // Abort any previous stream
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      const startTime = Date.now()

      await queryConsultingStream(
        {
          persona_slug: LIVE_PERSONA,
          question: trimmed,
          top_k: 5,
          response_language: 'zh',
        },
        {
          signal: controller.signal,
          onToken: (token) => {
            tokenBufferRef.current += token
            if (rafIdRef.current === null) {
              rafIdRef.current = requestAnimationFrame(() => {
                setStreamingContent(tokenBufferRef.current)
                rafIdRef.current = null
              })
            }
          },
          onRetrievalDone: ({ sources }) => {
            setStreamingSources(sources)
          },
          onDone: (res) => {
            const latencyMs = Date.now() - startTime
            const assistantMsg: LiveMessage = {
              role: 'assistant',
              content: res.answer,
              sources: res.sources,
              timestamp: new Date().toISOString(),
              latencyMs,
              telemetry: res.telemetry,
            }
            setMessages((prev) => [...prev, assistantMsg])
            setStreamingContent('')
            setStreamingSources([])
            tokenBufferRef.current = ''
            if (rafIdRef.current !== null) {
              cancelAnimationFrame(rafIdRef.current)
              rafIdRef.current = null
            }
            setIsStreaming(false)
            setLoading(false)

            // Log to session
            const entry: SessionLogEntry = {
              timestamp: new Date().toISOString(),
              question: trimmed,
              answer: res.answer,
              sources: res.sources,
              latencyMs,
            }
            setSessionLog((prev) => {
              const next = [...prev, entry]
              try {
                localStorage.setItem(
                  `live_qa_session_${new Date().toISOString().slice(0, 10)}`,
                  JSON.stringify(next),
                )
              } catch { /* storage full */ }
              return next
            })
          },
          onError: (err) => {
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: t('errorPrefix', { message: err.message }),
                timestamp: new Date().toISOString(),
              },
            ])
            tokenBufferRef.current = ''
            if (rafIdRef.current !== null) {
              cancelAnimationFrame(rafIdRef.current)
              rafIdRef.current = null
            }
            setStreamingSources([])
            setIsStreaming(false)
            setLoading(false)
          },
        },
      )
    },
    [loading, t],
  )

  // ── Handle submit from input ──
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      void submitQuestion(input)
    },
    [input, submitQuestion],
  )

  // ── Handle key press ──
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        void submitQuestion(input)
      }
    },
    [input, submitQuestion],
  )

  // ── PDF source click ──
  const handleSourceClick = useCallback(
    (source: SourceInfo, index: number) => {
      const raw = source as any
      dispatch({
        type: 'SELECT_SOURCE',
        source: {
          ...source,
          source_id: raw.chunk_id || raw.source_id || '',
          book_id_string:
            typeof raw.book_id === 'string'
              ? raw.book_id
              : source.book_id_string,
          snippet: raw.snippet || '',
          citation_label: `[${index}]`,
        },
      })
    },
    [dispatch],
  )

  // ── Group presets by category ──
  const categoryKeys = Array.from(new Set(presets.map((p) => p.categoryKey)))

  // ── Get last Q&A pair for display ──
  const lastQuestion = messages.filter((m) => m.role === 'user').at(-1)
  const lastAnswer = messages.filter((m) => m.role === 'assistant').at(-1)
  const answeredCount = presets.filter((p) => p.answered).length

  // ── Source icon SVG ──
  const SourceIcon = () => (
    <svg style={{ width: 14, height: 14 }} viewBox="0 0 16 16" fill="none">
      <path
        d="M4 1.5h5.086a1 1 0 0 1 .707.293l3.414 3.414a1 1 0 0 1 .293.707V13.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1Z"
        stroke="currentColor" strokeWidth="1.3"
      />
      <path d="M9 1.5V5a1 1 0 0 0 1 1h3.5" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  )

  return (
    <div className="live-root">
      <div className="live-container">
        {/* ── Sidebar: Preset Questions (G7-04) ── */}
        <aside className={`live-sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
          <div className="live-sidebar-header">
            <div className="live-sidebar-title">
              {t('sidebarTitle', { answered: answeredCount, total: presets.length })}
            </div>
            <div className="live-sidebar-subtitle">
              {t('sidebarHint')}
            </div>
          </div>
          <div className="live-sidebar-scroll">
            {categoryKeys.map((catKey) => (
              <div key={catKey}>
                <div className="live-category-label">
                  {t(`categories.${catKey}`)}
                </div>
                {presets
                  .filter((p) => p.categoryKey === catKey)
                  .map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className={`live-q-btn ${p.answered ? 'answered' : ''}`}
                      onClick={() => void submitQuestion(p.question)}
                      disabled={loading}
                    >
                      {p.question}
                    </button>
                  ))}
              </div>
            ))}

            {/* Manual questions appended to sidebar */}
            {messages
              .filter(
                (m) =>
                  m.role === 'user' &&
                  !presets.some((p) => p.question === m.content),
              )
              .map((m, i) => (
                <div key={`manual-${i}`}>
                  {i === 0 && (
                    <div className="live-category-label">{t('manualCategory')}</div>
                  )}
                  <button type="button" className="live-q-btn answered" disabled>
                    {m.content}
                  </button>
                </div>
              ))}
          </div>
        </aside>

        {/* ── Main Content ── */}
        <main className="live-main">
          {/* Header */}
          <div className="live-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className="live-header-title">{t('pageTitle')}</span>
              <span className="live-header-badge">{t('liveBadge')}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ fontSize: 12, color: 'var(--live-text-muted)' }}>
                {t('answeredLabel', { count: answeredCount })}
                {sessionLog.length > 0 &&
                  ` · ${t('avgLatency', {
                    seconds: Math.round(
                      sessionLog.reduce((s, e) => s + e.latencyMs, 0) /
                        sessionLog.length / 1000,
                    ),
                  })}`}
              </span>
              <button
                type="button"
                onClick={() => setSidebarOpen((prev) => !prev)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--live-border)',
                  borderRadius: 8,
                  padding: '6px 12px',
                  color: 'var(--live-text-muted)',
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                {sidebarOpen ? t('hideSidebar') : t('showSidebar')}
              </button>
            </div>
          </div>

          {/* Answer Area */}
          <div className="live-answer-area" ref={answerAreaRef}>
            {!lastQuestion && !loading ? (
              <div className="live-empty">
                <svg
                  className="live-empty-icon"
                  fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round" strokeLinejoin="round"
                    d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
                  />
                </svg>
                <div className="live-empty-text">{t('emptyHint')}</div>
              </div>
            ) : (
              <div className="live-slide-up">
                {/* Current question */}
                {lastQuestion && (
                  <div className="live-question">Q: {lastQuestion.content}</div>
                )}

                {/* Loading state */}
                {loading && !isStreaming && (
                  <div className="live-loading">
                    <div className="live-loading-dot" />
                    <div className="live-loading-dot" />
                    <div className="live-loading-dot" />
                  </div>
                )}

                {/* Streaming answer */}
                {isStreaming && smoothedText && (
                  <div className="live-answer">
                    <Markdown rehypePlugins={[rehypeRaw]}>{smoothedText}</Markdown>
                    <span className="live-cursor" />

                    {streamingSources.length > 0 && (
                      <div className="live-sources">
                        {streamingSources.map((s, i) => (
                          <button
                            key={i} type="button" className="live-source-chip"
                            onClick={() => handleSourceClick(s, i + 1)}
                          >
                            <SourceIcon />
                            {s.book_title || t('sourceDoc')} p.{s.page_number}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Completed answer */}
                {!isStreaming && lastAnswer && (
                  <div className="live-answer">
                    <Markdown rehypePlugins={[rehypeRaw]}>{lastAnswer.content}</Markdown>

                    {lastAnswer.sources && lastAnswer.sources.length > 0 && (
                      <div className="live-sources">
                        <div style={{ fontSize: 14, color: 'var(--live-text-muted)', marginBottom: 8 }}>
                          {t('sourcesLabel', { count: lastAnswer.sources.length })}
                        </div>
                        {lastAnswer.sources.map((s, i) => (
                          <button
                            key={i} type="button" className="live-source-chip"
                            onClick={() => handleSourceClick(s, i + 1)}
                            title={t('jumpToPdf')}
                          >
                            <SourceIcon />
                            [{i + 1}] {s.book_title || t('sourceDoc')} p.{s.page_number}
                            {s.score != null && (
                              <span style={{
                                fontSize: 12,
                                color: s.score >= 0.7 ? '#00e676' : 'var(--live-text-muted)',
                              }}>
                                {(s.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    )}

                    {lastAnswer.latencyMs && (
                      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--live-text-muted)', opacity: 0.6 }}>
                        {t('latencyLabel', { seconds: (lastAnswer.latencyMs / 1000).toFixed(1) })}
                        {lastAnswer.telemetry && ` · ${lastAnswer.telemetry.output_tokens} tokens`}
                      </div>
                    )}
                  </div>
                )}

                {/* Previous Q&A history (collapsed) */}
                {messages.length > 2 && (
                  <details style={{ marginTop: 32, borderTop: '1px solid var(--live-border)', paddingTop: 16 }}>
                    <summary style={{ fontSize: 14, color: 'var(--live-text-muted)', cursor: 'pointer', marginBottom: 12 }}>
                      {t('historyTitle', { count: Math.floor(messages.length / 2) })}
                    </summary>
                    {messages
                      .slice(0, -2)
                      .filter((m) => m.role === 'user')
                      .map((m, i) => {
                        const answerMsg = messages.slice(0, -2).filter((a) => a.role === 'assistant')[i]
                        return (
                          <div key={i} style={{
                            marginBottom: 16, padding: 12, borderRadius: 8,
                            background: 'var(--live-card)', border: '1px solid var(--live-border)',
                          }}>
                            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--live-accent)', marginBottom: 4 }}>
                              Q: {m.content}
                            </div>
                            {answerMsg && (
                              <div style={{ fontSize: 13, color: 'var(--live-text-muted)', lineHeight: 1.6, maxHeight: 100, overflow: 'hidden' }}>
                                {answerMsg.content.slice(0, 200)}
                                {answerMsg.content.length > 200 && '...'}
                              </div>
                            )}
                          </div>
                        )
                      })}
                  </details>
                )}
              </div>
            )}
          </div>

          {/* Input bar */}
          <form className="live-input-bar" onSubmit={handleSubmit}>
            <input
              type="text" className="live-input"
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('inputPlaceholder')}
              disabled={loading} autoFocus
            />
            <button
              type="submit" className="live-send-btn"
              disabled={loading || !input.trim()} title="Send (Enter)"
            >
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
              </svg>
            </button>
          </form>
        </main>

        {/* Brand Overlay (G7-05) */}
        <div className="live-brand-overlay">
          <span className="live-brand-text">{t('brandWatermark')}</span>
        </div>
      </div>
    </div>
  )
}
