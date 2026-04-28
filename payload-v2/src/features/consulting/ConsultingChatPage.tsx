/**
 * ConsultingChatPage — AI consulting chat with persona-specific knowledge base.
 *
 * Sprint C5: Full chat UI for consulting personas.
 * Features:
 *   - Persona header with name + icon
 *   - SSE streaming chat (reuses existing MessageBubble/ChatInput)
 *   - Dual-collection retrieval (persona KB + user private docs when logged in)
 *   - Source cards with retrieval_origin tags (persona_kb / user_private)
 */

'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useAuth } from '@/features/shared/AuthProvider'
import { useI18n } from '@/features/shared/i18n'
import { fetchAvailableModels } from '@/features/engine/llms'
import { useSmoothText } from '@/features/shared/hooks/useSmoothText'
import type { ModelInfo, SourceInfo } from '@/features/shared/types'
import type { Message } from '@/features/chat/types'
import { NEAR_BOTTOM_THRESHOLD } from '@/features/chat/types'
import MessageBubble from '@/features/chat/panel/MessageBubble'
import ChatInput from '@/features/chat/panel/ChatInput'
import { queryConsultingStream, type PersonaInfo } from './api'

// ── Persona Header ──

function PersonaHeader({
  persona,
  selectedModel,
  models,
  onModelChange,
}: {
  persona: { name: string; slug: string; icon?: string; description?: string }
  selectedModel: string | null
  models: ModelInfo[]
  onModelChange: (model: string, provider?: string) => void
}) {
  return (
    <div className="shrink-0 flex items-center gap-4 px-6 py-3 border-b border-border bg-card/80 backdrop-blur-sm">
      {/* Persona identity */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary text-lg font-bold shrink-0">
          {persona.icon === 'scale' && '⚖️'}
          {persona.icon === 'shield-check' && '🛡️'}
          {persona.icon === 'clipboard-check' && '📋'}
          {!persona.icon && '💼'}
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground truncate">{persona.name}</h2>
          {persona.description && (
            <p className="text-xs text-muted-foreground truncate">{persona.description}</p>
          )}
        </div>
      </div>

      {/* Model selector */}
      {models.length > 0 && (
        <select
          value={selectedModel ?? ''}
          onChange={(e) => {
            const m = models.find((mod) => mod.name === e.target.value)
            if (m) onModelChange(m.name, m.provider)
          }}
          className="text-xs bg-muted border border-border rounded-lg px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name}
            </option>
          ))}
        </select>
      )}
    </div>
  )
}

// ── Welcome Screen ──

