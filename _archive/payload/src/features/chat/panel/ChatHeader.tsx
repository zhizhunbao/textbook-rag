/**
 * panel/ChatHeader.tsx
 * 聊天面板顶栏 — 标题、模式切换、模型选择、新建对话
 */
import type { ModelInfo, BookSummary } from "@/features/shared/types";
import ModeToggle from "./ModeToggle";

interface Props {
  sessionBooks: BookSummary[];
  chatMode: "answer" | "trace";
  selectedModel: string;
  models: ModelInfo[];
  loading: boolean;
  selectedSourceLabel: string | null;
  onModeChange: (mode: "answer" | "trace") => void;
  onModelChange: (model: string, provider?: string) => void;
  onNewChat: () => void;
}

export default function ChatHeader({
  sessionBooks,
  chatMode,
  selectedModel,
  models,
  loading,
  selectedSourceLabel,
  onModeChange,
  onModelChange,
  onNewChat,
}: Props) {
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
              : `${sessionBooks.length} books in session`}
          </p>
        </div>

        {/* Controls */}
        <div className="flex shrink-0 items-center gap-2">
          <ModeToggle
            mode={chatMode}
            onChange={onModeChange}
          />
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

          {/* New Chat */}
          <button
            type="button"
            onClick={onNewChat}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 text-xs font-medium text-foreground transition hover:bg-accent"
            title="Start a new session — choose different books"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            New Chat
          </button>
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
