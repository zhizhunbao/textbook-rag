/**
 * panel/ChatPanel.tsx
 * 聊天主面板 — 组装 ChatHeader / WelcomeScreen / MessageThread / ChatInput
 * 从原来 966 行瘦身到 ~280 行，子组件已拆分到同级文件和 trace/ 子模块
 */
import {
  useState,
  useRef,
  useCallback,
  useEffect,
} from "react";
import { evaluateFromHistory } from "@/features/engine/evaluation/api";
import { fetchAvailableModels, discoverLocalModels } from "@/features/engine/llms";
import { fetchConsultingPersonas, queryConsultingStream } from "@/features/shared/consultingApi";
import { useAppDispatch, useAppState } from "@/features/shared/AppContext";
import { useAuth } from "@/features/shared/AuthProvider";
import { useCountry } from "@/features/shared/CountryContext";
import { useI18n } from "@/features/shared/i18n";
import type { ModelInfo, SourceInfo } from "@/features/shared/types";
import type { PersonaInfo, HighlightKeyword, NumericHighlight } from "@/features/shared/consultingApi";

import type { Message } from "../types";
import { NEAR_BOTTOM_THRESHOLD } from "../types";
import { useChatHistoryContext } from "../history/ChatHistoryContext";
import { ThinkingProcessPanel } from "@/features/engine/evaluation";
import { useSmoothText } from "@/features/shared/hooks/useSmoothText";

import ChatHeader from "./ChatHeader";
import ChatInput from "./ChatInput";
import WelcomeScreen from "./WelcomeScreen";
import MessageBubble from "./MessageBubble";
import SourceCard from "./SourceCard";

