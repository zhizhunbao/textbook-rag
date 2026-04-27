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
import { queryTextbookStream } from "@/features/engine/query_engine";
import { fetchAvailableModels } from "@/features/engine/llms";
import { useAppDispatch, useAppState } from "@/features/shared/AppContext";
import { useAuth } from "@/features/shared/AuthProvider";
import { useI18n } from "@/features/shared/i18n";
import type { ModelInfo, SourceInfo } from "@/features/shared/types";

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
}: {
  activeSessionId: string | null;
  onSessionCreated: (id: string) => void;
  /** Exposed so parent can trigger submitQuestion from sidebar */
  submitRef?: React.MutableRefObject<((q: string) => void) | null>;
  /** Questions sidebar state */
  showQuestions?: boolean;
  onToggleQuestions?: () => void;
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
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // Token accumulator — ref avoids re-renders per token; RAF batches at 60fps
  const tokenBufferRef = useRef("");
  const rafIdRef = useRef<number | null>(null);
  // Prompt mode state — user-selected system prompt override
  const [promptSlug, setPromptSlug] = useState<string | null>(null);
  const [customSystemPrompt, setCustomSystemPrompt] = useState<string | null>(null);

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

  /** Track current session id across renders inside callbacks */
  const sessionIdRef = useRef<string | null>(activeSessionId);
  /** Track the previous session id so we detect session switches */
  const prevSessionIdRef = useRef<string | null>(activeSessionId);
  useEffect(() => {
    sessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  /** When history panel selects an old session (or page refreshes), restore its messages */
  useEffect(() => {
    if (!activeSessionId) return;

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
    // Re-run when sessions list arrives (fixes race on page refresh)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId, chatHistory.sessions]);

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
    const distanceFromBottom =
      thread.scrollHeight - thread.scrollTop - thread.clientHeight;
    const nextNearBottom = distanceFromBottom < NEAR_BOTTOM_THRESHOLD;
    shouldStickToBottomRef.current = nextNearBottom;
    setIsNearBottom((prev) => prev === nextNearBottom ? prev : nextNearBottom);
    if (nextNearBottom) setHasNewMessagesBelow((prev) => prev === false ? prev : false);
  }, []);

  /* ── Load models ── */
  useEffect(() => {
    fetchAvailableModels()
      .then((availableModels) => {
        setModels(availableModels);
        if (availableModels.length > 0) {
          const currentMatch = availableModels.find((m) => m.name === selectedModel);
          if (currentMatch) {
            // Model still available — sync provider in case it drifted (e.g. stale sessionStorage)
            if (currentMatch.provider && currentMatch.provider !== selectedProvider) {
              dispatch({ type: "SET_MODEL", model: currentMatch.name, provider: currentMatch.provider });
            }
          } else {
            // Model no longer available — fall back to default
            const preferred =
              availableModels.find((model) => model.is_default) ?? availableModels[0];
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
          sessionId = await chatHistory.createSession({ sessionBookIds, bookTitles, firstMessage: trimmed });
          sessionIdRef.current = sessionId;
          onSessionCreated(sessionId);
        } catch (err) {
          // Session creation failed (e.g. expired auth) — proceed without history
          console.warn('[ChatPanel] Failed to create session, continuing without history:', err);
        }
      }

      const startTime = Date.now();

      // Map Payload CMS IDs → engine book_id strings for correct filtering
      // DM-T1-02: When ALL books are selected, skip the filter so backend searches entire library
      const isAllBooks = sessionBookIds.length === books.length;
      const engineBookIdStrings = isAllBooks
        ? []
        : sessionBookIds
            .map((pid) => books.find((b) => b.id === pid)?.book_id)
            .filter((s): s is string => !!s);
      const filters = engineBookIdStrings.length > 0 ? { book_id_strings: engineBookIdStrings } : undefined;

      await queryTextbookStream(
        { question: trimmed, filters, model: selectedModel, provider: selectedProvider, top_k: 5, custom_system_prompt: customSystemPrompt },
        {
          signal: controller.signal,
          onToken: (token) => {
            // Accumulate in ref (no re-render), flush to state via RAF
            tokenBufferRef.current += token;
            if (rafIdRef.current === null) {
              rafIdRef.current = requestAnimationFrame(() => {
                setStreamingContent(tokenBufferRef.current);
                rafIdRef.current = null;
              });
            }
          },
          onRetrievalDone: ({ sources }) => {
            setStreamingSources(sources);
          },
          onDone: (res) => {
            // Enrich sources with book titles from the loaded books list
            // (backend chunks don't store book_title in metadata)
            const enrichedSources = res.sources.map((s) => {
              if (s.book_title) return s;
              const idStr = s.book_id_string || String(s.book_id);
              // Try exact match on engineBookId (book_id)
              let match = books.find((b) => b.book_id === idStr);
              // Fallback: match by Payload numeric id
              if (!match && typeof s.book_id === 'number') {
                match = books.find((b) => b.id === s.book_id);
              }
              // Fallback: case-insensitive partial match
              if (!match && idStr) {
                const lower = idStr.toLowerCase();
                match = books.find((b) =>
                  b.book_id.toLowerCase() === lower ||
                  b.title.toLowerCase().includes(lower),
                );
              }
              if (!match) {
                console.warn('[CitationEnrich] No book match for source:', { book_id: s.book_id, book_id_string: s.book_id_string, idStr, availableBookIds: books.map(b => b.book_id) });
              }
              return match ? { ...s, book_title: match.title } : s;
            });

            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: res.answer,
                sources: enrichedSources,
                trace: res.trace,
                model: selectedModel || res.trace?.generation?.model || undefined,
                timestamp: new Date().toISOString(),
                telemetry: res.telemetry,
              },
            ]);
            setStreamingContent("");
            setStreamingSources([]);
            tokenBufferRef.current = "";
            if (rafIdRef.current !== null) {
              cancelAnimationFrame(rafIdRef.current);
              rafIdRef.current = null;
            }
            setIsStreaming(false);
            setLoading(false);

            // Persist both messages to chat history
            if (sessionId) {
              chatHistory.appendMessages(sessionId, [
                { role: "user", content: trimmed, timestamp: new Date().toISOString() },
                { role: "assistant", content: res.answer, sources: enrichedSources, trace: res.trace, timestamp: new Date().toISOString() },
              ]);
            }

            // Log query to Payload QueryLogs and capture queryId for inline eval
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
                trace: res.trace,
                model: selectedModel,
                latencyMs,
              }),
            })
              .then(async (r) => {
                if (r.ok) {
                  const doc = await r.json();
                  // Attach queryId to the last assistant message for inline evaluation
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
                    // Also persist queryId to the ChatMessages record
                    if (sessionId) {
                      chatHistory.updateLastAssistantQueryId(sessionId, qId);
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
            setIsStreaming(false);
            setLoading(false);
          },
        },
      );
    },
    [sessionBookIds, selectedModel, selectedProvider, currentUser, books, chatHistory, onSessionCreated, customSystemPrompt],
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
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-background">
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
          // Reset to all-books scope without clearing messages
          dispatch({ type: 'START_SESSION', bookIds: books.map((b) => b.id) });
        }}
        showQuestions={showQuestions}
        onToggleQuestions={onToggleQuestions}
        selectedPromptSlug={promptSlug}
        onPromptChange={(slug, systemPrompt) => {
          setPromptSlug(slug);
          setCustomSystemPrompt(systemPrompt);
        }}
      />

      {/* ── Message thread ── */}
      <div
        ref={threadRef}
        className="chat-thread relative flex-1 overflow-y-auto px-4 pb-44 pt-6"
        onScroll={updateNearBottom}
      >
        {!hasMessages && !loading ? (
          <WelcomeScreen
            sessionBooks={sessionBooks}
            loading={loading}
            onSubmitQuestion={(q) => void submitQuestion(q)}
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
                  queryId={message.queryId}
                  timestamp={message.timestamp}
                  telemetry={message.telemetry}
                  onRetry={message.role === "user" && !loading ? (q) => void submitQuestion(q) : undefined}
                />
              </div>
            ))}

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
    </div>
  );
}
