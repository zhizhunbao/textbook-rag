import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { fetchModels, queryTextbook, fetchSuggestions, fetchDemo } from "@/features/shared/api";
import { useAppDispatch, useAppState } from "@/features/shared/AppContext";
import { useAuth } from "@/features/shared/AuthProvider";
import type {
  ModelInfo,
  QueryResponse,
  QueryTrace,
  SourceInfo,
  TraceChunkHit,
} from "@/features/shared/types";
import MessageBubble from "./MessageBubble";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  trace?: QueryTrace;
}

const FALLBACK_SUGGESTIONS = [
  "What are the main topics covered in this book?",
  "What are the prerequisites for this book?",
  "Summarize the most important takeaways.",
  "What practical examples does this book provide?",
];

const NEAR_BOTTOM_THRESHOLD = 160;

const ICONS = [
  <svg key="i0" className="h-4 w-4 text-amber-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M9.75 17.25h4.5M12 3v.75m4.243 1.007-.53.53M20.25 12H21m-3.257 4.243.53.53M3.75 12H3m3.257-4.243-.53-.53M7.757 4.757l-.53-.53" />
  </svg>,
  <svg key="i1" className="h-4 w-4 text-blue-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342" />
  </svg>,
  <svg key="i2" className="h-4 w-4 text-emerald-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
  </svg>,
  <svg key="i3" className="h-4 w-4 text-sky-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
  </svg>,
];

function ThreadStatus({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">{title}</div>
      <div className="mt-1 text-sm text-slate-500">{subtitle}</div>
    </div>
  );
}

function ModeToggle({
  mode,
  onChange,
}: {
  mode: "answer" | "trace";
  onChange: (mode: "answer" | "trace") => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-slate-200 bg-white p-1">
      {(["answer", "trace"] as const).map((option) => {
        const active = mode === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition ${
              active
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {option === "answer" ? "Answer" : "Trace"}
          </button>
        );
      })}
    </div>
  );
}

function formatScore(score: number | null) {
  return score == null ? "n/a" : score.toFixed(4);
}

function TraceStat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "warn";
}) {
  return (
    <div
      className={`rounded-xl border px-3 py-2 ${
        tone === "warn"
          ? "border-amber-200 bg-amber-50"
          : "border-slate-200 bg-white"
      }`}
    >
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">
        {label}
      </div>
      <div className="mt-1 text-sm font-medium text-slate-800">{value}</div>
    </div>
  );
}

function TracePromptBlock({
  title,
  text,
  defaultOpen = false,
}: {
  title: string;
  text: string;
  defaultOpen?: boolean;
}) {
  return (
    <details
      className="rounded-xl border border-slate-200 bg-white"
      open={defaultOpen}
    >
      <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-slate-700">
        <div className="flex items-center justify-between gap-3">
          <span>{title}</span>
          <span className="text-[11px] text-slate-400">{text.length} chars</span>
        </div>
      </summary>
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap border-t border-slate-200 p-3 text-xs leading-5 text-slate-700">
        {text || "(empty)"}
      </pre>
    </details>
  );
}

