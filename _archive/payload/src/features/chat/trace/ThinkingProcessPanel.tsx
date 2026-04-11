/**
 * trace/ThinkingProcessPanel.tsx
 * 可视化思考过程流程图 — 垂直布局，只显示实际用到的步骤
 *
 * 规则:
 *   - 只显示实际有结果/被使用的策略节点
 *   - 未使用的策略不占位不显示
 *   - Query 节点只在有 fts_query 时显示
 *   - 每个节点显示简要统计，点击可展开详情
 */
import { useState } from "react";
import type { QueryTrace, TraceChunkHit } from "@/features/shared/types";

/* ── SVG Icons ── */

function IconQuery({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
  );
}

function IconFts({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
    </svg>
  );
}

function IconVector({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
    </svg>
  );
}

function IconToc({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
    </svg>
  );
}

function IconFusion({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}

function IconLlm({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
    </svg>
  );
}

/* ── Strategy metadata ── */
const STRATEGY_META: Record<
  string,
  {
    label: string;
    Icon: (props: { className?: string }) => React.ReactElement;
    colorClasses: string;       // icon circle bg + text
    borderActive: string;
    gradient: string;
  }
> = {
  fts: {
    label: "FTS5 (BM25)",
    Icon: IconFts,
    colorClasses: "bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400",
    borderActive: "border-amber-400/60",
    gradient: "from-amber-500/8 to-transparent",
  },
  vector: {
    label: "Vector Search",
    Icon: IconVector,
    colorClasses: "bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400",
    borderActive: "border-blue-400/60",
    gradient: "from-blue-500/8 to-transparent",
  },
  toc: {
    label: "TOC Heading",
    Icon: IconToc,
    colorClasses: "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400",
    borderActive: "border-emerald-400/60",
    gradient: "from-emerald-500/8 to-transparent",
  },
};

/* ── Vertical connector line ── */
function VConnector() {
  return (
    <div className="flex justify-center py-0.5">
      <div className="flex flex-col items-center">
        <div className="w-px h-4 bg-border" />
        <svg width="10" height="8" viewBox="0 0 10 8" className="text-muted-foreground/40 -mt-px">
          <polygon points="5 8, 0 0, 10 0" fill="currentColor" />
        </svg>
      </div>
    </div>
  );
}

/* ── Hit list for expanded detail ── */
function HitList({ hits, maxShow = 3 }: { hits: TraceChunkHit[]; maxShow?: number }) {
  if (hits.length === 0) return <div className="text-muted-foreground italic text-xs">No hits</div>;

  return (
    <div className="space-y-1 mt-2">
      {hits.slice(0, maxShow).map((hit) => (
        <div
          key={`${hit.chunk_id}-${hit.rank}`}
          className="flex items-center justify-between rounded-md bg-muted/60 px-2.5 py-1.5 text-xs"
        >
          <span className="truncate text-foreground">
            p.{hit.page_number} — {hit.snippet.slice(0, 50)}…
          </span>
          <span className="ml-2 shrink-0 font-mono font-semibold text-muted-foreground">
            {hit.score != null ? hit.score.toFixed(3) : "n/a"}
          </span>
        </div>
      ))}
      {hits.length > maxShow && (
        <div className="text-center text-[10px] text-muted-foreground">
          +{hits.length - maxShow} more
        </div>
      )}
    </div>
  );
}

/* ── Flow node (vertical) ── */
function FlowNode({
  Icon,
  label,
  stat,
  colorClasses,
  borderActive,
  gradient,
  detail,
}: {
  Icon: (props: { className?: string }) => React.ReactElement;
  label: string;
  stat: string;
  colorClasses: string;
  borderActive: string;
  gradient: string;
  detail?: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      type="button"
      onClick={() => detail && setExpanded(!expanded)}
      className={`
        w-full rounded-xl border px-3.5 py-2.5 text-left transition-all duration-150
        bg-gradient-to-r ${gradient}
        ${borderActive}
        ${detail ? "cursor-pointer hover:shadow-md" : "cursor-default"}
        ${expanded ? "shadow-md" : "shadow-sm"}
      `}
    >
      <div className="flex items-center gap-3">
        {/* Icon circle */}
        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${colorClasses}`}>
          <Icon className="h-4 w-4" />
        </div>

        {/* Label + stat */}
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold text-foreground">{label}</div>
          <div className="text-[11px] text-muted-foreground truncate">{stat}</div>
        </div>

        {/* Expand chevron */}
        {detail && (
          <svg
            className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-150 ${expanded ? "rotate-180" : ""}`}
            fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && detail && (
        <div className="mt-2 border-t border-border pt-2">{detail}</div>
      )}
    </button>
  );
}

