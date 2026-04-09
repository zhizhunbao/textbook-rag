/**
 * AnswerBlockRenderer — Renders AI answers as semantic AnswerBlocks.
 *
 * Each AnswerBlock is a Markdown paragraph followed by citation chips.
 * Clicking a chip toggles an inline content panel below the chips row
 * (no floating popover) and jumps the PDF viewer to that page.
 *
 * Usage: <AnswerBlockRenderer content={text} sources={sources} />
 */

"use client";

import { useMemo, useState, useCallback } from "react";
import type { ReactNode } from "react";
import Markdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import type { SourceInfo } from "@/features/shared/types";
import { parseAnswerBlocks } from "./answerBlocks";
import CitationChip from "./CitationChip";
import { prepareForKatex } from "./textUtils";

// ============================================================
// Types
// ============================================================
interface AnswerBlockRendererProps {
  /** Raw LLM answer text */
  content: string;
  /** Source list from the query response */
  sources?: SourceInfo[];
}

// ============================================================
// Helpers
// ============================================================



// ============================================================
// Inline citation content panel
// ============================================================
function InlineCitationPanel({ source, index, onClose }: { source: SourceInfo; index: number; onClose: () => void }) {
  const previewContent = source.full_content || source.snippet;
  if (!previewContent) return null;

  return (
    <div className="relative mt-1.5 rounded-lg border border-border/50 border-l-2 border-l-blue-500/60 bg-muted/20 pl-3 pr-8 py-2 text-xs leading-relaxed text-popover-foreground/90 animate-in fade-in slide-in-from-top-1 duration-150">
      {/* Close button */}
      <button
        type="button"
        onClick={onClose}
        className="absolute top-1.5 right-1.5 inline-flex h-5 w-5 items-center justify-center rounded-md text-muted-foreground/40 transition-colors hover:bg-muted hover:text-foreground"
        aria-label="Close"
      >
        ×
      </button>
      <Markdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeRaw]}
        components={{
          p({ children }) {
            return <p className="my-1 leading-relaxed">{children}</p>;
          },
          code({ children, className }) {
            if (className) {
              return (
                <code className={`${className} text-[0.9em]`}>
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded-[3px] bg-muted px-1 py-0.5 text-[0.88em] font-mono text-foreground">
                {children}
              </code>
            );
          },
          pre({ children }) {
            return (
              <pre className="my-1.5 overflow-x-auto rounded-md bg-muted/70 p-2 text-[0.88em] font-mono leading-snug">
                {children}
              </pre>
            );
          },
          strong({ children }) {
            return (
              <strong className="font-semibold text-foreground">
                {children}
              </strong>
            );
          },
        }}
      >
        {prepareForKatex(previewContent)}
      </Markdown>
    </div>
  );
}

