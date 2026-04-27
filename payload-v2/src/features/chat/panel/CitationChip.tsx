/**
 * CitationChip — Inline citation chip for AnswerBlock rendering.
 *
 * Displays [N] BookTitle p.XX + relevance score + strategy tag.
 * Click the chip body → toggle inline content panel.
 *
 * Action buttons (all SVG, no emoji):
 *   📄 Open PDF  → dispatch SELECT_SOURCE to open PDF viewer.
 *   📋 Copy      → copy snippet text to clipboard.
 *   👁 Preview   → toggle inline content panel (same as chip click).
 *
 * Score color rules (UEP-T4-04, aligned with EvalScoreCard GRADE_CLS):
 *   ≥0.85 → emerald (excellent)
 *   ≥0.70 → blue    (good)
 *   ≥0.50 → amber   (fair)
 *   <0.50 → red     (poor)
 *
 * Strategy icons (all SVG, EV2-T1-03):
 *   bm25   → text-search magnifier icon (blue)
 *   vector → neural-network / embedding icon (purple)
 *   both   → merge-arrows icon (emerald)
 *
 * Usage: <CitationChip source={source} index={1} onChipClick={fn} />
 */

"use client";

import { useCallback } from "react";
import { useAppDispatch } from "@/features/shared/AppContext";
import type { SourceInfo } from "@/features/shared/types";

// ============================================================
// SVG Icon Components (no emoji!)
// ============================================================

/** BM25 keyword search icon — magnifier with "T" text inside */
function IconBM25({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <text x="7" y="9.5" textAnchor="middle" fill="currentColor" fontSize="6" fontWeight="700" fontFamily="system-ui">T</text>
    </svg>
  );
}

/** Vector embedding icon — neural-network nodes */
function IconVector({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="3" cy="4" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="3" cy="12" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="13" cy="8" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="8" cy="3" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="8" cy="13" r="1.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M4.5 4.5L6.5 3.5M4.5 11.5L6.5 12.5M9.5 3.5L11.5 7.5M9.5 12.5L11.5 8.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

/** Both / hybrid retrieval icon — converging arrows */
function IconHybrid({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 4L8 8L3 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M13 4L8 8L13 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="1.5" fill="currentColor" />
    </svg>
  );
}

/** Document / PDF icon */
function IconDocument({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 1.5h5.086a1 1 0 0 1 .707.293l3.414 3.414a1 1 0 0 1 .293.707V13.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.3" />
      <path d="M9 1.5V5a1 1 0 0 0 1 1h3.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M5.5 9h5M5.5 11h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}



// ============================================================
// Helpers
// ============================================================

/** Color-coded CSS classes for relevance score badge (UEP-T4-04). */
function scoreStyle(score: number): string {
  if (score >= 0.85) return "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20";
  if (score >= 0.7) return "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/20";
  if (score >= 0.5) return "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20";
  return "bg-red-500/15 text-red-400 ring-1 ring-red-500/20";
}

/** Retrieval strategy tag config (EV2-T1-03). All SVG, no emoji. */
const STRATEGY_TAG: Record<string, { Icon: React.FC<{ className?: string }>; label: string; cls: string }> = {
  bm25:   { Icon: IconBM25,   label: "BM25",   cls: "bg-blue-500/12 text-blue-500 ring-1 ring-blue-500/25" },
  vector: { Icon: IconVector,  label: "Vector", cls: "bg-purple-500/12 text-purple-500 ring-1 ring-purple-500/25" },
  both:   { Icon: IconHybrid,  label: "Both",   cls: "bg-emerald-500/12 text-emerald-500 ring-1 ring-emerald-500/25" },
};

/** Shared style for the small square action buttons */
const ACTION_BTN =
  "inline-flex h-[24px] w-[24px] items-center justify-center rounded-md transition-all duration-150 " +
  "text-muted-foreground/50 hover:bg-accent hover:text-foreground";

// ============================================================
// Types
// ============================================================
interface CitationChipProps {
  source: SourceInfo;
  /** 1-based citation number */
  index: number;
  /** Whether this chip is the currently active/selected citation */
  isActive?: boolean;
  /** Callback when chip is clicked (for parent to toggle inline panel) */
  onChipClick?: () => void;
}

// ============================================================
// Component
// ============================================================
export default function CitationChip({
  source,
  index,
  isActive = false,
  onChipClick,
}: CitationChipProps) {
  const dispatch = useAppDispatch();

  // ── Click chip body → toggle inline content panel only ─────
  const handleChipClick = useCallback(() => {
    onChipClick?.();
  }, [onChipClick]);

  // ── Click PDF icon → jump PDF viewer to this source's page ─
  const handleOpenPdf = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      const raw = source as any;
      dispatch({
        type: "SELECT_SOURCE",
        source: {
          ...source,
          source_id: raw.chunk_id || raw.source_id || "",
          book_id_string:
            typeof raw.book_id === "string"
              ? raw.book_id
              : source.book_id_string,
          snippet: raw.snippet || "",
          citation_label: `[${index}]`,
        },
      });
    },
    [dispatch, source, index],
  );



  const score = source.score;
  const strategyTag = source.retrieval_source
    ? STRATEGY_TAG[source.retrieval_source]
    : null;

  return (
    <span className="citation-chip group/chip inline-flex items-center gap-0.5">
      {/* ── Info chip (clickable → toggle panel) ── */}
      <button
        type="button"
        onClick={handleChipClick}
        className={`inline-flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-all duration-150 ${
          isActive
            ? "border-primary/40 bg-primary/10 text-primary shadow-sm shadow-primary/10"
            : "border-border/60 bg-card/60 text-muted-foreground hover:border-primary/30 hover:bg-accent/50 hover:text-foreground"
        }`}
        aria-label={`${source.book_title || ""} p.${source.page_number}${score != null ? ` — relevance ${(score * 100).toFixed(0)}%` : ""} — click to preview`}
      >
        {/* Citation number badge */}
        <span
          className={`inline-flex h-[20px] w-[20px] items-center justify-center rounded-full text-[10px] font-bold leading-none shrink-0 ${
            isActive
              ? "bg-primary text-primary-foreground"
              : "bg-muted-foreground/15 text-muted-foreground"
          }`}
        >
          {index}
        </span>

        {/* Book title (truncated) */}
        {source.book_title && (
          <span className="max-w-[120px] truncate text-[11px] text-foreground/80">
            {source.book_title}
          </span>
        )}

        {/* Page number */}
        <span className="shrink-0 tabular-nums text-muted-foreground/70 text-[11px]">
          p.{source.page_number}
        </span>

        {/* Relevance score badge */}
        {score != null && (
          <span
            className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums ${scoreStyle(score)}`}
            title={`Relevance Score: ${score.toFixed(2)}`}
          >
            {score.toFixed(2)}
          </span>
        )}

        {/* Retrieval strategy tag (SVG icon, EV2-T1-03) */}
        {strategyTag && (
          <span
            className={`shrink-0 inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-semibold leading-none ${strategyTag.cls}`}
            title={`Retrieved via ${strategyTag.label}`}
          >
            <strategyTag.Icon className="h-2.5 w-2.5" />
            <span className="hidden sm:inline">{strategyTag.label}</span>
          </span>
        )}
      </button>

      {/* ── PDF action button ── */}
      <button
        type="button"
        onClick={handleOpenPdf}
        className={ACTION_BTN}
        title="Open in PDF viewer"
        aria-label={`Open PDF — ${source.book_title || ""} p.${source.page_number}`}
      >
        <IconDocument className="h-3 w-3" />
      </button>
    </span>
  );
}
