/**
 * MessageBubble — Chat message bubble for user and AI messages.
 *
 * User messages: rendered as Markdown with KaTeX support.
 * AI messages (streaming): plain text with typing cursor.
 * AI messages (done): delegated to AnswerBlockRenderer for semantic
 *   paragraph rendering with CitationChip/CitationPopover.
 *
 * Usage: <MessageBubble role="assistant" content={text} sources={sources} />
 */

import Markdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import type { SourceInfo } from "@/features/shared/types";
import AnswerBlockRenderer from "./AnswerBlockRenderer";
import { prepareForKatex } from "./textUtils";

// ============================================================
// Types
// ============================================================
interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  onRetry?: (content: string) => void;
  isStreaming?: boolean;
}

// ============================================================
// Helpers
// ============================================================



// ============================================================
// Component
// ============================================================
export default function MessageBubble({ role, content, sources, onRetry, isStreaming }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex items-start gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {/* ── AI avatar ── */}
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
          </svg>
        </div>
      )}

      <div className={`max-w-[86%] ${isUser ? "order-first" : ""}`}>
        <div className={`mb-1 text-[11px] font-medium uppercase tracking-[0.16em] ${isUser ? "text-right text-blue-500" : "text-muted-foreground"}`}>
          {isUser ? "You" : "Textbook RAG"}
        </div>
        <div
          className={`rounded-[22px] px-4 py-3 text-sm shadow-sm ${
            isUser
              ? "rounded-tr-md bg-blue-600 text-white"
              : "rounded-tl-md border border-border bg-card/92 text-card-foreground"
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
              <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[2px] animate-pulse bg-blue-500" />
            </div>
          ) : (
            /* ── Completed AI: semantic AnswerBlocks with citation chips ── */
            <AnswerBlockRenderer content={content} sources={sources} />
          )}
        </div>

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

      {/* ── User avatar ── */}
      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6.75a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.118a7.5 7.5 0 0 1 15 0A17.933 17.933 0 0 1 12 21.75a17.933 17.933 0 0 1-7.5-1.632Z" />
          </svg>
        </div>
      )}
    </div>
  );
}
