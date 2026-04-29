/**
 * panel/ChatInput.tsx
 * 底部输入栏 — 锁定书籍 bar + 检索参数控件 + textarea + 发送按钮
 *
 * Controls exposed to user:
 *   - Retrieval Mode (Standard / Auto / Smart / Deep)
 *   - Top-K (3–20 slider)
 *   - Reranker toggle (LLMRerank on/off)
 *   - Auto-Evaluate toggle (auto-run 4-dim eval after each response)
 */
import { useState, useRef, useEffect, useCallback, type FormEvent, type KeyboardEvent } from "react";
import type { BookBase } from "@/features/shared/books";
import type { RetrievalMode } from "@/features/engine/query_engine/types";
import { useI18n } from "@/features/shared/i18n";
import { tpl } from "@/features/shared/i18n";

// ============================================================
// Types
// ============================================================
interface Props {
  sessionBooks: BookBase[];
  input: string;
  loading: boolean;
  retrievalMode: RetrievalMode;
  topK: number;
  rerankerEnabled: boolean;
  autoEvaluate: boolean;
  onInputChange: (value: string) => void;
  onRetrievalModeChange: (mode: RetrievalMode) => void;
  onTopKChange: (value: number) => void;
  onRerankerChange: (enabled: boolean) => void;
  onAutoEvaluateChange: (enabled: boolean) => void;
  onSubmit: (question: string) => void;
}

// ============================================================
// Toggle Switch — reusable mini toggle
// ============================================================
function MiniToggle({
  enabled,
  onChange,
  disabled,
  label,
  title,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      aria-label={label}
      title={title ?? label}
      disabled={disabled}
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-[18px] w-[32px] shrink-0 items-center rounded-full border transition-colors duration-200 ${
        enabled
          ? "border-primary/40 bg-primary"
          : "border-border bg-muted/80"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <span
        className={`inline-block h-[14px] w-[14px] rounded-full bg-white shadow-sm transition-transform duration-200 ${
          enabled ? "translate-x-[15px]" : "translate-x-[1px]"
        }`}
      />
    </button>
  );
}

// ============================================================
// Component
// ============================================================
export default function ChatInput({
  sessionBooks,
  input,
  loading,
  retrievalMode,
  topK,
  rerankerEnabled,
  autoEvaluate,
  onInputChange,
  onRetrievalModeChange,
  onTopKChange,
  onRerankerChange,
  onAutoEvaluateChange,
  onSubmit,
}: Props) {
  const { t } = useI18n();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showSettings, setShowSettings] = useState(false);

  const resizeTextarea = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(input);
  }

  function handleTextareaKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    if (event.nativeEvent.isComposing) return;
    event.preventDefault();
    onSubmit(input);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="absolute inset-x-0 bottom-0 bg-background px-4 pb-4 pt-3"
    >
      <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-border bg-card shadow-md">
        {/* ── Row 1: Document scope + retrieval mode + settings toggle ── */}
        <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-4 py-2">
          <svg className="h-3.5 w-3.5 shrink-0 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
          {sessionBooks.length <= 5 ? (
            <div className="flex min-w-0 flex-1 flex-wrap gap-1.5">
              {sessionBooks.map((book) => (
                <span
                  key={book.id}
                  className="inline-flex max-w-[200px] items-center truncate rounded-full bg-primary px-2.5 py-0.5 text-[11px] font-medium text-primary-foreground"
                  title={book.title}
                >
                  {book.title}
                </span>
              ))}
            </div>
          ) : (
            <span className="flex-1 text-xs text-muted-foreground">
              {tpl(t.chatSearchAllDocs, { count: sessionBooks.length })}
            </span>
          )}
          <select
            className="h-7 shrink-0 rounded-md border border-border bg-background px-2 text-[11px] font-medium text-foreground outline-none transition focus:border-primary"
            value={retrievalMode}
            onChange={(event) => onRetrievalModeChange(event.target.value as RetrievalMode)}
            disabled={loading}
            title="Retrieval mode"
          >
            <option value="standard">Standard</option>
            <option value="auto">Auto</option>
            <option value="smart">Smart soon</option>
            <option value="deep">Deep soon</option>
          </select>
          {/* Settings gear toggle */}
          <button
            type="button"
            onClick={() => setShowSettings((v) => !v)}
            className={`flex items-center justify-center h-7 w-7 shrink-0 rounded-md border transition-colors ${
              showSettings
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:bg-accent hover:text-foreground"
            }`}
            title={showSettings ? "Hide retrieval settings" : "Show retrieval settings"}
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
          </button>
        </div>

        {/* ── Row 2: Retrieval settings panel (collapsible) ── */}
        {showSettings && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border bg-muted/30 px-4 py-2">
            {/* Top-K */}
            <div className="flex items-center gap-2">
              <label className="text-[11px] font-medium text-muted-foreground whitespace-nowrap" title="Number of document chunks retrieved per query">
                Top-K
              </label>
              <input
                type="range"
                min={3}
                max={20}
                step={1}
                value={topK}
                onChange={(e) => onTopKChange(Number(e.target.value))}
                disabled={loading}
                className="h-1 w-16 cursor-pointer accent-primary"
              />
              <span className="w-5 text-center text-[11px] font-bold tabular-nums text-foreground">
                {topK}
              </span>
            </div>

            {/* Divider */}
            <div className="h-4 w-px bg-border" />

            {/* Reranker toggle */}
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] font-medium text-muted-foreground whitespace-nowrap" title="LLMRerank — re-scores retrieved chunks with LLM for higher precision (uses extra tokens)">
                Reranker
              </label>
              <MiniToggle
                enabled={rerankerEnabled}
                onChange={onRerankerChange}
                disabled={loading}
                label="Enable LLM Reranker"
                title="LLMRerank: re-scores retrieved chunks with LLM for higher precision. Costs extra tokens per query."
              />
              {rerankerEnabled && (
                <span className="text-[9px] font-medium text-amber-500" title="Reranker adds ~1 extra LLM call per query">
                  +tokens
                </span>
              )}
            </div>

            {/* Divider */}
            <div className="h-4 w-px bg-border" />

            {/* Auto-Evaluate toggle */}
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] font-medium text-muted-foreground whitespace-nowrap" title="Automatically evaluate each response (faithfulness, relevancy, accuracy)">
                Auto-Eval
              </label>
              <MiniToggle
                enabled={autoEvaluate}
                onChange={onAutoEvaluateChange}
                disabled={loading}
                label="Auto-evaluate responses"
                title="Auto-Evaluate: automatically runs 4-dimension quality evaluation after each response. Costs extra LLM tokens."
              />
              {autoEvaluate && (
                <span className="text-[9px] font-medium text-amber-500" title="Auto-eval adds ~2 extra LLM calls per response">
                  +tokens
                </span>
              )}
            </div>
          </div>
        )}

        {/* ── Textarea + send ── */}
        <div className="flex items-end gap-3 px-4 py-3">
          <textarea
            ref={textareaRef}
            rows={1}
            className="max-h-[200px] min-h-[28px] flex-1 resize-none border-0 bg-transparent py-0.5 text-sm text-foreground outline-none placeholder:text-muted-foreground"
            placeholder={
              sessionBooks.length === 1
                ? tpl(t.chatPlaceholderSingle, { title: sessionBooks[0].title })
                : t.chatPlaceholderMulti
            }
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={handleTextareaKeyDown}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
            title={t.chatSendTitle}
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
        <div className="px-4 pb-2 text-[11px] text-muted-foreground">
          {t.chatInputHint}
        </div>
      </div>
    </form>
  );
}