function TraceHitList({
  title,
  hits,
  emptyLabel,
}: {
  title: string;
  hits: TraceChunkHit[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
      <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
        {title}
      </div>
      {hits.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
          {emptyLabel}
        </div>
      ) : (
        <div className="space-y-2">
          {hits.map((hit) => (
            <div
              key={`${title}-${hit.chunk_id}-${hit.rank}`}
              className="rounded-lg border border-slate-200 bg-white p-2.5"
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                <span className="font-semibold text-slate-700">#{hit.rank}</span>
                <span>{hit.book_title}</span>
                {hit.chapter_title && <span>{hit.chapter_title}</span>}
                {hit.page_number && <span>p.{hit.page_number}</span>}
                <span>score {formatScore(hit.score)}</span>
              </div>
              <div className="mt-1.5 text-sm text-slate-700">{hit.snippet}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TracePanel({ trace }: { trace: QueryTrace }) {
  const ftsCount = trace.retrieval.fts_results.length;
  const vectorCount = trace.retrieval.vector_results.length;
  const pageindexCount = (trace.retrieval.pageindex_results ?? []).length;
  const metadataCount = (trace.retrieval.metadata_results ?? []).length;
  const fusedCount = trace.retrieval.fused_results.length;
  const noContext = fusedCount === 0;
  const filterLines = [
    trace.filters?.book_ids?.length
      ? `book_ids: ${trace.filters.book_ids.join(", ")}`
      : null,
    trace.filters?.chapter_ids?.length
      ? `chapter_ids: ${trace.filters.chapter_ids.join(", ")}`
      : null,
    trace.filters?.content_types?.length
      ? `content_types: ${trace.filters.content_types.join(", ")}`
      : null,
  ].filter(Boolean) as string[];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">
            Execution Trace
          </div>
          <div className="mt-1 text-sm font-medium text-slate-900">
            {noContext
              ? "No retrieval context reached the model."
              : `${fusedCount} context chunks were sent to the model.`}
          </div>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600">
          {trace.generation.model}
        </div>
      </div>

      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-5">
          <TraceStat label="FTS hits" value={String(ftsCount)} tone={ftsCount === 0 ? "warn" : "default"} />
          <TraceStat label="Vector hits" value={String(vectorCount)} tone={vectorCount === 0 ? "warn" : "default"} />
          <TraceStat label="PageIndex hits" value={String(pageindexCount)} tone={pageindexCount === 0 ? "warn" : "default"} />
          <TraceStat label="Metadata hits" value={String(metadataCount)} tone={metadataCount === 0 ? "warn" : "default"} />
          <TraceStat label="Context sent" value={String(fusedCount)} tone={noContext ? "warn" : "default"} />
        </div>

        {noContext && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-900">
            Retrieval returned no usable context. The model answered without textbook evidence, so this result is not useful for optimization until retrieval is fixed.
          </div>
        )}

        <details className="rounded-xl border border-slate-200 bg-slate-50/70" open>
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
            Request
          </summary>
          <div className="space-y-3 border-t border-slate-200 p-3">
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">
                Question
              </div>
              <div>{trace.question}</div>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <TraceStat label="top_k" value={String(trace.top_k)} />
              <TraceStat label="fetch_k" value={String(trace.retrieval.fetch_k)} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <TraceStat
                label="Active book"
                value={trace.active_book_title || "none"}
              />
              <TraceStat
                label="Filters"
                value={filterLines.length > 0 ? filterLines.join(" | ") : "none"}
              />
            </div>
          </div>
        </details>

        <details className="rounded-xl border border-slate-200 bg-slate-50/70" open>
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
            Retrieval
          </summary>
          <div className="space-y-3 border-t border-slate-200 p-3">
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
              <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">
                FTS query
              </div>
              <code className="break-all text-[13px] text-slate-800">
                {trace.retrieval.fts_query || "(empty)"}
              </code>
            </div>
            <div className="space-y-3">
              <TraceHitList
                title="FTS Hits"
                hits={trace.retrieval.fts_results}
                emptyLabel="Keyword search returned no chunks."
              />
              <TraceHitList
                title="Vector Hits"
                hits={trace.retrieval.vector_results}
                emptyLabel="Vector search returned no chunks."
              />
              <TraceHitList
                title="PageIndex Hits"
                hits={trace.retrieval.pageindex_results ?? []}
                emptyLabel="PageIndex tree search returned no chunks."
              />
              <TraceHitList
                title="Metadata Hits"
                hits={trace.retrieval.metadata_results ?? []}
                emptyLabel="Metadata filter returned no chunks."
              />
              <TraceHitList
                title="Fused Context Sent To LLM"
                hits={trace.retrieval.fused_results}
                emptyLabel="RRF produced no context to send to the model."
              />
            </div>
          </div>
        </details>

        <details className="rounded-xl border border-slate-200 bg-slate-50/70">
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
            Generation
          </summary>
          <div className="space-y-3 border-t border-slate-200 p-3">
            <div className="grid gap-2 md:grid-cols-2">
              <TraceStat label="Model" value={trace.generation.model} />
              <TraceStat
                label="Prompt context"
                value={noContext ? "empty" : `${fusedCount} chunks attached`}
                tone={noContext ? "warn" : "default"}
              />
            </div>
            <TracePromptBlock title="System prompt" text={trace.generation.system_prompt} />
            <TracePromptBlock
              title="User prompt"
              text={trace.generation.user_prompt}
              defaultOpen={noContext}
            />
          </div>
        </details>
      </div>
    </div>
  );
}

/* ── Thinking Process Panel (collapsible, always visible) ── */

const STRATEGY_META: Record<string, { label: string; color: string; desc: string }> = {
  fts:       { label: "FTS5 (BM25)",         color: "text-amber-600 bg-amber-50 border-amber-200",  desc: "Full-text keyword search using SQLite FTS5 with BM25 ranking" },
  vector:    { label: "Vector (Embedding)",   color: "text-blue-600 bg-blue-50 border-blue-200",    desc: "Semantic similarity search via ChromaDB embeddings" },
  pageindex: { label: "PageIndex (Tree)",     color: "text-emerald-600 bg-emerald-50 border-emerald-200", desc: "Hierarchical TOC tree traversal with LLM-guided selection" },
  metadata:  { label: "Metadata Filter",      color: "text-purple-600 bg-purple-50 border-purple-200",   desc: "Chapter & content-type metadata matching" },
};

function ThinkingProcessPanel({ trace }: { trace: QueryTrace }) {
  const strategies = [
    { key: "fts",       hits: trace.retrieval.fts_results },
    { key: "vector",    hits: trace.retrieval.vector_results },
    { key: "pageindex", hits: trace.retrieval.pageindex_results ?? [] },
    { key: "metadata",  hits: trace.retrieval.metadata_results ?? [] },
  ];
  const fusedCount = trace.retrieval.fused_results.length;

  return (
    <details className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-slate-700 select-none">
        <svg className="h-4 w-4 text-slate-400 transition-transform [[open]>&]:rotate-90" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="m9 5 7 7-7 7" />
        </svg>
        <span>Thinking Process</span>
        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
          4 strategies → {fusedCount} fused chunks
        </span>
      </summary>

      <div className="space-y-4 border-t border-slate-200 p-4">
        {/* Step 1: Query Analysis */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">1</span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Query Analysis</span>
          </div>
          <div className="ml-7 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-400">Generated FTS Query</div>
            <code className="text-sm text-slate-800">{trace.retrieval.fts_query}</code>
          </div>
        </div>

        {/* Step 2: Multi-Strategy Retrieval */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">2</span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Multi-Strategy Retrieval</span>
          </div>
          <div className="ml-7 grid gap-2 md:grid-cols-2">
            {strategies.map(({ key, hits }) => {
              const meta = STRATEGY_META[key];
              return (
                <div key={key} className={`rounded-lg border p-3 ${meta.color}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{meta.label}</span>
                    <span className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-bold">
                      {hits.length} hits
                    </span>
                  </div>
                  <div className="mt-1 text-[11px] opacity-75">{meta.desc}</div>
                  {hits.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {hits.map((hit) => (
                        <div key={`${key}-${hit.chunk_id}-${hit.rank}`} className="flex items-center justify-between rounded bg-white/60 px-2 py-1 text-[11px]">
                          <span className="truncate">p.{hit.page_number} — {hit.snippet.slice(0, 50)}…</span>
                          <span className="ml-2 shrink-0 font-mono font-semibold">
                            {hit.score != null ? hit.score.toFixed(3) : "n/a"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Step 3: RRF Fusion */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">3</span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">RRF Fusion</span>
            <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold text-green-700">Best {fusedCount} selected</span>
          </div>
          <div className="ml-7 space-y-1">
            {trace.retrieval.fused_results.map((hit) => (
              <div key={`fused-${hit.chunk_id}-${hit.rank}`} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">
                  {hit.rank}
                </span>
                <span className="min-w-0 flex-1 truncate text-slate-700">
                  p.{hit.page_number} — {hit.snippet.slice(0, 80)}…
                </span>
                <span className="shrink-0 font-mono text-xs font-semibold text-slate-500">
                  {hit.score != null ? hit.score.toFixed(4) : "n/a"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Step 4: Generation */}
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">4</span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Answer Generation</span>
          </div>
          <div className="ml-7 flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-700">{trace.generation.model}</span>
            <span>{fusedCount} context chunks → structured answer with citations</span>
          </div>
        </div>
      </div>
    </details>
  );
}

export default function ChatPanel() {
  const {
    currentBookId,
    selectedSource,
    books,
    selectedModel,
    chatMode,
  } = useAppState();
  const dispatch = useAppDispatch();
  const { user: currentUser } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [hasNewMessagesBelow, setHasNewMessagesBelow] = useState(false);

  const threadRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const shouldStickToBottomRef = useRef(true);

  const currentBook = books.find((b) => b.id === currentBookId);
  const hasMessages = messages.length > 0;

  const resizeTextarea = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, []);

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

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  useEffect(() => {
    fetchModels()
      .then((availableModels) => {
        setModels(availableModels);
        if (
          availableModels.length > 0 &&
          !availableModels.some((model) => model.name === selectedModel)
        ) {
          const preferred =
            availableModels.find((model) => model.is_default) ?? availableModels[0];
          dispatch({ type: "SET_MODEL", model: preferred.name });
        }
      })
      .catch(() => setModels([]));
  }, [dispatch, selectedModel]);

  useEffect(() => {
    if (!currentBookId) {
      setSuggestions(FALLBACK_SUGGESTIONS);
      return;
    }

    fetchSuggestions(currentBookId)
      .then((nextSuggestions) =>
        setSuggestions(nextSuggestions.length ? nextSuggestions : FALLBACK_SUGGESTIONS),
      )
      .catch(() => setSuggestions(FALLBACK_SUGGESTIONS));
  }, [currentBookId]);

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

      const startTime = Date.now();

      try {
        const filters = currentBookId ? { book_ids: [currentBookId] } : undefined;
        const res: QueryResponse = await queryTextbook({
          question: trimmed,
          filters,
          model: selectedModel,
          top_k: 5,
        });

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: res.answer,
            sources: res.sources,
            trace: res.trace,
          },
        ]);

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
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    [currentBookId, selectedModel, currentUser],
  );

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submitQuestion(input);
  }

  function handleTextareaKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    if (event.nativeEvent.isComposing) return;
    event.preventDefault();
    void submitQuestion(input);
  }

  const resetConversation = useCallback(() => {
    setMessages([]);
    setInput("");
    setLoading(false);
    setError(null);
    setHasNewMessagesBelow(false);
    setIsNearBottom(true);
    shouldStickToBottomRef.current = true;
    dispatch({ type: "SELECT_SOURCE", source: null });
    scrollToBottom("auto");
  }, [dispatch, scrollToBottom]);

  const runDemo = useCallback(async () => {
    setError(null);
    setLoading(true);
    shouldStickToBottomRef.current = true;
    setHasNewMessagesBelow(false);
    try {
      const res = await fetchDemo();
      // Switch to HTTP book (id=24)
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
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-[#f5f7fb]">
      <div className="border-b border-slate-200 bg-[#f8fafc] px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {hasMessages && (
                <button
                  type="button"
                  onClick={resetConversation}
                  className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                  title="Back to chat start"
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m15 18-6-6 6-6" />
                  </svg>
                  <span>Back</span>
                </button>
              )}
              <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              <h2 className="truncate text-sm font-semibold text-slate-900">
                {currentBook ? currentBook.title : "Textbook RAG"}
              </h2>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {currentBook
                ? `${currentBook.page_count} pages | ${currentBook.chapter_count} chapters`
                : "Select a textbook to start a conversation"}
            </p>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <ModeToggle
            mode={chatMode}
            onChange={(mode) => dispatch({ type: "SET_CHAT_MODE", mode })}
          />
          <label className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">
            <span>Model</span>
            <select
              className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-[12px] font-medium normal-case tracking-normal text-slate-700 outline-none transition focus:border-slate-300"
              value={selectedModel}
              onChange={(event) =>
                dispatch({ type: "SET_MODEL", model: event.target.value })
              }
              disabled={loading || models.length === 0}
              suppressHydrationWarning
            >
              {models.length === 0 ? (
                <option value={selectedModel} suppressHydrationWarning>{selectedModel}</option>
              ) : (
                models.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name}
                    {model.is_default ? " (default)" : ""}
                  </option>
                ))
              )}
            </select>
          </label>
        </div>

        {selectedSourceLabel && (
          <div className="mt-3 inline-flex max-w-full items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-600">
            <svg className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m0 0 4-4m-4 4-4-4" />
            </svg>
            <span className="truncate">Focused source: {selectedSourceLabel}</span>
          </div>
        )}
      </div>

      <div
        ref={threadRef}
        className="chat-thread relative flex-1 overflow-y-auto px-4 pb-40 pt-4"
        onScroll={updateNearBottom}
      >
        {!hasMessages && !loading ? (
          <div className="mx-auto flex max-w-3xl flex-col gap-4 py-6">
            <ThreadStatus
              title={currentBook ? currentBook.title : "Textbook RAG"}
              subtitle={
                currentBook
                  ? "Ask normally, or switch to Trace to inspect retrieval and prompt construction."
                  : "Choose a textbook first, then start asking questions."
              }
            />

            <div className="grid gap-2 md:grid-cols-2">
              {suggestions.map((question, index) => (
                <button
                  key={question}
                  onClick={() => void submitQuestion(question)}
                  className="group rounded-xl border border-slate-200 bg-white px-3 py-3 text-left transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 shrink-0 rounded-md bg-slate-100 p-2">
                      {ICONS[index % ICONS.length]}
                    </span>
                    <div className="text-sm text-slate-700 group-hover:text-slate-900">
                      {question}
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {/* Demo button */}
            <button
              type="button"
              onClick={() => void runDemo()}
              disabled={loading}
              className="group mx-auto flex items-center gap-2 rounded-xl border-2 border-dashed border-indigo-300 bg-indigo-50/50 px-5 py-3 text-sm font-medium text-indigo-600 transition hover:border-indigo-400 hover:bg-indigo-50 disabled:opacity-50"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
              </svg>
              Demo: FastAPI Dependency Injection
            </button>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-3">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className="space-y-2">
                <MessageBubble
                  role={message.role}
                  content={message.content}
                  sources={message.sources}
                />
                {message.role === "assistant" && chatMode === "trace" && message.trace && (
                  <TracePanel trace={message.trace} />
                )}
                {message.role === "assistant" && message.trace && (
                  <ThinkingProcessPanel trace={message.trace} />
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-start gap-3">
                <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 shadow-sm">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
                  </svg>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
                    </div>
                    <span className="text-sm text-slate-500">
                      Searching the book and drafting an answer...
                    </span>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-sm">
                {error}
              </div>
            )}
          </div>
        )}
      </div>

      {hasNewMessagesBelow && !isNearBottom && (
        <div className="pointer-events-none absolute inset-x-0 bottom-40 flex justify-center px-4">
          <button
            type="button"
            onClick={() => scrollToBottom("smooth")}
            className="pointer-events-auto rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            Jump to latest
          </button>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="absolute inset-x-0 bottom-0 border-t border-slate-200 bg-[#f8fafc] px-4 pb-4 pt-3"
      >
        <div className="mx-auto max-w-3xl rounded-2xl border border-slate-300 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">
            Message
          </div>
          <div className="flex items-end gap-3 px-4 py-3">
            <div className="flex-1">
              <textarea
                ref={textareaRef}
                rows={1}
                className="max-h-[200px] min-h-[28px] w-full resize-none border-0 bg-transparent px-0 py-0.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                placeholder={
                  currentBook
                    ? `Ask about ${currentBook.title}...`
                    : "Select a textbook, then ask a question..."
                }
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleTextareaKeyDown}
                disabled={loading}
              />
              <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-slate-400">
                <span>
                  {currentBook
                    ? "Grounded answers use the selected textbook only."
                    : "Pick a book to enable retrieval."}
                </span>
                <span>Enter to send | Shift+Enter for line breaks</span>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-900 bg-slate-900 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-400"
              title="Send message"
            >
              {loading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/80 border-t-transparent" />
              ) : (
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.906 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
