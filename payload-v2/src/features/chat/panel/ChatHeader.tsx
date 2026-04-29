/**
 * ChatHeader — Chat panel top bar with title, model selector, prompt selector,
 * scope indicator, questions toggle, and retrieval settings (Reranker / Top-K / Auto-Eval).
 *
 * Usage: <ChatHeader sessionBooks={books} totalBookCount={67} ... />
 */

import { Lightbulb, X } from "lucide-react";
import type { ModelInfo } from "@/features/shared/types";
import type { BookBase } from "@/features/shared/books";
import type { PersonaInfo } from "@/features/shared/consultingApi";
import type { ChatMode } from "../history/api";
import PromptSelector from "./PromptSelector";

// ============================================================
// Mini Toggle — compact switch for boolean settings
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
// Types
// ============================================================
interface ChatHeaderProps {
  sessionBooks: BookBase[];
  /** Total indexed book count — used to detect "scoped" vs "all" mode. */
  totalBookCount: number;
  selectedModel: string;
  models: ModelInfo[];
  loading: boolean;
  onModelChange: (model: string, provider?: string) => void;
  onNewChat: () => void;
  /** Clear book scope — search all documents again. */
  onClearScope?: () => void;
  /** Questions sidebar toggle */
  showQuestions?: boolean;
  onToggleQuestions?: () => void;
  mode: ChatMode;
  personas: PersonaInfo[];
  selectedPersonaSlug: string | null;
  modeLocked: boolean;
  onModeChange: (mode: ChatMode) => void;
  onPersonaChange: (slug: string) => void;
  /** Prompt mode selection */
  selectedPromptSlug: string | null;
  onPromptChange: (slug: string, systemPrompt: string) => void;
  /** Retrieval settings */
  topK: number;
  rerankerEnabled: boolean;
  autoEvaluate: boolean;
  onTopKChange: (value: number) => void;
  onRerankerChange: (enabled: boolean) => void;
  onAutoEvaluateChange: (enabled: boolean) => void;
}

// ============================================================
// Component
// ============================================================
export default function ChatHeader({
  sessionBooks,
  totalBookCount,
  selectedModel,
  models,
  loading,
  onModelChange,
  onNewChat,
  onClearScope,
  showQuestions,
  onToggleQuestions,
  mode,
  personas,
  selectedPersonaSlug,
  modeLocked,
  onModeChange,
  onPersonaChange,
  selectedPromptSlug,
  onPromptChange,
  topK,
  rerankerEnabled,
  autoEvaluate,
  onTopKChange,
  onRerankerChange,
  onAutoEvaluateChange,
}: ChatHeaderProps) {
  const isScoped = sessionBooks.length < totalBookCount && totalBookCount > 0;

  return (
    <div className="shrink-0 border-b border-border bg-card px-4 py-2.5">
      {/* ── Row 1: Title + selectors ── */}
      <div className="flex items-center gap-3">
        {/* Title + scope indicator */}
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-foreground">EcDev Research</h2>
          <div className="flex items-center gap-1.5">
            {isScoped ? (
              <>
                <span className="text-[11px] text-primary font-medium">
                  {sessionBooks.length === 1
                    ? sessionBooks[0].title
                    : `Searching ${sessionBooks.length} of ${totalBookCount} documents`}
                </span>
                {onClearScope && (
                  <button
                    type="button"
                    onClick={onClearScope}
                    className="flex items-center gap-0.5 text-[10px] text-muted-foreground hover:text-foreground bg-muted hover:bg-muted-foreground/20 rounded px-1.5 py-0.5 transition-colors"
                    title="Search all documents"
                  >
                    <X className="h-2.5 w-2.5" />
                    <span>All</span>
                  </button>
                )}
              </>
            ) : (
              <p className="text-[11px] text-muted-foreground">
                {`Searching all ${sessionBooks.length} documents`}
              </p>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex shrink-0 items-center gap-2">
          <select
            className="rounded-md border border-border bg-background px-2 py-1.5 text-[12px] font-medium text-foreground outline-none transition focus:border-primary"
            value={mode}
            onChange={(event) => onModeChange(event.target.value as ChatMode)}
            disabled={loading || modeLocked}
            title={modeLocked ? "Mode is locked for this conversation" : "Chat mode"}
          >
            <option value="rag">RAG</option>
            <option value="consulting">Consulting</option>
          </select>

          {mode === "consulting" && (
            <select
              className="max-w-[180px] rounded-md border border-border bg-background px-2 py-1.5 text-[12px] font-medium text-foreground outline-none transition focus:border-primary"
              value={selectedPersonaSlug ?? ""}
              onChange={(event) => onPersonaChange(event.target.value)}
              disabled={loading || modeLocked || personas.length === 0}
              title={modeLocked ? "Persona is locked for this conversation" : "Consulting persona"}
            >
              {personas.length === 0 ? (
                <option value="">No personas</option>
              ) : (
                personas.map((persona) => (
                  <option key={persona.slug} value={persona.slug}>
                    {persona.name}
                  </option>
                ))
              )}
            </select>
          )}

          {/* Prompt mode selector */}
          {mode === "rag" && (
            <PromptSelector
              selectedSlug={selectedPromptSlug}
              onSelect={onPromptChange}
            />
          )}

          {/* Model selector */}
          <select
            className="rounded-md border border-border bg-background px-2 py-1.5 text-[12px] font-medium text-foreground outline-none transition focus:border-primary"
            value={selectedModel}
            onChange={(event) => {
              const name = event.target.value;
              const found = models.find((m) => m.name === name);
              onModelChange(name, found?.provider);
            }}
            disabled={loading || models.length === 0}
            suppressHydrationWarning
          >
            {models.length === 0 ? (
              <option value={selectedModel} suppressHydrationWarning>{selectedModel}</option>
            ) : (
              models.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name}
                  {model.is_default ? " ✦" : ""}
                </option>
              ))
            )}
          </select>

          {/* Questions sidebar toggle — hidden when sidebar is open (it has its own close button) */}
          {onToggleQuestions && !showQuestions && (
            <button
              type="button"
              onClick={onToggleQuestions}
              className={`flex items-center justify-center h-8 w-8 rounded-lg border transition-colors ${
                showQuestions
                  ? 'bg-primary/10 text-primary border-primary/30'
                  : 'border-border text-muted-foreground hover:bg-accent'
              }`}
              title={showQuestions ? 'Hide questions' : 'Show suggested questions'}
            >
              <Lightbulb size={16} />
            </button>
          )}
        </div>
      </div>

      {/* ── Row 2: Retrieval settings — flat controls ── */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-border/50 pt-2">
        {/* Top-K */}
        <div className="flex items-center gap-1.5">
          <label
            className="text-[11px] font-medium text-muted-foreground whitespace-nowrap"
            title="Number of document chunks retrieved per query"
          >
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
        <div className="h-4 w-px bg-border/60" />

        {/* Reranker toggle */}
        <div className="flex items-center gap-1.5">
          <label
            className="text-[11px] font-medium text-muted-foreground whitespace-nowrap"
            title="LLMRerank — re-scores retrieved chunks with LLM for higher precision (uses extra tokens)"
          >
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
        <div className="h-4 w-px bg-border/60" />

        {/* Auto-Evaluate toggle */}
        <div className="flex items-center gap-1.5">
          <label
            className="text-[11px] font-medium text-muted-foreground whitespace-nowrap"
            title="Automatically evaluate each response (faithfulness, relevancy, accuracy)"
          >
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
    </div>
  );
}
