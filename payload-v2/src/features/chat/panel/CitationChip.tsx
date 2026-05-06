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
// Helpers — 5-Level Score Grading System
// ============================================================

/**
 * 5-level grade for Vector cosine similarity (0–1 range).
 *
 *   Excellent  ≥0.85   — near-perfect semantic match
 *   Good       ≥0.70   — strong relevance
 *   Fair       ≥0.55   — moderate relevance
 *   Weak       ≥0.40   — marginal match
 *   Poor       <0.40   — likely irrelevant
 */
function vectorGrade(score: number): { label: string; cls: string; tooltip: string } {
  if (score >= 0.85) return {
    label: "Excellent",
    cls: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/25",
    tooltip: "Excellent — near-perfect semantic match",
  };
  if (score >= 0.70) return {
    label: "Good",
    cls: "bg-purple-500/15 text-purple-400 ring-1 ring-purple-500/20",
    tooltip: "Good — strong semantic relevance",
  };
  if (score >= 0.55) return {
    label: "Fair",
    cls: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20",
    tooltip: "Fair — moderate semantic relevance",
  };
  if (score >= 0.40) return {
    label: "Weak",
    cls: "bg-orange-500/12 text-orange-400/80 ring-1 ring-orange-500/15",
    tooltip: "Weak — marginal semantic match",
  };
  return {
    label: "Poor",
    cls: "bg-red-500/10 text-red-400/60 ring-1 ring-red-500/12",
    tooltip: "Poor — likely irrelevant",
  };
}

/**
 * 5-level grade for BM25 Okapi score (0–∞, typical 0–20+).
 *
 *   Excellent  ≥8    — strong keyword overlap
 *   Good       ≥5    — solid keyword match
 *   Fair       ≥2    — moderate keyword match
 *   Weak       >0    — minimal keyword signal
 *   None       =0    — no keyword match at all
 */
function bm25Grade(score: number): { label: string; cls: string; tooltip: string } {
  if (score >= 8) return {
    label: "Excellent",
    cls: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/25",
    tooltip: "Excellent — strong keyword overlap",
  };
  if (score >= 5) return {
    label: "Good",
    cls: "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/20",
    tooltip: "Good — solid keyword match",
  };
  if (score >= 2) return {
    label: "Fair",
    cls: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20",
    tooltip: "Fair — moderate keyword match",
  };
  if (score > 0) return {
    label: "Weak",
    cls: "bg-orange-500/12 text-orange-400/80 ring-1 ring-orange-500/15",
    tooltip: "Weak — minimal keyword signal",
  };
  return {
    label: "None",
    cls: "bg-muted-foreground/8 text-muted-foreground/50 ring-1 ring-muted-foreground/10",
    tooltip: "None — no keyword match",
  };
}

/** Retrieval strategy tag config (EV2-T1-03). All SVG, no emoji. */
const STRATEGY_TAG: Record<string, { Icon: React.FC<{ className?: string }>; label: string; cls: string }> = {
  bm25:   { Icon: IconBM25,   label: "BM25",   cls: "bg-blue-500/12 text-blue-500 ring-1 ring-blue-500/25" },
  vector: { Icon: IconVector,  label: "Vector", cls: "bg-purple-500/12 text-purple-500 ring-1 ring-purple-500/25" },
  both:   { Icon: IconHybrid,  label: "Both",   cls: "bg-emerald-500/12 text-emerald-500 ring-1 ring-emerald-500/25" },
};

/** Consulting source type tag config (C4). */
const SOURCE_TYPE_TAG: Record<string, { label: string; cls: string }> = {
  persona: { label: "Persona", cls: "bg-blue-500/12 text-blue-500 ring-1 ring-blue-500/25" },
  user_doc: { label: "User doc", cls: "bg-orange-500/12 text-orange-500 ring-1 ring-orange-500/25" },
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
  const sourceTypeTag = source.source_type
    ? SOURCE_TYPE_TAG[source.source_type]
    : null;
  const strategyTag = source.retrieval_source
    ? STRATEGY_TAG[source.retrieval_source]
    : null;

  // Pre-compute grades for score badges
  const vGrade = source.vector_score != null && source.vector_score > 0
    ? vectorGrade(source.vector_score) : null;
  const kGrade = source.bm25_score != null
    ? bm25Grade(source.bm25_score) : null;

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

        {/* Per-retriever scores: number pill + grade label pill */}
        {(source.vector_score != null || source.bm25_score != null) ? (
          <>
            {vGrade && source.vector_score != null && (
              <>
                {/* Vector score number */}
                <span
                  className="shrink-0 rounded-full bg-purple-500/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-purple-400 ring-1 ring-purple-500/15"
                  title={`Vector cosine similarity: ${source.vector_score.toFixed(4)}`}
                >
                  V:{source.vector_score.toFixed(2)}
                </span>
                {/* Vector grade label */}
                <span
                  className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold leading-none ${vGrade.cls}`}
                  title={vGrade.tooltip}
                >
                  {vGrade.label}
                </span>
              </>
            )}
            {kGrade && source.bm25_score != null && (
              <>
                {/* BM25 score number */}
                <span
                  className="shrink-0 rounded-full bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-blue-400 ring-1 ring-blue-500/15"
                  title={`BM25 keyword score: ${source.bm25_score.toFixed(4)}`}
                >
                  K:{source.bm25_score.toFixed(2)}
                </span>
                {/* BM25 grade label */}
                <span
                  className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold leading-none ${kGrade.cls}`}
                  title={kGrade.tooltip}
                >
                  {kGrade.label}
                </span>
              </>
            )}
          </>
        ) : score != null && (() => {
          const g = vectorGrade(score);
          return (
            <>
              <span
                className="shrink-0 rounded-full bg-purple-500/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-purple-400 ring-1 ring-purple-500/15"
                title={`Score: ${score.toFixed(4)}`}
              >
                {score.toFixed(2)}
              </span>
              <span
                className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold leading-none ${g.cls}`}
                title={g.tooltip}
              >
                {g.label}
              </span>
            </>
          );
        })()}

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

        {/* Consulting source type tag (C4) */}
        {sourceTypeTag && (
          <span
            className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold leading-none ${sourceTypeTag.cls}`}
            title={`Consulting source: ${sourceTypeTag.label}`}
          >
            {sourceTypeTag.label}
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
