"use client";

/**
 * panel/SourceCard.tsx
 * Compact citation chip — shows [n] book_title · p.XX inline.
 * Hover  → portal-based popover with Markdown/KaTeX-rendered snippet.
 * Click  → dispatches SELECT_SOURCE to jump to PDF page + highlight.
 */
import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import Markdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import type { SourceInfo } from "@/features/shared/types";
import { useAppDispatch } from "@/features/shared/AppContext";
import { prepareForKatex } from "./textUtils";



interface Props {
  source: SourceInfo;
  index: number;
  isActive: boolean;
}

export default function SourceCard({ source, index, isActive }: Props) {
  const dispatch = useAppDispatch();
  const chipRef = useRef<HTMLButtonElement>(null);
  const [showPopover, setShowPopover] = useState(false);
  const [pos, setPos] = useState<{
    top?: number;
    bottom?: number;
    left: number;
  }>({ left: 0 });
  const enterTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const leaveTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const citationNum = source.citation_index ?? index + 1;

  /* ── Delayed show / hide — allows mouse travel between chip and popover ── */
  const scheduleShow = useCallback(() => {
    clearTimeout(leaveTimer.current);
    enterTimer.current = setTimeout(() => {
      if (!chipRef.current) return;
      const r = chipRef.current.getBoundingClientRect();
      const popW = 356;
      const popH = 320;
      const gap = 10;

      const fitsRight = r.right + gap + popW < window.innerWidth - 8;
      const fitsLeft = r.left - gap - popW > 8;

      if (fitsRight) {
        const top = Math.max(
          8,
          Math.min(r.top - 40, window.innerHeight - popH - 8),
        );
        setPos({ top, left: r.right + gap });
      } else if (fitsLeft) {
        const top = Math.max(
          8,
          Math.min(r.top - 40, window.innerHeight - popH - 8),
        );
        setPos({ top, left: r.left - gap - popW });
      } else {
        const openUp = r.top > window.innerHeight / 2;
        const left = Math.max(8, Math.min(r.left, window.innerWidth - popW - 8));
        setPos(
          openUp
            ? { bottom: window.innerHeight - r.top + gap, left }
            : { top: r.bottom + gap, left },
        );
      }
      setShowPopover(true);
    }, 200);
  }, []);

  const scheduleHide = useCallback(() => {
    clearTimeout(enterTimer.current);
    leaveTimer.current = setTimeout(() => setShowPopover(false), 180);
  }, []);

  /* ── Close on scroll so stale position doesn't linger ── */
  useEffect(() => {
    if (!showPopover) return;
    const close = () => setShowPopover(false);
    const thread = chipRef.current?.closest(".chat-thread");
    thread?.addEventListener("scroll", close, { passive: true });
    return () => thread?.removeEventListener("scroll", close);
  }, [showPopover]);

  /* ── Cleanup timers ── */
  useEffect(
    () => () => {
      clearTimeout(enterTimer.current);
      clearTimeout(leaveTimer.current);
    },
    [],
  );

  /* ── Popover (rendered into document.body via portal) ── */
  const popover =
    showPopover && source.snippet
      ? createPortal(
          <div
            className="source-popover fixed z-9999 w-[348px] rounded-xl border border-border/60 bg-popover/95 p-3 text-xs shadow-2xl backdrop-blur-md"
            style={{
              top: pos.top != null ? `${pos.top}px` : undefined,
              bottom: pos.bottom != null ? `${pos.bottom}px` : undefined,
              left: `${pos.left}px`,
            }}
            onMouseEnter={() => clearTimeout(leaveTimer.current)}
            onMouseLeave={scheduleHide}
          >
            {/* ── Header ── */}
            <div className="mb-2 flex items-center gap-1.5 border-b border-border/40 pb-2">
              <span className="inline-flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-blue-500 text-[10px] font-bold text-white">
                {citationNum}
              </span>
              <span className="min-w-0 flex-1 truncate font-semibold text-foreground">
                {source.book_title}
              </span>
              {source.chapter_title && (
                <>
                  <span className="text-muted-foreground/40">·</span>
                  <span className="max-w-[120px] truncate text-muted-foreground">
                    {source.chapter_title}
                  </span>
                </>
              )}
              <span className="ml-auto shrink-0 tabular-nums text-muted-foreground/60">
                p.{source.page_number}
              </span>
            </div>

            {/* ── Snippet with Markdown + KaTeX rendering ── */}
            <div className="source-snippet max-h-96 overflow-y-auto rounded-lg bg-muted/30 px-3 py-2 leading-relaxed text-popover-foreground/90">
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
                {prepareForKatex(source.snippet)}
              </Markdown>
            </div>
          </div>,
          document.body,
        )
      : null;

  /* ── Chip ── */
  return (
    <>
      <button
        ref={chipRef}
        type="button"
        onClick={() => dispatch({ type: "SELECT_SOURCE", source })}
        onMouseEnter={scheduleShow}
        onMouseLeave={scheduleHide}
        className={`source-chip inline-flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all duration-150 ${
          isActive
            ? "border-blue-400/60 bg-blue-500/10 text-blue-500 shadow-sm shadow-blue-500/10"
            : "border-border bg-card/80 text-muted-foreground hover:border-blue-300/50 hover:bg-accent/50 hover:text-foreground"
        }`}
        aria-label={`${source.book_title} · p.${source.page_number} — click to view in PDF`}
      >
        <span
          className={`inline-flex h-[18px] w-[18px] items-center justify-center rounded-full text-[10px] font-bold leading-none ${
            isActive
              ? "bg-blue-500 text-white"
              : "bg-muted-foreground/15 text-muted-foreground"
          }`}
        >
          {citationNum}
        </span>
        <span className="max-w-[140px] truncate">
          {source.book_title}
        </span>
        <span className="text-muted-foreground/40">·</span>
        <span className="shrink-0 tabular-nums text-muted-foreground/70">
          p.{source.page_number}
        </span>
      </button>
      {popover}
    </>
  );
}