function ConsultingWelcome({
  persona,
  onSubmit,
}: {
  persona: { name: string; description?: string }
  onSubmit: (q: string) => void
}) {
  const suggestions = getSuggestions(persona.name)

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
      <div className="text-center max-w-lg space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mx-auto mb-2">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-foreground">{persona.name}</h2>
        {persona.description && (
          <p className="text-sm text-muted-foreground">{persona.description}</p>
        )}
        <p className="text-xs text-muted-foreground mt-4">Try asking:</p>
        <div className="flex flex-wrap gap-2 justify-center mt-2">
          {suggestions.map((q, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onSubmit(q)}
              className="text-xs px-3 py-2 rounded-lg border border-border bg-card hover:bg-muted hover:border-primary/30 text-foreground transition-colors text-left"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function getSuggestions(personaName: string): string[] {
  if (personaName.toLowerCase().includes('lawyer') || personaName.includes('法律')) {
    return [
      '劳动合同解除有哪些合法条件？',
      '竞业限制协议的法律效力如何？',
      '企业裁员需要遵守哪些法规？',
    ]
  }
  if (personaName.toLowerCase().includes('compliance') || personaName.includes('合规')) {
    return [
      '数据隐私合规的基本要求有哪些？',
      '反洗钱（AML）合规检查要点？',
      '跨境数据传输的合规框架？',
    ]
  }
  if (personaName.toLowerCase().includes('auditor') || personaName.includes('审计')) {
    return [
      '内部审计流程的标准步骤？',
      '风险评估矩阵如何构建？',
      '审计报告的关键要素有哪些？',
    ]
  }
  return ['How can you help me?', 'What topics are covered in your knowledge base?']
}

// ── Main Page ──

export default function ConsultingChatPage({ persona }: { persona: PersonaInfo }) {
  const { user } = useAuth()
  const { t } = useI18n()

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<string | undefined>()
  const [isNearBottom, setIsNearBottom] = useState(true)
  const [hasNewMessagesBelow, setHasNewMessagesBelow] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingSources, setStreamingSources] = useState<SourceInfo[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const tokenBufferRef = useRef('')
  const rafIdRef = useRef<number | null>(null)
  const threadRef = useRef<HTMLDivElement>(null)
  const shouldStickToBottomRef = useRef(true)

  const hasMessages = messages.length > 0

  const { displayText: smoothedText, isRevealing } = useSmoothText({
    text: streamingContent,
    isStreaming,
    speed: 12,
  })

  // Load models
  useEffect(() => {
    fetchAvailableModels()
      .then((available) => {
        setModels(available)
        if (available.length > 0) {
          const preferred = available.find((m) => m.is_default) ?? available[0]
          setSelectedModel(preferred.name)
          setSelectedProvider(preferred.provider)
        }
      })
      .catch(() => setModels([]))
  }, [])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const el = threadRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior })
    shouldStickToBottomRef.current = true
    setIsNearBottom(true)
    setHasNewMessagesBelow(false)
  }, [])

  const updateNearBottom = useCallback(() => {
    const el = threadRef.current
    if (!el) return
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight
    const near = dist < NEAR_BOTTOM_THRESHOLD
    shouldStickToBottomRef.current = near
    setIsNearBottom(near)
    if (near) setHasNewMessagesBelow(false)
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    if (shouldStickToBottomRef.current) scrollToBottom('smooth')
    else if (hasMessages) setHasNewMessagesBelow(true)
  }, [hasMessages, loading, messages, scrollToBottom])

  // Keep scrolled during streaming
  useEffect(() => {
    if (!isStreaming || !shouldStickToBottomRef.current) return
    let id: number
    const tick = () => {
      const el = threadRef.current
      if (el && shouldStickToBottomRef.current) el.scrollTop = el.scrollHeight
      id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [isStreaming])

  // Submit question
  const submitQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim()
      if (!trimmed) return

      setInput('')
      setError(null)
      shouldStickToBottomRef.current = true
      setHasNewMessagesBelow(false)
      setMessages((prev) => [...prev, { role: 'user', content: trimmed, timestamp: new Date().toISOString() }])
      setLoading(true)
      setStreamingContent('')
      setStreamingSources([])
      tokenBufferRef.current = ''
      setIsStreaming(true)

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      await queryConsultingStream(
        {
          persona_slug: persona.slug,
          question: trimmed,
          top_k: 5,
          model: selectedModel,
          provider: selectedProvider,
          user_id: user?.id ?? null,
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
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: res.answer,
                sources: res.sources,
                model: selectedModel || undefined,
                timestamp: new Date().toISOString(),
              },
            ])
            setStreamingContent('')
            setStreamingSources([])
            tokenBufferRef.current = ''
            if (rafIdRef.current !== null) {
              cancelAnimationFrame(rafIdRef.current)
              rafIdRef.current = null
            }
            setIsStreaming(false)
            setLoading(false)
          },
          onError: (err) => {
            setError(err.message)
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
    [persona.slug, selectedModel, selectedProvider, user],
  )

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-background">
      {/* ── Persona Header ── */}
      <PersonaHeader
        persona={persona}
        selectedModel={selectedModel}
        models={models}
        onModelChange={(model, provider) => {
          setSelectedModel(model)
          setSelectedProvider(provider)
        }}
      />

      {/* ── Message thread ── */}
      <div
        ref={threadRef}
        className="chat-thread relative flex-1 overflow-y-auto px-4 pb-44 pt-6"
        onScroll={updateNearBottom}
      >
        {!hasMessages && !loading ? (
          <ConsultingWelcome
            persona={persona}
            onSubmit={(q) => void submitQuestion(q)}
          />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-3">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className="space-y-2">
                <MessageBubble
                  role={message.role}
                  content={message.content}
                  sources={message.sources}
                  model={message.model}
                  timestamp={message.timestamp}
                  onRetry={message.role === 'user' && !loading ? (q) => void submitQuestion(q) : undefined}
                />
              </div>
            ))}

            {/* Streaming bubble */}
            {isStreaming && smoothedText && (
              <div className="space-y-2">
                <MessageBubble
                  role="assistant"
                  content={smoothedText}
                  sources={streamingSources}
                  model={selectedModel || undefined}
                  isStreaming={isRevealing}
                />
              </div>
            )}

            {loading && !isStreaming && (
              <div className="flex items-start gap-3">
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
                  </svg>
                </div>
                <div className="rounded-2xl rounded-tl-md border border-border bg-card px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.2s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.1s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {t.chatSearching}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive shadow-sm">
                {error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Scroll to bottom */}
      {hasNewMessagesBelow && !isNearBottom && (
        <div className="pointer-events-none absolute inset-x-0 bottom-44 flex justify-center px-4">
          <button
            type="button"
            onClick={() => scrollToBottom('smooth')}
            className="pointer-events-auto rounded-full border border-border bg-card px-4 py-1.5 text-xs font-medium text-foreground shadow-sm transition hover:bg-accent"
          >
            {t.chatJumpToLatest}
          </button>
        </div>
      )}

      {/* ── Input area ── */}
      <ChatInput
        sessionBooks={[]}
        input={input}
        loading={loading}
        onInputChange={setInput}
        onSubmit={(q) => void submitQuestion(q)}
      />
    </div>
  )
}
