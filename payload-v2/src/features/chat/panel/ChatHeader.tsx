/**
 * ChatHeader — Chat panel top bar with title, model selector, prompt selector,
 * scope indicator, and questions toggle.
 *
 * Usage: <ChatHeader sessionBooks={books} totalBookCount={67} ... />
 */

import { Lightbulb, X } from "lucide-react";
import type { ModelInfo } from "@/features/shared/types";
import type { BookBase } from "@/features/shared/books";
import PromptSelector from "./PromptSelector";

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
  /** Prompt mode selection */
  selectedPromptSlug: string | null;
  onPromptChange: (slug: string, systemPrompt: string) => void;
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
  selectedPromptSlug,
  onPromptChange,
}: ChatHeaderProps) {
  const isScoped = sessionBooks.length < totalBookCount && totalBookCount > 0;

  return (
    <div className="shrink-0 border-b border-border bg-card px-4 py-2.5">
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
          {/* Prompt mode selector */}
          <PromptSelector
            selectedSlug={selectedPromptSlug}
            onSelect={onPromptChange}
          />

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
    </div>
  );
}

