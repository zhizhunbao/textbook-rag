/**
 * CitationPopover — Hover popover for citation full-content preview.
 *
 * Renders a portal-based popover with Markdown + KaTeX content from
 * the source's full_content field (falling back to snippet).
 * Shared between CitationChip and SourceCard.
 *
 * Usage: <CitationPopover source={source} anchor={chipEl} onClose={fn} />
 */

"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import Markdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import type { SourceInfo } from "@/features/shared/types";
import { prepareForKatex } from "./textUtils";

// ============================================================
// Types
// ============================================================
interface CitationPopoverProps {
  /** Source to preview */
  source: SourceInfo;
  /** The anchor element (chip) for positioning */
  anchorEl: HTMLElement | null;
  /** Whether the popover is visible */
  visible: boolean;
  /** Keep the popover alive (e.g. when mouse enters popover) */
  onMouseEnter?: () => void;
  /** Schedule close (e.g. when mouse leaves popover) */
  onMouseLeave?: () => void;
}

// ============================================================
// Helpers
// ============================================================


// ============================================================
// Component
// ============================================================
export default function CitationPopover({
  source,
  anchorEl,
  visible,
  onMouseEnter,
  onMouseLeave,
}: CitationPopoverProps) {
  const [pos, setPos] = useState<{
    top?: number;
    bottom?: number;
    left: number;
  }>({ left: 0 });

  // ── Recompute position when anchor or visibility changes ────
  useEffect(() => {
    if (!visible || !anchorEl) return;
    const r = anchorEl.getBoundingClientRect();
    const popW = 356; // popover width (w-[348px] + padding)
    const popH = 320; // estimated max height
    const gap = 10;   // spacing between chip and popover

    // Prefer: open to the RIGHT of the chip
    const fitsRight = r.right + gap + popW < window.innerWidth - 8;
    // Fallback: open to the LEFT of the chip
    const fitsLeft = r.left - gap - popW > 8;

    if (fitsRight) {
      // Right of chip, vertically centered on chip
      const top = Math.max(
        8,
        Math.min(r.top - 40, window.innerHeight - popH - 8),
      );
      setPos({ top, left: r.right + gap });
    } else if (fitsLeft) {
      // Left of chip
      const top = Math.max(
        8,
        Math.min(r.top - 40, window.innerHeight - popH - 8),
      );
      setPos({ top, left: r.left - gap - popW });
    } else {
      // Fallback: above or below, left-aligned to chip
      const openUp = r.top > window.innerHeight / 2;
      const left = Math.max(8, Math.min(r.left, window.innerWidth - popW - 8));
      setPos(
        openUp
          ? { bottom: window.innerHeight - r.top + gap, left }
          : { top: r.bottom + gap, left },
      );
    }
  }, [visible, anchorEl]);

  // ── Close on scroll ─────────────────────────────────────────
  useEffect(() => {
    if (!visible || !anchorEl) return;
    const close = () => onMouseLeave?.();
    const thread = anchorEl.closest(".chat-thread");
    thread?.addEventListener("scroll", close, { passive: true });
    return () => thread?.removeEventListener("scroll", close);
  }, [visible, anchorEl, onMouseLeave]);

  // Use full_content for preview; fall back to snippet
  const previewContent = source.full_content || source.snippet;
  if (!visible || !previewContent) return null;


  return createPortal(
    <div
      className="citation-popover fixed z-9999 w-[348px] rounded-xl border border-border/60 bg-popover/95 p-3 text-xs shadow-2xl backdrop-blur-md"
      style={{
        top: pos.top != null ? `${pos.top}px` : undefined,
        bottom: pos.bottom != null ? `${pos.bottom}px` : undefined,
        left: `${pos.left}px`,
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* ── Content with Markdown + KaTeX rendering ── */}
      <div className="citation-snippet max-h-96 overflow-y-auto rounded-lg bg-muted/30 px-3 py-2 leading-relaxed text-popover-foreground/90">
        <Markdown
          remarkPlugins={[remarkMath]}
          rehypePlugins={[rehypeKatex, rehypeRaw]}
          components={{
            p({ children }) {
              return (
                <p className="my-1 leading-relaxed">{children}</p>
              );
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
    </div>,
    document.body,
  );
}
