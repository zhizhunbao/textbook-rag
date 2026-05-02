/**
 * MessageBubble — Chat message bubble for user and AI messages.
 *
 * User messages: rendered as Markdown with KaTeX support.
 * AI messages (streaming): plain text with typing cursor.
 * AI messages (done): delegated to AnswerBlockRenderer for semantic
 *   paragraph rendering with CitationChip/CitationPopover.
 *
 * Inline evaluation (EV2-T5 + UEP-T3):
 *   When queryId is present, renders an "Evaluate" button in the
 *   assistant message footer. Clicking triggers the history-based
 *   evaluation endpoint and renders scores inline.
 *   Dual-view mode (UEP-T3-02): user-friendly InlineEvalCard (default)
 *   vs developer EvalScoreCard, toggled with localStorage persistence.
 *
 * Usage: <MessageBubble role="assistant" content={text} sources={sources} queryId={42} />
 */

import { useState, useCallback, useEffect } from "react";
import Markdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import type { SourceInfo } from "@/features/shared/types";
import type { EvaluationResult } from "@/features/engine/evaluation/types";
import type { LlmTelemetry } from "@/features/engine/query_engine/types";
import { evaluateFromHistory, fetchEvaluations } from "@/features/engine/evaluation/api";
import EvalScoreCard from "@/features/engine/evaluation/components/EvalScoreCard";
import InlineEvalCard from "./InlineEvalCard";
import AnswerBlockRenderer from "./AnswerBlockRenderer";
import { prepareForKatex } from "./textUtils";

// ============================================================
// SVG Icons
// ============================================================

/** Gauge / speedometer icon for "Evaluate" */
function IconGauge({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12Z" stroke="currentColor" strokeWidth="1.3" />
      <path d="M8 5v3l2 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="1" fill="currentColor" />
    </svg>
  );
}

