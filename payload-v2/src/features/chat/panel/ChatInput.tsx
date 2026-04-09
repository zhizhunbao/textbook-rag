/**
 * panel/ChatInput.tsx
 * 底部输入栏 — 锁定书籍 bar + textarea + 发送按钮
 */
import { useRef, useEffect, useCallback, type FormEvent, type KeyboardEvent } from "react";
import type { BookBase } from "@/features/shared/books";

interface Props {
  sessionBooks: BookBase[];
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (question: string) => void;
}

export default function ChatInput({
  sessionBooks,
  input,
  loading,
  onInputChange,
  onSubmit,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
        {/* Document scope indicator */}
        <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-4 py-2">
          <svg className="h-3.5 w-3.5 shrink-0 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
          {sessionBooks.length <= 5 ? (
            /* Show individual book pills only for small selections */
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
            /* All-books mode: clean single-line indicator */
            <span className="text-xs text-muted-foreground">
              Searching all {sessionBooks.length} documents
            </span>
          )}
        </div>

        {/* Textarea + send */}
        <div className="flex items-end gap-3 px-4 py-3">
          <textarea
            ref={textareaRef}
            rows={1}
            className="max-h-[200px] min-h-[28px] flex-1 resize-none border-0 bg-transparent py-0.5 text-sm text-foreground outline-none placeholder:text-muted-foreground"
            placeholder={
              sessionBooks.length === 1
                ? `Ask about ${sessionBooks[0].title}...`
                : "Ask about Ottawa economic data..."
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
            title="Send message (Enter)"
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
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </form>
  );
}