// ============================================================
// Component
// ============================================================
export default function AnswerBlockRenderer({
  content,
  sources,
}: AnswerBlockRendererProps) {

  // ── Build citation lookup map ─────────────────────────────
  const citationMap = useMemo(() => {
    const map = new Map<number, SourceInfo>();
    if (!sources) return map;

    for (const s of sources) {
      const ci = (s as any).citation_index as number | undefined;
      if (ci != null) map.set(ci, s);
    }
    // Fallback: if no citation_index, use legacy array-based mapping
    if (map.size === 0) {
      for (let i = 0; i < sources.length; i++) {
        map.set(i + 1, sources[i]);
      }
    }
    return map;
  }, [sources]);

  // ── Parse answer into blocks ──────────────────────────────
  const blocks = useMemo(() => parseAnswerBlocks(content), [content]);

  // ── Expanded citations state (multiple panels can be open) ──
  const [expandedCitations, setExpandedCitations] = useState<Set<number>>(new Set());

  const toggleCitation = useCallback((globalIndex: number) => {
    setExpandedCitations((prev) => {
      const next = new Set(prev);
      if (next.has(globalIndex)) next.delete(globalIndex);
      else next.add(globalIndex);
      return next;
    });
  }, []);

  const closeCitation = useCallback((globalIndex: number) => {
    setExpandedCitations((prev) => {
      const next = new Set(prev);
      next.delete(globalIndex);
      return next;
    });
  }, []);

  // ── Determine active citation ─────────────────────────────
  // Track the specific globalIndex that was selected (not just chunk_id)
  // so only one chip highlights when the same citation appears in multiple blocks
  const [selectedGlobalIndex, setSelectedGlobalIndex] = useState<number | null>(null);

  // ── Pre-compute global sequential numbering across all blocks ──
  const blocksWithGlobalIndex = useMemo(() => {
    let globalIdx = 0;
    const result = blocks.map((block) => {
      const blockSources = block.citationIndices
        .map((ci) => ({ ci, source: citationMap.get(ci) }))
        .filter(
          (entry): entry is { ci: number; source: SourceInfo } =>
            entry.source != null,
        );
      const withGlobal = blockSources.map((entry) => ({
        ...entry,
        globalIndex: ++globalIdx,
      }));
      return { text: block.text, sources: withGlobal };
    });

    // Fallback: if LLM didn't write any [N] markers, show all sources
    // as citation chips after the last paragraph block.
    const totalCited = result.reduce((sum, b) => sum + b.sources.length, 0);
    if (totalCited === 0 && citationMap.size > 0 && result.length > 0) {
      const lastBlock = result[result.length - 1];
      const fallbackSources = Array.from(citationMap.entries()).map(
        ([ci, source]) => ({ ci, source, globalIndex: ++globalIdx }),
      );
      lastBlock.sources = fallbackSources;
    }

    return result;
  }, [blocks, citationMap]);

  // ── Compute uncited sources (sources not referenced by any [N] marker) ──
  const { uncitedSources } = useMemo(() => {
    // Collect all citation indices that appeared in the answer text
    const citedIndices = new Set<number>();
    for (const block of blocksWithGlobalIndex) {
      for (const { ci } of block.sources) {
        citedIndices.add(ci);
      }
    }

    // Find sources that exist in citationMap but were never cited
    let idx = blocksWithGlobalIndex.reduce(
      (max, b) => Math.max(max, ...b.sources.map((s) => s.globalIndex), 0),
      0,
    );
    const uncited: Array<{ ci: number; source: SourceInfo; globalIndex: number }> = [];
    for (const [ci, source] of citationMap.entries()) {
      if (!citedIndices.has(ci)) {
        uncited.push({ ci, source, globalIndex: ++idx });
      }
    }
    return { uncitedSources: uncited, nextGlobalIdx: idx };
  }, [blocksWithGlobalIndex, citationMap]);

  // ── Show/hide uncited sources section ─────────────────────
  const [showAllSources, setShowAllSources] = useState(false);

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="answer-blocks space-y-3">
      {blocksWithGlobalIndex.map((block, blockIdx) => (
        <div key={blockIdx} className="answer-block">
          {/* ── Paragraph text (Markdown + KaTeX) ── */}
          <Markdown
            remarkPlugins={[remarkMath]}
            rehypePlugins={[rehypeKatex, rehypeRaw]}
            components={{
              h2({ children }) {
                return (
                  <h2 className="mt-4 mb-2 text-base font-bold text-foreground">
                    {children}
                  </h2>
                );
              },
              h3({ children }) {
                return (
                  <h3 className="mt-3 mb-1.5 text-[0.94rem] font-semibold text-foreground">
                    {children}
                  </h3>
                );
              },
              p({ children }) {
                return (
                  <p className="my-1.5 leading-7 text-foreground">
                    {children}
                  </p>
                );
              },
              ul({ children }) {
                return (
                  <ul className="my-2 list-disc space-y-1 pl-5 text-foreground">
                    {children}
                  </ul>
                );
              },
              ol({ children }) {
                return (
                  <ol className="my-2 list-decimal space-y-1 pl-5 text-foreground">
                    {children}
                  </ol>
                );
              },
              li({ children }) {
                return <li className="leading-7">{children}</li>;
              },
              strong({ children }) {
                return (
                  <strong className="font-semibold text-foreground">
                    {children}
                  </strong>
                );
              },
              code({ children }) {
                return (
                  <code className="rounded bg-muted px-1.5 py-0.5 text-[0.92em] text-foreground">
                    {children}
                  </code>
                );
              },
              a({
                href,
                children,
              }: {
                href?: string;
                children?: ReactNode;
              }) {
                return (
                  <a
                    href={href}
                    className="text-blue-600 underline decoration-blue-200 underline-offset-2 hover:text-blue-800"
                  >
                    {children}
                  </a>
                );
              },
            }}
          >
            {prepareForKatex(block.text)}
          </Markdown>

          {/* ── Citation chips row ── */}
          {block.sources.length > 0 && (
            <div className="mt-1">
              <div className="flex flex-wrap items-center gap-1.5">
                {block.sources.map(({ ci, source, globalIndex }) => (
                  <CitationChip
                    key={ci}
                    source={source}
                    index={ci}
                    isActive={
                      expandedCitations.has(globalIndex) ||
                      selectedGlobalIndex === globalIndex
                    }
                    onChipClick={() => {
                      toggleCitation(globalIndex);
                      setSelectedGlobalIndex(
                        selectedGlobalIndex === globalIndex ? null : globalIndex,
                      );
                    }}
                  />
                ))}
              </div>

              {/* ── Inline expanded content panels (multiple can be open) ── */}
              {block.sources.map(({ ci, source, globalIndex }) =>
                expandedCitations.has(globalIndex) ? (
                  <InlineCitationPanel
                    key={`panel-${ci}`}
                    source={source}
                    index={globalIndex}
                    onClose={() => closeCitation(globalIndex)}
                  />
                ) : null,
              )}
            </div>
          )}
        </div>
      ))}

      {/* ── All Sources section (shows uncited sources) ── */}
      {uncitedSources.length > 0 && (
        <div className="mt-2 border-t border-border/30 pt-2">
          <button
            type="button"
            onClick={() => setShowAllSources((prev) => !prev)}
            className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground/70 transition-colors hover:text-foreground"
          >
            <svg
              className={`h-3 w-3 transition-transform duration-150 ${showAllSources ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            {uncitedSources.length} more source{uncitedSources.length > 1 ? "s" : ""} retrieved
          </button>

          {showAllSources && (
            <div className="mt-1.5">
              <div className="flex flex-wrap items-center gap-1.5">
                {uncitedSources.map(({ ci, source, globalIndex }) => (
                  <CitationChip
                    key={`uncited-${ci}`}
                    source={source}
                    index={ci}
                    isActive={
                      expandedCitations.has(globalIndex) ||
                      selectedGlobalIndex === globalIndex
                    }
                    onChipClick={() => {
                      toggleCitation(globalIndex);
                      setSelectedGlobalIndex(
                        selectedGlobalIndex === globalIndex ? null : globalIndex,
                      );
                    }}
                  />
                ))}
              </div>

              {/* ── Inline expanded content panels for uncited sources ── */}
              {uncitedSources.map(({ ci, source, globalIndex }) =>
                expandedCitations.has(globalIndex) ? (
                  <InlineCitationPanel
                    key={`panel-uncited-${ci}`}
                    source={source}
                    index={globalIndex}
                    onClose={() => closeCitation(globalIndex)}
                  />
                ) : null,
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