/** Spinner icon for loading state */
function IconSpinner({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg className={`${className} animate-spin`} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.25" />
      <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/** User silhouette icon for user view mode. */
function IconUser({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M3 14c0-2.5 2.2-4.5 5-4.5s5 2 5 4.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

/** Wrench icon for developer view mode. */
function IconWrench({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10.5 2.5a3.5 3.5 0 0 0-3.2 4.9L3 11.7l1.3 1.3 4.3-4.3a3.5 3.5 0 0 0 4.9-3.2l-2 2-1.5-.5-.5-1.5 2-2Z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ============================================================
// Eval view mode — persisted to localStorage (UEP-T3-02)
// ============================================================
type EvalViewMode = 'user' | 'dev'
const EVAL_VIEW_KEY = 'eval-view-mode'

function getInitialViewMode(): EvalViewMode {
  if (typeof window === 'undefined') return 'user'
  const stored = localStorage.getItem(EVAL_VIEW_KEY)
  return stored === 'dev' ? 'dev' : 'user'
}

// ============================================================
// Types
// ============================================================
interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  /** LLM model name (assistant messages only). */
  model?: string;
  /** Payload Queries record ID for inline evaluation. */
  queryId?: number;
  /** ISO 8601 timestamp of when the message was created. */
  timestamp?: string;
  /** LLM token usage telemetry (assistant messages only). */
  telemetry?: LlmTelemetry;
  onRetry?: (content: string) => void;
  isStreaming?: boolean;
}

// ============================================================
// Helpers
// ============================================================



// ============================================================
// Component
// ============================================================
export default function MessageBubble({ role, content, sources, model, queryId, timestamp, telemetry, onRetry, isStreaming }: Props) {
  const isUser = role === "user";

  // ── Inline evaluation state ──────────────────────────────
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [showEval, setShowEval] = useState(false);
  const [evalViewMode, setEvalViewMode] = useState<EvalViewMode>(getInitialViewMode);

  // Auto-load existing evaluation on mount (show Scores button if already evaluated)
  useEffect(() => {
    if (!queryId || isStreaming) return;
    let cancelled = false;
    fetchEvaluations({ queryRef: queryId, limit: 1 })
      .then((res) => {
        if (cancelled) return;
        if (res.evaluations.length > 0) {
          setEvalResult(res.evaluations[0]);
        }
      })
      .catch(() => { /* ignore */ });
    return () => { cancelled = true; };
  }, [queryId, isStreaming]);

  const handleEvaluate = useCallback(async () => {
    if (!queryId) return;
    setEvalLoading(true);
    setEvalError(null);

    try {
      // First check if evaluation already exists for this query
      const existing = await fetchEvaluations({ queryRef: queryId, limit: 1 });
      if (existing.evaluations.length > 0) {
        setEvalResult(existing.evaluations[0]);
        setShowEval(true);
        setEvalLoading(false);
        return;
      }

      // Trigger new evaluation
      await evaluateFromHistory(queryId);

      // Fetch the saved evaluation result
      // Small delay to let Payload persist
      await new Promise((r) => setTimeout(r, 800));
      const fresh = await fetchEvaluations({ queryRef: queryId, limit: 1 });
      if (fresh.evaluations.length > 0) {
        setEvalResult(fresh.evaluations[0]);
        setShowEval(true);
      } else {
        setEvalError("Evaluation completed but result not found.");
      }
    } catch (err: any) {
      setEvalError(err?.message || "Evaluation failed");
    } finally {
      setEvalLoading(false);
    }
  }, [queryId]);

  /** Whether the loaded evaluation has incomplete core scores (RAG/LLM/Answer all missing). */
  const isIncomplete = evalResult && (
    evalResult.faithfulness == null &&
    evalResult.ragScore == null &&
    evalResult.answerRelevancy == null
  );

  /** Force re-run evaluation even if one already exists. */
  const handleReEvaluate = useCallback(async () => {
    if (!queryId) return;
    setEvalLoading(true);
    setEvalError(null);
    setShowEval(true);
    setEvalResult(null);

    try {
      await evaluateFromHistory(queryId);
      await new Promise((r) => setTimeout(r, 800));
      const fresh = await fetchEvaluations({ queryRef: queryId, limit: 1 });
      if (fresh.evaluations.length > 0) {
        setEvalResult(fresh.evaluations[0]);
      } else {
        setEvalError("Re-evaluation completed but result not found.");
      }
    } catch (err: any) {
      setEvalError(err?.message || "Re-evaluation failed");
    } finally {
      setEvalLoading(false);
    }
  }, [queryId]);

  return (
    <div className={`flex items-start ${isUser ? "justify-end" : "justify-start"}`}>


      <div className="max-w-[86%]">
        {/* Header: timestamp + model badge (no role label — alignment indicates sender) */}
        {(!isUser || timestamp) && (
          <div className={`mb-1 flex items-center gap-2 text-[11px] ${isUser ? "justify-end" : ""}`}>
            {timestamp && (
              <span className="text-[10px] font-normal normal-case tracking-normal text-muted-foreground/50" title={timestamp}>
                {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            {!isUser && model && (
              <span className="rounded-md bg-muted/60 px-1.5 py-0.5 text-[10px] font-normal normal-case tracking-normal text-muted-foreground/70">
                {model}
              </span>
            )}
          </div>
        )}

        {/* ── LLM telemetry (token usage) ── */}
        {!isUser && telemetry && !isStreaming && (
          <div className="mb-1 flex items-center gap-2 text-[10px] text-muted-foreground/50">
            {telemetry.llm_calls > 0 && (
              <span className="inline-flex items-center gap-0.5" title="Number of LLM API calls">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" /></svg>
                {telemetry.llm_calls} call{telemetry.llm_calls > 1 ? 's' : ''}
              </span>
            )}
            {telemetry.input_tokens > 0 && (
              <span className="inline-flex items-center gap-0.5" title="Estimated input tokens (question + context)">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
                ~{telemetry.input_tokens.toLocaleString()} in
              </span>
            )}
            {telemetry.output_tokens > 0 && (
              <span className="inline-flex items-center gap-0.5" title="Output tokens generated">
                <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg>
                {telemetry.output_tokens.toLocaleString()} out
              </span>
            )}
          </div>
        )}
        <div
          className={`text-sm ${
            isUser
              ? "rounded-[22px] rounded-tr-md border border-primary/20 bg-primary/10 px-4 py-3 shadow-sm text-foreground"
              : "text-card-foreground"
          }`}
        >
          {isUser ? (
            /* ── User message: Markdown + KaTeX ── */
            <div className="leading-6 [&_p]:my-0.5 [&_.katex]:text-[0.95em]">
              <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                {prepareForKatex(content)}
              </Markdown>
            </div>
          ) : isStreaming ? (
            /* ── Streaming: plain text with typing cursor ── */
            <div className="whitespace-pre-wrap leading-7 text-foreground">
              {content}
              <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[2px] animate-pulse bg-primary" />
            </div>
          ) : (
            /* ── Completed AI: semantic AnswerBlocks with citation chips ── */
            <AnswerBlockRenderer content={content} sources={sources} />
          )}
        </div>

        {/* ── Assistant message footer: evaluate button + score card ── */}
        {!isUser && !isStreaming && queryId && (
          <div className="mt-2 space-y-2">
            {/* Action bar */}
            <div className="flex items-center gap-1.5">

              {/* Evaluate button — shown when no eval result exists yet */}
              {!evalResult && !evalLoading && (
                <button
                  type="button"
                  onClick={handleEvaluate}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary transition-all duration-150 hover:bg-primary/20"
                  title="Evaluate this response"
                >
                  <IconGauge className="h-3 w-3" />
                  <span>Evaluate</span>
                </button>
              )}

              {/* Loading spinner while evaluating */}
              {evalLoading && (
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-border/50 bg-card/60 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                  <IconSpinner className="h-3 w-3" />
                  <span>Evaluating…</span>
                </span>
              )}

              {/* Toggle eval scores visibility (when already evaluated) */}
              {evalResult && (
                <button
                  type="button"
                  onClick={() => setShowEval((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary transition-all duration-150 hover:bg-primary/15"
                  title="Toggle evaluation scores"
                >
                  <IconGauge className="h-3 w-3" />
                  <span>Scores</span>
                  <svg
                    className={`h-2.5 w-2.5 transition-transform duration-150 ${showEval ? "rotate-180" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}



              {/* Re-evaluate button — shown when existing eval has incomplete scores */}
              {evalResult && isIncomplete && !evalLoading && (
                <button
                  type="button"
                  onClick={handleReEvaluate}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/40 bg-amber-400/10 px-2.5 py-1 text-[11px] font-medium text-amber-600 transition-all duration-150 hover:bg-amber-400/20 hover:border-amber-400/60"
                  title="Re-run evaluation (previous scores incomplete)"
                >
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
                  </svg>
                  <span>Re-evaluate</span>
                </button>
              )}
            </div>

            {/* Inline evaluation score card */}
            {showEval && (
              <div className="rounded-xl border border-border/40 bg-card/50 p-3 animate-in slide-in-from-top-2 fade-in duration-200">
                {evalError && (
                  <div className="text-xs text-destructive">{evalError}</div>
                )}
                {evalResult && (
                  <EvalScoreCard evaluation={evalResult} locale="en" />
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Retry button for user messages ── */}
        {isUser && onRetry && (
          <div className="mt-1 flex justify-end">
            <button
              type="button"
              onClick={() => onRetry(content)}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              title="Re-ask this question"
            >
              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
              </svg>
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