export default function ChatPanel({
  activeSessionId,
  onSessionCreated,
  submitRef,
  showQuestions,
  onToggleQuestions,
  isLiveMode = false,  // G7-03: live broadcast mode
  onLiveModeToggle,    // G7-03: toggle callback
  onConsultingPersonaChange,
}: {
  activeSessionId: string | null;
  onSessionCreated: (id: string) => void;
  /** Exposed so parent can trigger submitQuestion from sidebar */
  submitRef?: React.MutableRefObject<((q: string) => void) | null>;
  /** Questions sidebar state */
  showQuestions?: boolean;
  onToggleQuestions?: () => void;
  /** G7-03: Live broadcast mode — large fonts, minimal chrome */
  isLiveMode?: boolean;
  /** G7-03: Toggle live broadcast mode */
  onLiveModeToggle?: () => void;
  /** C4-06: Notify parent when consulting persona changes (for sidebar) */
  onConsultingPersonaChange?: (slug: string, name: string | null) => void;
}) {
  const {
    currentBookId,
    books,
    selectedModel,
    selectedProvider,
    sessionBookIds,
  } = useAppState();
  const dispatch = useAppDispatch();
  const { user: currentUser } = useAuth();
  const { country } = useCountry();
  const { t } = useI18n();
  const chatHistory = useChatHistoryContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [hasNewMessagesBelow, setHasNewMessagesBelow] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamingSources, setStreamingSources] = useState<SourceInfo[]>([]);
  const [streamingKeywords, setStreamingKeywords] = useState<HighlightKeyword[]>([]);
  const [streamingNumericHighlights, setStreamingNumericHighlights] = useState<NumericHighlight[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [personas, setPersonas] = useState<PersonaInfo[]>([]);
  const [selectedPersonaSlug, setSelectedPersonaSlug] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Token accumulator — ref avoids re-renders per token; RAF batches at 60fps
  const tokenBufferRef = useRef("");
  const rafIdRef = useRef<number | null>(null);
  // Prompt mode state — user-selected system prompt override
  const [customSystemPrompt, setCustomSystemPrompt] = useState<string | null>(null);
  // Retrieval settings — user-adjustable from ChatHeader settings row
  const [topK, setTopK] = useState(5);
  const [rerankerEnabled, setRerankerEnabled] = useState(false);
  const [autoEvaluate, setAutoEvaluate] = useState(false);
  /** Ref to track autoEvaluate inside callbacks without stale closures */
  const autoEvaluateRef = useRef(false);
  useEffect(() => { autoEvaluateRef.current = autoEvaluate; }, [autoEvaluate]);
  // G1-07: Response language state (synced from localStorage)
  const [responseLang, setResponseLang] = useState<string | null>(null);
  useEffect(() => {
    try {
      const stored = localStorage.getItem('consultrag_language');
      if (stored) setResponseLang(stored);
    } catch { /* SSR */ }
  }, []);

  // Smooth text reveal — à la Coze/GPT typewriter effect
  const { displayText: smoothedText, isRevealing } = useSmoothText({
    text: streamingContent,
    isStreaming,
    speed: 12,
  });

  const threadRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);

  const sessionBooks = books.filter((b) => sessionBookIds.includes(b.id));
  const hasMessages = messages.length > 0;
  const activeSession = activeSessionId ? chatHistory.getSession(activeSessionId) : null;
  const effectiveMode = "consulting";
  const effectivePersonaSlug = activeSession?.personaSlug ?? selectedPersonaSlug;
  const isAdmin = currentUser?.role === 'admin';
  const modeLocked = isAdmin ? false : (hasMessages || !!activeSessionId);

  /** Track current session id across renders inside callbacks */
  const sessionIdRef = useRef<string | null>(activeSessionId);
  /** Track the previous session id so we detect session switches */
  const prevSessionIdRef = useRef<string | null>(activeSessionId);
  useEffect(() => {
    sessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  useEffect(() => {
    fetchConsultingPersonas()
      .then((items) => {
        setPersonas(items);
        setSelectedPersonaSlug((current) => {
          if (current) return current;
          // G7-03: In live mode, always default to live-study-immigration
          const defaultSlug = isLiveMode ? 'live-study-immigration' : 'live-study-immigration';
          const defaultPersona = items.find((p) => p.slug === defaultSlug);
          return defaultPersona?.slug ?? items[0]?.slug ?? null;
        });
      })
      .catch(() => setPersonas([]));
  }, [currentUser?.selectedPersona, isLiveMode]);

  // C4-06: Propagate persona selection to parent for sidebar integration
  // Use selectedPersonaSlug (user's current selection) instead of effectivePersonaSlug
  // (which is locked to the active session) so the questions sidebar updates immediately
  useEffect(() => {
    if (!selectedPersonaSlug) return;
    const persona = personas.find((p) => p.slug === selectedPersonaSlug);
    onConsultingPersonaChange?.(selectedPersonaSlug, persona?.name ?? null);
  }, [selectedPersonaSlug, personas, onConsultingPersonaChange]);



  /** When history panel selects an old session, or switches to a new chat */
  useEffect(() => {
    if (!activeSessionId) {
      // If we transitioned from an active session to a new chat (null), clear the UI
      if (prevSessionIdRef.current !== null) {
        setMessages([]);
        setInput("");
        setStreamingContent("");
        setStreamingSources([]);
        setLoading(false);
        setError(null);
        prevSessionIdRef.current = null;
        sessionIdRef.current = null;
      }
      return;
    }

    // NEVER overwrite messages during an active chat (streaming / loading)
    // This prevents appendMessages() → sessions update → effect re-run
    // from clobbering the live conversation state.
    if (isStreaming || loading) return;

    // Detect session switch — clear stale messages from the previous session
    const isSessionSwitch = prevSessionIdRef.current !== activeSessionId;
    if (isSessionSwitch) {
      prevSessionIdRef.current = activeSessionId;
      setMessages([]);
    }

    // Only restore from cache/server on session switch or initial load (empty local state)
    // Do NOT overwrite when sessions list updates mid-conversation (appendMessages trigger)
    if (!isSessionSwitch && messages.length > 0) return;

    const session = chatHistory.getSession(activeSessionId);
    if (session && session.messages.length > 0) {
      setMessages(session.messages as Message[]);
      return;
    }
    // Messages not cached — lazy-load from Payload
    chatHistory.loadSessionMessages(activeSessionId).then((msgs) => {
      // Guard: don't overwrite if user started chatting while we were loading
      if (sessionIdRef.current !== activeSessionId) return;
      if (msgs.length > 0) {
        setMessages(msgs as Message[]);
      }
    });
    // Re-run when session count changes (fixes race on page refresh)
    // ⚠️ Do NOT depend on chatHistory.sessions (object ref) — that causes
    //    infinite loops because loadSessionMessages calls setSessions to cache,
    //    which changes the ref, which re-triggers this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId, chatHistory.sessions.length]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const thread = threadRef.current;
    if (!thread) return;
    thread.scrollTo({ top: thread.scrollHeight, behavior });
    shouldStickToBottomRef.current = true;
    setIsNearBottom((prev) => prev === true ? prev : true);
    setHasNewMessagesBelow((prev) => prev === false ? prev : false);
  }, []);

  const updateNearBottom = useCallback(() => {
    const thread = threadRef.current;
    if (!thread) return;
    const distanceFromBottom = Math.ceil(
      thread.scrollHeight - thread.scrollTop - thread.clientHeight
    );
    
    // Only lock to bottom if strictly at the bottom (2px leniency for zoom/fractional pixels).
    const isAtBottom = distanceFromBottom <= 2;
    // NEAR_BOTTOM_THRESHOLD is for showing the "jump to latest" button.
    const nextNearBottom = distanceFromBottom < NEAR_BOTTOM_THRESHOLD;
    
    shouldStickToBottomRef.current = isAtBottom;
    setIsNearBottom((prev) => (prev === nextNearBottom ? prev : nextNearBottom));
    if (nextNearBottom) setHasNewMessagesBelow((prev) => (prev === false ? prev : false));
  }, []);

  /* ── Load models — cross-check local models with Ollama /api/tags ── */
  useEffect(() => {
    Promise.all([fetchAvailableModels(), discoverLocalModels().catch(() => [])])
      .then(([cmsModels, localModels]) => {
        // Build a set of actually-installed Ollama model names
        const installedNames = new Set(localModels.map((m) => m.name));

        // Keep cloud models as-is; for Ollama models, only keep those truly installed
        const verified = cmsModels.filter((m) => {
          if (m.provider && m.provider !== "ollama") return true; // cloud → always keep
          return installedNames.has(m.name); // local → must be installed
        });

        setModels(verified);
        if (verified.length > 0) {
          const currentMatch = verified.find((m) => m.name === selectedModel);
          if (currentMatch) {
            if (currentMatch.provider && currentMatch.provider !== selectedProvider) {
              dispatch({ type: "SET_MODEL", model: currentMatch.name, provider: currentMatch.provider });
            }
          } else {
            const preferred =
              verified.find((model) => model.is_default) ?? verified[0];
            dispatch({ type: "SET_MODEL", model: preferred.name, provider: preferred.provider });
          }
        }
      })
      .catch(() => setModels([]));
  }, [dispatch, selectedModel, selectedProvider]);



  /* ── Auto-scroll on new messages / loading changes ── */
  useEffect(() => {
    if (!threadRef.current) return;
    if (!hasMessages) {
      scrollToBottom("auto");
      return;
    }
    if (shouldStickToBottomRef.current) {
      scrollToBottom("smooth");
      return;
    }
    setHasNewMessagesBelow(true);
  }, [hasMessages, loading, messages, scrollToBottom]);

  /* ── Keep scrolled to bottom during streaming (RAF, no state deps) ── */
  useEffect(() => {
    if (!isStreaming || !shouldStickToBottomRef.current) return;
    let id: number;
    const tick = () => {
      const el = threadRef.current;
      if (el && shouldStickToBottomRef.current) {
        el.scrollTop = el.scrollHeight;
      }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [isStreaming]);

  /* ── Submit question ── */
  const submitQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      const existingSession = sessionIdRef.current
        ? chatHistory.getSession(sessionIdRef.current)
        : null;
      const personaSlug = existingSession?.personaSlug ?? selectedPersonaSlug;
      const persona = personas.find((item) => item.slug === personaSlug) ?? null;
      if (!personaSlug) {
        setError("Please select a consulting persona before sending.");
        return;
      }

      setInput("");
      setError(null);
      shouldStickToBottomRef.current = true;
      setHasNewMessagesBelow(false);
      setMessages((prev) => [...prev, { role: "user", content: trimmed, timestamp: new Date().toISOString() }]);
      setLoading(true);
      setStreamingContent("");
      setStreamingSources([]);
      tokenBufferRef.current = "";
      setIsStreaming(true);

      // Abort any previous stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      // Create a new history session on the first message of a fresh conversation
      let sessionId = sessionIdRef.current;
      if (!sessionId) {
        try {
          const bookTitles = books
            .filter((b) => sessionBookIds.includes(b.id))
            .map((b) => b.title);
          sessionId = await chatHistory.createSession({
            sessionBookIds,
            bookTitles,
            firstMessage: trimmed,
            mode: "consulting",
            personaSlug: personaSlug,
            personaName: persona?.name ?? null,
          });
          sessionIdRef.current = sessionId;
          onSessionCreated(sessionId);
        } catch (err) {
          // Session creation failed (e.g. expired auth) — proceed without history
          console.warn('[ChatPanel] Failed to create session, continuing without history:', err);
        }
      }

      const startTime = Date.now();

      // G8-02: Map book filter for textbook persona
      const isAllBooks = sessionBookIds.length === books.length;
      const engineBookIdStrings = isAllBooks
        ? undefined
        : sessionBookIds
            .map((pid) => books.find((b) => b.id === pid)?.book_id)
            .filter((s): s is string => !!s);

      // Build chat history for follow-up question contextualization
      // Only send last 6 messages (3 turns) with truncated content to limit payload
      const recentChatHistory = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content.slice(0, 500),
      }));

      await queryConsultingStream(
          {
            persona_slug: personaSlug,
            question: trimmed,
            model: selectedModel,
            provider: selectedProvider,
            top_k: topK,
            country,
            response_language: responseLang,
            book_id_strings: engineBookIdStrings?.length ? engineBookIdStrings : undefined,
            chat_history: recentChatHistory.length > 0 ? recentChatHistory : undefined,
          },
          {
            signal: controller.signal,
            onToken: (token) => {
              tokenBufferRef.current += token;
              if (rafIdRef.current === null) {
                rafIdRef.current = requestAnimationFrame(() => {
                  setStreamingContent(tokenBufferRef.current);
                  rafIdRef.current = null;
                });
              }
            },
            onRetrievalDone: ({ sources, highlight_keywords, numeric_highlights }) => {
              setStreamingSources(sources);
              setStreamingKeywords(highlight_keywords ?? []);
              setStreamingNumericHighlights(numeric_highlights ?? []);
            },
            onWarning: ({ message }) => {
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `⚠️ ${message}`, timestamp: new Date().toISOString() },
              ]);
            },
            onDone: (res) => {
              // G8-03: Source enrichment — enrich book_title from frontend books list
              const enrichedSources = res.sources.map((s) => {
                if (s.book_title) return s;
                const idStr = s.book_id_string || String(s.book_id);
                let match = books.find((b) => b.book_id === idStr);
                if (!match && typeof s.book_id === 'number') {
                  match = books.find((b) => b.id === s.book_id);
                }
                if (!match && idStr) {
                  const lower = idStr.toLowerCase();
                  match = books.find((b) =>
                    b.book_id.toLowerCase() === lower ||
                    b.title.toLowerCase().includes(lower),
                  );
                }
                return match ? { ...s, book_title: match.title } : s;
              });
              const kws = res.highlight_keywords ?? [];
              const numHl = res.numeric_highlights ?? [];
              const answerKws = res.answer_highlight_keywords ?? [];
              setMessages((prev) => {
                // Backfill keywords onto the preceding user message
                const updated = prev.map((m, i) =>
                  i === prev.length - 1 && m.role === "user" && kws.length > 0
                    ? { ...m, highlightKeywords: kws }
                    : m,
                );
                updated.push({
                  role: "assistant",
                  content: res.answer,
                  sources: enrichedSources,
                  model: selectedModel || undefined,
                  timestamp: new Date().toISOString(),
                  telemetry: res.telemetry,
                  highlightKeywords: kws,
                  numericHighlights: numHl,
                  answerHighlightKeywords: answerKws.length > 0 ? answerKws : undefined,
                });
                return updated;
              });
              setStreamingContent("");
              setStreamingSources([]);
              setStreamingKeywords([]);
              setStreamingNumericHighlights([]);
              tokenBufferRef.current = "";
              if (rafIdRef.current !== null) {
                cancelAnimationFrame(rafIdRef.current);
                rafIdRef.current = null;
              }
              setIsStreaming(false);
              setLoading(false);

              if (sessionId) {
                chatHistory.appendMessages(sessionId, [
                  { role: "user", content: trimmed, timestamp: new Date().toISOString(), highlightKeywords: kws.length > 0 ? kws : undefined },
                  { role: "assistant", content: res.answer, sources: enrichedSources, timestamp: new Date().toISOString(), model: selectedModel || undefined, telemetry: res.telemetry, highlightKeywords: kws.length > 0 ? kws : undefined, numericHighlights: numHl.length > 0 ? numHl : undefined, answerHighlightKeywords: answerKws.length > 0 ? answerKws : undefined },
                ]);
              }

              const latencyMs = Date.now() - startTime;
              fetch('/api/queries', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                  user: currentUser?.id ?? null,
                  sessionId: sessionId ?? null,
                  question: trimmed,
                  answer: res.answer,
                  sources: enrichedSources,
                  model: selectedModel,
                  latencyMs,
                }),
              })
                .then(async (r) => {
                  if (r.ok) {
                    const doc = await r.json();
                    if (doc?.doc?.id) {
                      const qId = doc.doc.id as number;
                      setMessages((prev) => {
                        const updated = [...prev];
                        const last = updated[updated.length - 1];
                        if (last?.role === 'assistant') {
                          updated[updated.length - 1] = { ...last, queryId: qId };
                        }
                        return updated;
                      });
                      if (sessionId) {
                        chatHistory.updateLastAssistantQueryId(sessionId, qId);
                      }
                      if (autoEvaluateRef.current) {
                        evaluateFromHistory(qId).catch(() => { /* ignore eval errors */ });
                      }
                    }
                  }
                })
                .catch(() => { /* ignore logging errors */ });
            },
            onError: (err) => {
              setError(err.message);
              tokenBufferRef.current = "";
              if (rafIdRef.current !== null) {
                cancelAnimationFrame(rafIdRef.current);
                rafIdRef.current = null;
              }
              setStreamingSources([]);
              setStreamingKeywords([]);
              setStreamingNumericHighlights([]);
              setIsStreaming(false);
              setLoading(false);
            },
          },
        );
    },
    [sessionBookIds, selectedModel, selectedProvider, currentUser, books, chatHistory, onSessionCreated, customSystemPrompt, selectedPersonaSlug, personas, topK, country, responseLang, autoEvaluate],
  );

  /** Expose submitQuestion to parent (so QuestionsSidebar can call it) */
  useEffect(() => {
    if (submitRef) submitRef.current = (q: string) => void submitQuestion(q);
    return () => { if (submitRef) submitRef.current = null; };
  }, [submitRef, submitQuestion]);

  /** Go back to the book picker — ends the session */
  const resetConversation = useCallback(() => {
    setMessages([]);
    setInput("");
    setLoading(false);
    setError(null);
    setHasNewMessagesBelow(false);
    setIsNearBottom(true);
    shouldStickToBottomRef.current = true;
    sessionIdRef.current = null;
    dispatch({ type: "RESET_SESSION" });
  }, [dispatch]);



  return (
    <div className={`relative flex h-full min-h-0 flex-col overflow-hidden bg-background${isLiveMode ? ' live-mode' : ''}`}>
      {/* ── Header ── */}
      <ChatHeader
        sessionBooks={sessionBooks}
        totalBookCount={books.length}
        selectedModel={selectedModel}
        models={models}
        loading={loading}
        onModelChange={(model, provider) => dispatch({ type: "SET_MODEL", model, provider })}
        onNewChat={resetConversation}
        onClearScope={() => {
          dispatch({ type: 'START_SESSION', bookIds: books.map((b) => b.id) });
        }}
        showQuestions={showQuestions}
        onToggleQuestions={onToggleQuestions}
        personas={personas}
        selectedPersonaSlug={effectivePersonaSlug}
        modeLocked={modeLocked}
        onPersonaChange={setSelectedPersonaSlug}
        topK={topK}
        rerankerEnabled={rerankerEnabled}
        autoEvaluate={autoEvaluate}
        onTopKChange={setTopK}
        onRerankerChange={setRerankerEnabled}
        onAutoEvaluateChange={setAutoEvaluate}
        isLiveMode={isLiveMode}
        onLiveModeToggle={onLiveModeToggle}
      />

      {/* ── Message thread ── */}
      <div
        ref={threadRef}
        className="chat-thread relative flex-1 overflow-y-auto px-4 pb-44 pt-6"
        onScroll={updateNearBottom}
        onWheel={(e) => {
          if (e.deltaY < 0) {
            shouldStickToBottomRef.current = false;
            setIsNearBottom(false);
          }
        }}
        onTouchStart={() => {
          shouldStickToBottomRef.current = false;
          setIsNearBottom(false);
        }}
      >


        {!hasMessages && !loading && !isLiveMode ? (
          <WelcomeScreen
            sessionBooks={sessionBooks}
            loading={loading}
            onSubmitQuestion={(q) => void submitQuestion(q)}
          />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-3">
            {messages.map((message, index) => {
              return (
                <div key={`${message.role}-${index}`} className="space-y-2">
                  <MessageBubble
                    role={message.role}
                    content={message.content}
                    sources={message.sources}
                    model={message.model}
                    queryId={message.queryId}
                    timestamp={message.timestamp}
                    telemetry={message.telemetry}
                    onRetry={message.role === "user" && !loading ? (q) => void submitQuestion(q) : undefined}
                    highlightKeywords={message.highlightKeywords}
                    numericHighlights={message.numericHighlights}
                    answerHighlightKeywords={message.answerHighlightKeywords}
                  />
                </div>
              );
            })}

            {/* Streaming bubble — shown while tokens arrive */}
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

      {hasNewMessagesBelow && !isNearBottom && (
        <div className="pointer-events-none absolute inset-x-0 bottom-44 flex justify-center px-4">
            <button
            type="button"
            onClick={() => scrollToBottom("smooth")}
            className="pointer-events-auto rounded-full border border-border bg-card px-4 py-1.5 text-xs font-medium text-foreground shadow-sm transition hover:bg-accent"
          >
            {t.chatJumpToLatest}
          </button>
        </div>
      )}

      {/* ── Input area ── */}
      <ChatInput
        sessionBooks={sessionBooks}
        input={input}
        loading={loading}
        onInputChange={setInput}
        onSubmit={(q) => void submitQuestion(q)}
      />

      {/* G7-05: Brand watermark — live mode only */}
      {isLiveMode && (
        <div className="live-watermark">
          Powered by ConsultRAG
        </div>
      )}
    </div>
  );
}
