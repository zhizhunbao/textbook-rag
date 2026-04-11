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
import { queryTextbookStream, fetchDemo } from "@/features/shared/api";
import { fetchAvailableModels } from "@/features/models";
import { useAppDispatch, useAppState } from "@/features/shared/AppContext";
import { useAuth } from "@/features/shared/AuthProvider";
import type { ModelInfo } from "@/features/shared/types";

import type { Message } from "../types";
import { NEAR_BOTTOM_THRESHOLD } from "../types";
import { useChatHistoryContext } from "../history/ChatHistoryContext";
import { TracePanel, ThinkingProcessPanel } from "../trace";
import { useSmoothText } from "../hooks/useSmoothText";

import ChatHeader from "./ChatHeader";
import ChatInput from "./ChatInput";
import WelcomeScreen from "./WelcomeScreen";
import MessageBubble from "./MessageBubble";
import SourceCard from "./SourceCard";

export default function ChatPanel({
  activeSessionId,
  onSessionCreated,
}: {
  activeSessionId: string | null;
  onSessionCreated: (id: string) => void;
}) {
  const {
    currentBookId,
    selectedSource,
    books,
    selectedModel,
    selectedProvider,
    chatMode,
    sessionBookIds,
  } = useAppState();
  const dispatch = useAppDispatch();
  const { user: currentUser } = useAuth();
  const chatHistory = useChatHistoryContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [hasNewMessagesBelow, setHasNewMessagesBelow] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // Token accumulator — ref avoids re-renders per token; RAF batches at 60fps
  const tokenBufferRef = useRef("");
  const rafIdRef = useRef<number | null>(null);

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
  useEffect(() => {
    sessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  /** When history panel selects an old session, restore its messages */
  useEffect(() => {
    if (!activeSessionId) return;
    const session = chatHistory.getSession(activeSessionId);
    if (session && session.messages.length > 0) {
      setMessages(session.messages as Message[]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const thread = threadRef.current;
    if (!thread) return;
    thread.scrollTo({ top: thread.scrollHeight, behavior });
    shouldStickToBottomRef.current = true;
    setIsNearBottom(true);
    setHasNewMessagesBelow(false);
  }, []);

  const updateNearBottom = useCallback(() => {
    const thread = threadRef.current;
    if (!thread) return;
    const distanceFromBottom =
      thread.scrollHeight - thread.scrollTop - thread.clientHeight;
    const nextNearBottom = distanceFromBottom < NEAR_BOTTOM_THRESHOLD;
    shouldStickToBottomRef.current = nextNearBottom;
    setIsNearBottom(nextNearBottom);
    if (nextNearBottom) setHasNewMessagesBelow(false);
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



  /* ── Auto-scroll ── */
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
  }, [hasMessages, loading, messages, smoothedText, scrollToBottom]);

  /* ── Submit question ── */
  const submitQuestion = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      setInput("");
      setError(null);
      shouldStickToBottomRef.current = true;
      setHasNewMessagesBelow(false);
      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      setLoading(true);
      setStreamingContent("");
      tokenBufferRef.current = "";
      setIsStreaming(true);

      // Abort any previous stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      // Create a new history session on the first message of a fresh conversation
      let sessionId = sessionIdRef.current;
      if (!sessionId) {
        const bookTitles = books
          .filter((b) => sessionBookIds.includes(b.id))
          .map((b) => b.title);
        sessionId = chatHistory.createSession({ sessionBookIds, bookTitles, firstMessage: trimmed });
        sessionIdRef.current = sessionId;
        onSessionCreated(sessionId);
      }

      const startTime = Date.now();

      // Map Payload CMS IDs → engine book_id strings for correct filtering
      const engineBookIdStrings = sessionBookIds
        .map((pid) => books.find((b) => b.id === pid)?.book_id)
        .filter((s): s is string => !!s);
      const filters = engineBookIdStrings.length > 0 ? { book_id_strings: engineBookIdStrings } : undefined;

      await queryTextbookStream(
        { question: trimmed, filters, model: selectedModel, provider: selectedProvider, top_k: 5 },
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
          onDone: (res) => {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: res.answer,
                sources: res.sources,
                trace: res.trace,
              },
            ]);
            setStreamingContent("");
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
                { role: "user", content: trimmed },
                { role: "assistant", content: res.answer, sources: res.sources, trace: res.trace },
              ]);
            }

            // Log query to Payload QueryLogs (fire-and-forget)
            const latencyMs = Date.now() - startTime;
            fetch('/api/query-logs', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({
                user: currentUser?.id ?? null,
                question: trimmed,
                answer: res.answer,
                sources: res.sources,
                trace: res.trace,
                model: selectedModel,
                latencyMs,
              }),
            }).catch(() => { /* ignore logging errors */ });
          },
          onError: (err) => {
            setError(err.message);
            tokenBufferRef.current = "";
            if (rafIdRef.current !== null) {
              cancelAnimationFrame(rafIdRef.current);
              rafIdRef.current = null;
            }
            setIsStreaming(false);
            setLoading(false);
          },
        },
      );
    },
    [sessionBookIds, selectedModel, selectedProvider, currentUser, books, chatHistory, onSessionCreated],
  );

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

  const runDemo = useCallback(async () => {
    setError(null);
    setLoading(true);
    shouldStickToBottomRef.current = true;
    setHasNewMessagesBelow(false);
    try {
      const res = await fetchDemo();
      dispatch({ type: "SET_BOOK", bookId: 36 });
      setMessages([
        { role: "user", content: res.trace.question },
        {
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          trace: res.trace,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo failed");
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const selectedSourceLabel = selectedSource
    ? `${selectedSource.chapter_title ?? selectedSource.book_title} | p.${selectedSource.page_number}`
    : null;

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-background">
      {/* ── Header ── */}
      <ChatHeader
        sessionBooks={sessionBooks}
        chatMode={chatMode}
        selectedModel={selectedModel}
        models={models}
        loading={loading}
        selectedSourceLabel={selectedSourceLabel}
        onModeChange={(mode) => dispatch({ type: "SET_CHAT_MODE", mode })}
        onModelChange={(model, provider) => dispatch({ type: "SET_MODEL", model, provider })}
        onNewChat={resetConversation}
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
            onRunDemo={() => void runDemo()}
          />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-3">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className="space-y-2">
                <MessageBubble
                  role={message.role}
                  content={message.content}
                  sources={message.sources}
                  onRetry={message.role === "user" && !loading ? (q) => void submitQuestion(q) : undefined}
                />
                {message.role === "assistant" && message.sources && message.sources.length > 0 && (() => {
                  // Deduplicate sources by citation_index (keep first occurrence)
                  const seen = new Set<number>();
                  const uniqueSources = message.sources.filter((s) => {
                    const ci = (s as any).citation_index as number | undefined;
                    const key = ci ?? -1;
                    if (key !== -1 && seen.has(key)) return false;
                    if (key !== -1) seen.add(key);
                    return true;
                  });
                  return (
                    <div className="ml-11 mt-1 flex flex-wrap gap-2">
                      {uniqueSources.map((s, i) => (
                        <SourceCard
                          key={`src-${index}-${(s as any).citation_index ?? i}`}
                          source={s}
                          index={i}
                          isActive={selectedSource?.source_id === s.source_id}
                        />
                      ))}
                    </div>
                  );
                })()}
                {message.role === "assistant" && chatMode === "trace" && message.trace && (
                  <TracePanel trace={message.trace} />
                )}
                {message.role === "assistant" && message.trace && (
                  <ThinkingProcessPanel trace={message.trace} />
                )}
              </div>
            ))}

            {/* Streaming bubble — shown while tokens arrive */}
            {isStreaming && smoothedText && (
              <div className="space-y-2">
                <MessageBubble
                  role="assistant"
                  content={smoothedText}
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
                      Searching the books…
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
            ↓ Jump to latest
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
