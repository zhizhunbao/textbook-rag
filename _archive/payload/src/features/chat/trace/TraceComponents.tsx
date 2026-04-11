/**
 * trace/TraceComponents.tsx
 * 小型可复用的 trace UI 组件：TraceStat / TracePromptBlock / TraceHitList
 */
import type { TraceChunkHit } from "@/features/shared/types";

/* ── helpers ── */
export function formatScore(score: number | null) {
  return score == null ? "n/a" : score.toFixed(4);
}

/* ── TraceStat ── */
export function TraceStat({
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
          ? "border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-500"
          : "border-border bg-card"
      }`}
    >
      <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-sm font-medium text-foreground">{value}</div>
    </div>
  );
}

/* ── TracePromptBlock ── */
export function TracePromptBlock({
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
      className="rounded-xl border border-border bg-card"
      open={defaultOpen}
    >
      <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-foreground">
        <div className="flex items-center justify-between gap-3">
          <span>{title}</span>
          <span className="text-[11px] text-muted-foreground">{text.length} chars</span>
        </div>
      </summary>
      <pre className="max-h-64 overflow-auto whitespace-pre-wrap border-t border-border p-3 text-xs leading-5 text-muted-foreground">
        {text || "(empty)"}
      </pre>
    </details>
  );
}

/* ── TraceHitList ── */
export function TraceHitList({
  title,
  hits,
  emptyLabel,
}: {
  title: string;
  hits: TraceChunkHit[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-muted/50 p-3">
      <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {title}
      </div>
      {hits.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-card px-3 py-2 text-sm text-muted-foreground">
          {emptyLabel}
        </div>
      ) : (
        <div className="space-y-2">
          {hits.map((hit) => (
            <div
              key={`${title}-${hit.chunk_id}-${hit.rank}`}
              className="rounded-lg border border-border bg-card p-2.5"
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">#{hit.rank}</span>
                <span>{hit.book_title}</span>
                {hit.chapter_title && <span>{hit.chapter_title}</span>}
                {hit.page_number && <span>p.{hit.page_number}</span>}
                <span>score {formatScore(hit.score)}</span>
              </div>
              <div className="mt-1.5 text-sm text-foreground">{hit.snippet}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
