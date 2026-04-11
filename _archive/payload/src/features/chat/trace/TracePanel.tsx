/**
 * trace/TracePanel.tsx
 * 完整的 Execution Trace 面板（展示 FTS / Vector / TOC / Fused 细节）
 */
import type { QueryTrace } from "@/features/shared/types";
import { TraceStat, TracePromptBlock, TraceHitList } from "./TraceComponents";

export default function TracePanel({ trace }: { trace: QueryTrace }) {
  const ftsCount = trace.retrieval.fts_results.length;
  const vectorCount = trace.retrieval.vector_results.length;
  const tocCount = (trace.retrieval.toc_results ?? []).length;
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
    <div className="rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Execution Trace
          </div>
          <div className="mt-1 text-sm font-medium text-foreground">
            {noContext
              ? "No retrieval context reached the model."
              : `${fusedCount} context chunks were sent to the model.`}
          </div>
        </div>
        <div className="rounded-md border border-border bg-muted px-2.5 py-1 text-xs text-muted-foreground">
          {trace.generation.model}
        </div>
      </div>

      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-4">
          <TraceStat label="FTS hits" value={String(ftsCount)} tone={ftsCount === 0 ? "warn" : "default"} />
          <TraceStat label="Vector hits" value={String(vectorCount)} tone={vectorCount === 0 ? "warn" : "default"} />
          <TraceStat label="TOC hits" value={String(tocCount)} tone={tocCount === 0 ? "warn" : "default"} />
          <TraceStat label="Context sent" value={String(fusedCount)} tone={noContext ? "warn" : "default"} />
        </div>

        {noContext && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2.5 text-sm text-amber-600 dark:text-amber-500">
            Retrieval returned no usable context. The model answered without textbook evidence, so this result is not useful for optimization until retrieval is fixed.
          </div>
        )}

        <details className="rounded-xl border border-border bg-muted/50" open>
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Request
          </summary>
          <div className="space-y-3 border-t border-border p-3">
            <div className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
              <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
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

        <details className="rounded-xl border border-border bg-muted/50" open>
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Retrieval
          </summary>
          <div className="space-y-3 border-t border-border p-3">
            <div className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground">
              <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                FTS query
              </div>
              <code className="break-all text-[13px] text-foreground">
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
                title="TOC Heading Hits"
                hits={trace.retrieval.toc_results ?? []}
                emptyLabel="TOC heading search returned no chunks."
              />
              <TraceHitList
                title="Fused Context Sent To LLM"
                hits={trace.retrieval.fused_results}
                emptyLabel="RRF produced no context to send to the model."
              />
            </div>
          </div>
        </details>

        <details className="rounded-xl border border-border bg-muted/50">
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Generation
          </summary>
          <div className="space-y-3 border-t border-border p-3">
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
