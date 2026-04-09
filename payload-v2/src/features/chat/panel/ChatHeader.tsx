/**
 * ChatHeader — Chat panel top bar with title, model selector, and questions toggle.
 *
 * Usage: <ChatHeader sessionBooks={books} selectedModel={model} ... />
 */

import { Lightbulb } from "lucide-react";
import type { ModelInfo } from "@/features/shared/types";
import type { BookBase } from "@/features/shared/books";

// ============================================================
// Types
// ============================================================
interface ChatHeaderProps {
  sessionBooks: BookBase[];
  selectedModel: string;
  models: ModelInfo[];
  loading: boolean;
  selectedSourceLabel: string | null;
  onModelChange: (model: string, provider?: string) => void;
  onNewChat: () => void;
  /** Questions sidebar toggle */
  showQuestions?: boolean;
  onToggleQuestions?: () => void;
}

// ============================================================
// Component
// ============================================================
export default function ChatHeader({
  sessionBooks,
  selectedModel,
  models,
  loading,
  selectedSourceLabel,
  onModelChange,
  onNewChat,
  showQuestions,
  onToggleQuestions,
}: ChatHeaderProps) {
  return (
    <div className="shrink-0 border-b border-border bg-card px-4 py-2.5">
      <div className="flex items-center gap-3">
        {/* Bot avatar */}
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
          </svg>
        </div>

        {/* Title */}
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-foreground">Textbook RAG</h2>
          <p className="text-[11px] text-muted-foreground">
            {sessionBooks.length === 1
              ? sessionBooks[0].title
              : `Searching all ${sessionBooks.length} documents`}
          </p>
        </div>

        {/* Controls */}
        <div className="flex shrink-0 items-center gap-2">
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

      {selectedSourceLabel && (
        <div className="mt-2 inline-flex max-w-full items-center gap-2 rounded-md border border-border bg-muted/50 px-3 py-1.5 text-[11px] text-muted-foreground">
          <svg className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
          </svg>
          <span className="truncate">{selectedSourceLabel}</span>
        </div>
      )}
    </div>
  );
}