/* ── Main component ── */
export default function ThinkingProcessPanel({ trace }: { trace: QueryTrace }) {
  const [isOpen, setIsOpen] = useState(false);

  const strategies = [
    { key: "fts", hits: trace.retrieval.fts_results ?? [] },
    { key: "vector", hits: trace.retrieval.vector_results ?? [] },
    { key: "toc", hits: trace.retrieval.toc_results ?? [] },
  ];

  // Only show strategies that were actually used (have hits)
  const activeStrategies = strategies.filter((s) => s.hits.length > 0);
  const fusedResults = trace.retrieval.fused_results ?? [];
  const fusedCount = fusedResults.length;

  // Build the visible flow nodes list
  const hasQuery = Boolean(trace.retrieval.fts_query);
  const hasFusion = fusedCount > 0;
  const hasGeneration = Boolean(trace.generation.model);

  // Count of visible stages for summary
  const visibleStages =
    (hasQuery ? 1 : 0) + activeStrategies.length + (hasFusion ? 1 : 0) + (hasGeneration ? 1 : 0);

  return (
    <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
      {/* ── Summary bar ── */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full cursor-pointer items-center gap-2 px-4 py-3 text-sm font-medium text-foreground select-none hover:bg-muted/50 transition-colors"
      >
        <svg
          className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
          fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m9 5 7 7-7 7" />
        </svg>

        <IconLlm className="h-4 w-4 text-primary" />

        <span>Thinking Process</span>

        {/* Mini icon strip */}
        <div className="ml-auto flex items-center gap-1.5">
          {activeStrategies.map(({ key }) => {
            const meta = STRATEGY_META[key];
            return (
              <div key={key} className={`flex h-5 w-5 items-center justify-center rounded ${meta.colorClasses}`} title={meta.label}>
                <meta.Icon className="h-3 w-3" />
              </div>
            );
          })}
          <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground whitespace-nowrap">
            {visibleStages} steps → {fusedCount} chunks
          </span>
        </div>
      </button>

      {/* ── Vertical flowchart ── */}
      {isOpen && (
        <div className="border-t border-border px-4 py-4">
          <div className="mx-auto max-w-md flex flex-col">
            {/* 1. Query Analysis — only if fts_query exists */}
            {hasQuery && (
              <>
                <FlowNode
                  Icon={IconQuery}
                  label="Query Analysis"
                  stat={trace.retrieval.fts_query || trace.question}
                  colorClasses="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  borderActive="border-slate-300/60 dark:border-slate-600/60"
                  gradient="from-slate-500/5 to-transparent"
                  detail={
                    <div className="text-xs space-y-1.5">
                      <div>
                        <span className="font-semibold text-foreground">Question: </span>
                        <span className="text-muted-foreground">{trace.question}</span>
                      </div>
                      {trace.retrieval.fts_query && (
                        <div>
                          <span className="font-semibold text-foreground">FTS Query: </span>
                          <code className="text-primary text-[11px] break-all">{trace.retrieval.fts_query}</code>
                        </div>
                      )}
                    </div>
                  }
                />
                <VConnector />
              </>
            )}

            {/* 2. Strategy nodes — only active ones */}
            {activeStrategies.map(({ key, hits }, idx) => {
              const meta = STRATEGY_META[key];
              return (
                <div key={key}>
                  <FlowNode
                    Icon={meta.Icon}
                    label={meta.label}
                    stat={`${hits.length} hit${hits.length !== 1 ? "s" : ""} retrieved`}
                    colorClasses={meta.colorClasses}
                    borderActive={meta.borderActive}
                    gradient={meta.gradient}
                    detail={<HitList hits={hits} />}
                  />
                  {/* Connector after each strategy except the last one when there's no fusion/generation */}
                  {(idx < activeStrategies.length - 1 || hasFusion || hasGeneration) && (
                    <VConnector />
                  )}
                </div>
              );
            })}

            {/* Empty state if no strategies matched */}
            {activeStrategies.length === 0 && (
              <>
                <div className="rounded-xl border border-dashed border-amber-400/50 bg-amber-500/5 px-3.5 py-2.5 text-xs text-amber-600 dark:text-amber-400">
                  No retrieval strategies returned results
                </div>
                {(hasFusion || hasGeneration) && <VConnector />}
              </>
            )}

            {/* 3. RRF Fusion — only if there are fused results */}
            {hasFusion && (
              <>
                <FlowNode
                  Icon={IconFusion}
                  label="RRF Fusion"
                  stat={`Best ${fusedCount} chunk${fusedCount !== 1 ? "s" : ""} selected`}
                  colorClasses="bg-violet-100 text-violet-600 dark:bg-violet-900/40 dark:text-violet-400"
                  borderActive="border-violet-400/60"
                  gradient="from-violet-500/8 to-transparent"
                  detail={
                    <div className="space-y-1 mt-0">
                      {fusedResults.slice(0, 4).map((hit) => (
                        <div
                          key={`fused-${hit.chunk_id}-${hit.rank}`}
                          className="flex items-center justify-between rounded-md bg-muted/60 px-2.5 py-1.5 text-xs"
                        >
                          <span className="flex items-center gap-1.5 truncate text-foreground">
                            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[8px] font-bold text-primary-foreground shrink-0">
                              {hit.rank}
                            </span>
                            p.{hit.page_number} — {hit.snippet.slice(0, 40)}…
                          </span>
                          <span className="ml-2 shrink-0 font-mono font-semibold text-muted-foreground">
                            {hit.score != null ? hit.score.toFixed(4) : "n/a"}
                          </span>
                        </div>
                      ))}
                      {fusedResults.length > 4 && (
                        <div className="text-center text-[10px] text-muted-foreground">
                          +{fusedResults.length - 4} more
                        </div>
                      )}
                    </div>
                  }
                />
                {hasGeneration && <VConnector />}
              </>
            )}

            {/* 4. LLM Generation — only if model is present */}
            {hasGeneration && (
              <FlowNode
                Icon={IconLlm}
                label="Answer Generation"
                stat={trace.generation.model}
                colorClasses="bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-400"
                borderActive="border-rose-400/60"
                gradient="from-rose-500/8 to-transparent"
                detail={
                  <div className="text-xs space-y-1">
                    <div>
                      <span className="font-semibold text-foreground">Model: </span>
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-semibold text-foreground">
                        {trace.generation.model}
                      </span>
                    </div>
                    <div className="text-muted-foreground">
                      {fusedCount} context chunks → structured answer with citations
                    </div>
                  </div>
                }
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
