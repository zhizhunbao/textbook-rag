import {
  memo,
  startTransition,
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/esm/Page/TextLayer.css";

import { getPdfUrl, fetchToc } from "@/features/shared/api";
import { useAppState, useAppDispatch } from "@/features/shared/AppContext";
import ResizeHandle from "@/features/shared/ResizeHandle";
import type { TocEntry } from "@/features/shared/types";

function Loading() {
  return (
    <div className="flex h-full items-center justify-center text-slate-400 text-sm">
      Loading…
    </div>
  );
}

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const HORIZONTAL_GUTTER = 32;
const PAGE_GAP = 20;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.1;
const VIEWPORT_VERTICAL_PADDING = 40;
const INITIAL_RENDER_RADIUS = 2;
const VISIBLE_RENDER_RADIUS = 3;
const MIN_TEXT_MATCH_CHARS = 24;

interface PdfPageCanvasProps {
  pageNumber: number;
  renderWidth: number;
  onPageLoadSuccess: (pageNumber: number, dims: { width: number; height: number }) => void;
}

const PdfPageCanvas = memo(function PdfPageCanvas({
  pageNumber,
  renderWidth,
  onPageLoadSuccess,
}: PdfPageCanvasProps) {
  const handleLoadSuccess = useCallback(
    (page: { width: number; height: number }) => {
      onPageLoadSuccess(pageNumber, { width: page.width, height: page.height });
    },
    [onPageLoadSuccess, pageNumber],
  );

  return (
    <Page
      pageNumber={pageNumber}
      width={renderWidth}
      onLoadSuccess={handleLoadSuccess}
      loading={<Loading />}
      renderTextLayer
      renderAnnotationLayer={false}
    />
  );
});

function normalizeForMatch(text: string): string {
  return text
    .toLowerCase()
    .replace(/[\r\n\t]+/g, " ")
    .replace(/[\u00ad\u2010\u2011\u2012\u2013\u2014-]/gu, "")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildSnippetCandidates(snippet: string): string[] {
  const parts = snippet
    .split(/(?<=[.!?])\s+|\n+/)
    .map((part) => normalizeForMatch(part))
    .filter((part) => part.length >= MIN_TEXT_MATCH_CHARS);

  if (parts.length > 0) {
    return [...parts].sort((a, b) => b.length - a.length);
  }

  const normalized = normalizeForMatch(snippet);
  if (!normalized) return [];

  const words = normalized.split(" ").filter(Boolean);
  const windows: string[] = [];
  for (let i = 0; i < words.length; i += 1) {
    const window = words.slice(i, i + 10).join(" ");
    if (window.length >= MIN_TEXT_MATCH_CHARS) {
      windows.push(window);
    }
  }

  return windows.length > 0 ? windows : [normalized];
}

function highlightSnippetInPage(
  pageNode: HTMLDivElement,
  snippet: string,
  citationLabel?: string,
): HTMLElement | null {
  const textLayer = pageNode.querySelector(".react-pdf__Page__textContent");
  if (!(textLayer instanceof HTMLElement)) return null;

  // Remove previous overlay
  const prev = pageNode.querySelector(".pdf-citation-box");
  if (prev) prev.remove();

  const spans = Array.from(textLayer.querySelectorAll("span")).filter(
    (node): node is HTMLSpanElement => node instanceof HTMLSpanElement,
  );
  if (spans.length === 0) return null;

  const normalizedPieces: string[] = [];
  const charToSpan: number[] = [];

  let previousEndedWithHyphen = false;
  spans.forEach((span, spanIndex) => {
    const rawText = span.textContent ?? "";
    const normalized = normalizeForMatch(span.textContent ?? "");
    if (!normalized) return;

    const startsWithLetterOrDigit = /^\p{L}|\p{N}/u.test(normalized);
    if (
      normalizedPieces.length > 0 &&
      !(previousEndedWithHyphen && startsWithLetterOrDigit)
    ) {
      normalizedPieces.push(" ");
      charToSpan.push(spanIndex);
    }

    normalizedPieces.push(normalized);
    for (let i = 0; i < normalized.length; i += 1) {
      charToSpan.push(spanIndex);
    }

    previousEndedWithHyphen = /[\u00ad\u2010\u2011\u2012\u2013\u2014-]\s*$/u.test(rawText);
  });

  const normalizedText = normalizedPieces.join("");
  if (!normalizedText) return null;

  const candidates = buildSnippetCandidates(snippet);
  for (const candidate of candidates) {
    const start = normalizedText.indexOf(candidate);
    if (start === -1) continue;

    const end = start + candidate.length - 1;
    const matchedIndices = new Set<number>();
    for (let i = start; i <= end; i += 1) {
      const spanIndex = charToSpan[i];
      if (typeof spanIndex === "number") {
        matchedIndices.add(spanIndex);
      }
    }

    const matchedSpans = Array.from(matchedIndices)
      .sort((a, b) => a - b)
      .map((index) => spans[index]);

    if (matchedSpans.length === 0) continue;

    // Compute bounding rect relative to the page container
    const pageRect = pageNode.getBoundingClientRect();
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const span of matchedSpans) {
      const r = span.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      minX = Math.min(minX, r.left - pageRect.left);
      minY = Math.min(minY, r.top - pageRect.top);
      maxX = Math.max(maxX, r.right - pageRect.left);
      maxY = Math.max(maxY, r.bottom - pageRect.top);
    }

    if (!isFinite(minX)) continue;

    const pad = 4;
    const box = document.createElement("div");
    box.className = "pdf-citation-box";
    box.style.cssText = [
      "position:absolute",
      "pointer-events:none",
      `left:${minX - pad}px`,
      `top:${minY - pad}px`,
      `width:${maxX - minX + pad * 2}px`,
      `height:${maxY - minY + pad * 2}px`,
      "border:2px solid rgba(59,130,246,0.5)",
      "border-radius:6px",
      "background:rgba(59,130,246,0.06)",
    ].join(";");

    // Badge
    const badge = document.createElement("div");
    badge.style.cssText = [
      "position:absolute",
      "left:-2px",
      "top:-22px",
      "display:inline-flex",
      "align-items:center",
      "border-radius:9999px",
      "background:rgba(37,99,235,0.92)",
      "color:#eff6ff",
      "padding:1px 7px",
      "font-size:10px",
      "font-weight:700",
      "letter-spacing:0.04em",
      "white-space:nowrap",
      "box-shadow:0 4px 14px rgba(15,23,42,0.18)",
    ].join(";");
    badge.textContent = citationLabel ?? "Citation";
    box.appendChild(badge);

    pageNode.appendChild(box);
    return box;
  }

  return null;
}

export default function PdfViewer() {
  const {
    books,
    currentBookId,
    currentPage,
    selectedSource,
    selectedSourceNonce,
    pdfVariant,
    showToc,
  } =
    useAppState();
  const dispatch = useAppDispatch();

  const [numPages, setNumPages] = useState(0);
  const [pageDimsByPage, setPageDimsByPage] = useState<
    Record<number, { width: number; height: number }>
  >({});
  const [tocEntries, setTocEntries] = useState<TocEntry[]>([]);
  const [tocWidth, setTocWidth] = useState(260);
  const [selectedTocEntryId, setSelectedTocEntryId] = useState<number | null>(null);
  const [renderWidth, setRenderWidth] = useState(0);
  const [zoomScale, setZoomScale] = useState(1);
  const [isViewerHovered, setIsViewerHovered] = useState(false);
  const [renderedPages, setRenderedPages] = useState<Set<number>>(new Set([1]));
  const [loadedPages, setLoadedPages] = useState<Set<number>>(new Set());

  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const pageFrameRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef(new Map<number, HTMLDivElement>());

  const currentPageRef = useRef(currentPage);
  const skipNextScrollRef = useRef(false);
  const didFitPageRef = useRef(false);
  const matchedTextNonceRef = useRef<number | null>(null);
  const pendingPageJumpRef = useRef<{
    pageNumber: number;
    nonce: number;
  } | null>(null);
  const pendingSourceScrollRef = useRef<{
    pageNumber: number;
    hasBbox: boolean;
    nonce: number;
  } | null>(null);

  const hasToc = tocEntries.length > 0;

  // Map Payload numeric ID → engine string book_id for PDF/TOC APIs
  const engineBookId = useMemo(
    () => books.find((b) => b.id === currentBookId)?.book_id ?? null,
    [books, currentBookId],
  );

  const pdfUrl = useMemo(
    () => (engineBookId ? getPdfUrl(engineBookId, pdfVariant) : ""),
    [engineBookId, pdfVariant],
  );

  const pageNumbers = useMemo(
    () => Array.from({ length: numPages }, (_, index) => index + 1),
    [numPages],
  );
  const activeTocEntryId = useMemo(() => {
    if (selectedTocEntryId !== null) {
      const selectedEntry = tocEntries.find((entry) => entry.id === selectedTocEntryId);
      if (selectedEntry?.pdf_page === currentPage) {
        return selectedTocEntryId;
      }
    }

    let activeId: number | null = null;
    for (const entry of tocEntries) {
      if (entry.pdf_page <= currentPage) {
        activeId = entry.id;
      } else {
        break;
      }
    }

    return activeId;
  }, [currentPage, selectedTocEntryId, tocEntries]);

  const markPagesRendered = useCallback((centerPage: number, radius: number) => {
    setRenderedPages((prev) => {
      const next = new Set(prev);
      const start = Math.max(1, centerPage - radius);
      const end = Math.min(numPages || centerPage + radius, centerPage + radius);

      for (let page = start; page <= end; page += 1) {
        next.add(page);
      }

      return next;
    });
  }, [numPages]);

  const setPageNode = useCallback((pageNumber: number, node: HTMLDivElement | null) => {
    if (node) {
      pageRefs.current.set(pageNumber, node);
      return;
    }

    pageRefs.current.delete(pageNumber);
  }, []);



  const clampZoom = useCallback((value: number) => {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100));
  }, []);

  const applyZoom = useCallback(
    (delta: number) => {
      setZoomScale((prev) => clampZoom(prev + delta));
    },
    [clampZoom],
  );

  const resetZoom = useCallback(() => {
    setZoomScale(1);
  }, []);

  useEffect(() => {
    currentPageRef.current = currentPage;
  }, [currentPage]);

  useEffect(() => {
    if (!currentBookId) {
      setTocEntries([]);
      return;
    }

    setPageDimsByPage({});
    setNumPages(0);
    setRenderWidth(0);
    setZoomScale(1);
    setSelectedTocEntryId(null);
    setRenderedPages(new Set([1]));
    setLoadedPages(new Set());
    pageRefs.current.clear();

    didFitPageRef.current = false;
    matchedTextNonceRef.current = null;
    pendingPageJumpRef.current = null;
    pendingSourceScrollRef.current = null;

    if (engineBookId) fetchToc(engineBookId).then(setTocEntries).catch(() => setTocEntries([]));
  }, [currentBookId, pdfVariant]);

  useEffect(() => {
    if (renderWidth > 0) return;

    const node = pageFrameRef.current;
    if (!node) return;

    const updateWidth = () => {
      const next = Math.max(0, Math.floor(node.clientWidth - HORIZONTAL_GUTTER));
      if (next > 0) {
        setRenderWidth(next);
      }
    };

    updateWidth();

    const observer = new ResizeObserver(() => updateWidth());
    observer.observe(node);

    return () => observer.disconnect();
  }, [hasToc, renderWidth, showToc, tocWidth]);

  useEffect(() => {
    const viewport = scrollViewportRef.current;
    if (!viewport || pageNumbers.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let bestPage: number | null = null;
        let bestRatio = 0;

        for (const entry of entries) {
          if (!entry.isIntersecting) continue;

          const pageNumber = Number((entry.target as HTMLElement).dataset.pageNumber);
          startTransition(() => {
            markPagesRendered(pageNumber, VISIBLE_RENDER_RADIUS);
          });
          if (entry.intersectionRatio > bestRatio) {
            bestRatio = entry.intersectionRatio;
            bestPage = pageNumber;
          }
        }

        if (
          bestPage !== null &&
          pendingPageJumpRef.current &&
          bestPage !== pendingPageJumpRef.current.pageNumber
        ) {
          return;
        }

        if (bestPage !== null && bestPage !== currentPageRef.current) {
          skipNextScrollRef.current = true;
          dispatch({ type: "SET_PAGE", page: bestPage });
        }
      },
      {
        root: viewport,
        threshold: [0.25, 0.5, 0.75],
        rootMargin: "-15% 0px -35% 0px",
      },
    );

    for (const pageNumber of pageNumbers) {
      const node = pageRefs.current.get(pageNumber);
      if (node) observer.observe(node);
    }

    return () => observer.disconnect();
  }, [dispatch, markPagesRendered, pageNumbers]);

  useEffect(() => {
    if (numPages === 0) return;

    startTransition(() => {
      markPagesRendered(currentPage, INITIAL_RENDER_RADIUS);
    });
  }, [currentPage, markPagesRendered, numPages]);

  useEffect(() => {
    const target = pageRefs.current.get(currentPage);
    if (!target) return;

    if (
      skipNextScrollRef.current &&
      pendingPageJumpRef.current?.pageNumber !== currentPage
    ) {
      skipNextScrollRef.current = false;
      return;
    }

    target.scrollIntoView({
      block: "start",
      inline: "nearest",
      behavior: "smooth",
    });

    if (pendingPageJumpRef.current?.pageNumber === currentPage) {
      window.setTimeout(() => {
        if (pendingPageJumpRef.current?.pageNumber === currentPage) {
          pendingPageJumpRef.current = null;
        }
      }, 250);
    }
  }, [currentPage]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;

      const viewport = scrollViewportRef.current;
      const activeElement = document.activeElement;
      const isActiveInViewer =
        viewport !== null &&
        activeElement instanceof Node &&
        viewport.contains(activeElement);

      if (!isViewerHovered && !isActiveInViewer) return;

      if (event.key === "0") {
        event.preventDefault();
        resetZoom();
        return;
      }

      if (event.key === "=" || event.key === "+") {
        event.preventDefault();
        applyZoom(ZOOM_STEP);
        return;
      }

      if (event.key === "-") {
        event.preventDefault();
        applyZoom(-ZOOM_STEP);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [applyZoom, isViewerHovered, resetZoom]);

  useEffect(() => {
    const viewport = scrollViewportRef.current;
    if (!viewport) return;

    const handleWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      if (!isViewerHovered) return;

      event.preventDefault();
      applyZoom(event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP);
    };

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [applyZoom, isViewerHovered]);

  useEffect(() => {
    if (!selectedSource) return;
    // Allow highlight if book matches (by engine ID or if already on the correct book)
    const bookMatches = !selectedSource.book_id_string || selectedSource.book_id_string === engineBookId;
    if (!bookMatches) return;

    pendingSourceScrollRef.current = {
      pageNumber: selectedSource.page_number,
      hasBbox: Boolean(selectedSource.bbox),
      nonce: selectedSourceNonce,
    };
    matchedTextNonceRef.current = null;
    pendingPageJumpRef.current = {
      pageNumber: selectedSource.page_number,
      nonce: selectedSourceNonce,
    };
    skipNextScrollRef.current = false;
    startTransition(() => {
      markPagesRendered(selectedSource.page_number, VISIBLE_RENDER_RADIUS);
    });
  }, [
    currentBookId,
    markPagesRendered,
    selectedSource,
    selectedSource?.bbox,
    selectedSource?.book_id,
    selectedSource?.page_number,
    selectedSourceNonce,
  ]);

  useEffect(() => {
    const pending = pendingSourceScrollRef.current;
    if (!pending) return;

    const pageNode = pageRefs.current.get(pending.pageNumber);
    if (!pageNode) return;

    pageNode.scrollIntoView({
      block: "start",
      inline: "nearest",
      behavior: "smooth",
    });

    if (!pending.hasBbox) {
      pendingSourceScrollRef.current = null;
    }
  }, [
    currentPage,
    numPages,
    renderedPages,
    selectedSourceNonce,
  ]);

  useEffect(() => {
    if (!selectedSource?.snippet) return;
    // Allow highlight if book matches (by engine ID or if already on the correct book)
    const highlightBookMatches = !selectedSource.book_id_string || selectedSource.book_id_string === engineBookId;
    if (!highlightBookMatches) return;

    // Remove any previous citation box on other pages
    for (const node of pageRefs.current.values()) {
      const old = node.querySelector(".pdf-citation-box");
      if (old) old.remove();
    }

    const pageNode = pageRefs.current.get(selectedSource.page_number);
    if (!pageNode) return;

    const tryHighlight = () => {
      const firstMatch = highlightSnippetInPage(
        pageNode,
        selectedSource.snippet,
        selectedSource.citation_label,
      );
      if (!firstMatch) return false;

      matchedTextNonceRef.current = selectedSourceNonce;
      firstMatch.scrollIntoView({
        block: "center",
        inline: "nearest",
        behavior: "smooth",
      });
      pendingSourceScrollRef.current = null;
      return true;
    };

    if (tryHighlight()) return;

    const observer = new MutationObserver(() => {
      if (tryHighlight()) {
        observer.disconnect();
      }
    });

    observer.observe(pageNode, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [
    currentBookId,
    loadedPages,
    renderedPages,
    selectedSource?.book_id,
    selectedSource?.page_number,
    selectedSource?.snippet,
    selectedSourceNonce,
    zoomScale,
  ]);



  const onDocumentLoadSuccess = useCallback(
    ({ numPages: totalPages }: { numPages: number }) => {
      setNumPages(totalPages);
    },
    [],
  );

  const onPageLoadSuccess = useCallback(
    (pageNumber: number, { width, height }: { width: number; height: number }) => {
      setLoadedPages((prev) => {
        if (prev.has(pageNumber)) return prev;
        const next = new Set(prev);
        next.add(pageNumber);
        return next;
      });

      setPageDimsByPage((prev) => {
        const existing = prev[pageNumber];
        if (existing && existing.width === width && existing.height === height) {
          return prev;
        }

        return {
          ...prev,
          [pageNumber]: { width, height },
        };
      });

      if (
        pageNumber === 1 &&
        !didFitPageRef.current &&
        scrollViewportRef.current &&
        pageFrameRef.current
      ) {
        const availableWidth = Math.max(
          0,
          Math.floor(pageFrameRef.current.clientWidth - HORIZONTAL_GUTTER),
        );
        const availableHeight = Math.max(
          0,
          Math.floor(scrollViewportRef.current.clientHeight - VIEWPORT_VERTICAL_PADDING),
        );
        const fitPageWidth = Math.floor((availableHeight * width) / height);
        const nextWidth = Math.max(320, Math.min(availableWidth, fitPageWidth));

        if (nextWidth > 0) {
          didFitPageRef.current = true;
          setRenderWidth(nextWidth);
        }
      }
    },
    [],
  );

  const goToPage = useCallback(
    (page: number) => {
      if (page >= 1 && (!numPages || page <= numPages)) {
        dispatch({ type: "SET_PAGE", page });
      }
    },
    [dispatch, numPages],
  );

  if (!currentBookId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
        Select a textbook to view its PDF
      </div>
    );
  }

  const stableRenderWidth = renderWidth > 0 ? renderWidth : 800;
  const estimatedPageHeight =
    pageDimsByPage[1] && stableRenderWidth
      ? Math.round(
          (pageDimsByPage[1].height / pageDimsByPage[1].width) * stableRenderWidth,
        )
      : Math.round(stableRenderWidth * 1.33);
  const scaledPageGap = Math.max(12, Math.round(PAGE_GAP * zoomScale));

  return (
    <div className="relative flex h-full flex-col bg-background">
      <div className="flex items-center gap-2 border-b border-border bg-card px-3 py-2 text-sm text-card-foreground">
        {hasToc && (
          <button
            className="rounded px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => dispatch({ type: "TOGGLE_TOC" })}
            title="Toggle table of contents"
          >
            ☰
          </button>
        )}
        <button
          className="rounded px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-40"
          disabled={currentPage <= 1}
          onClick={() => goToPage(currentPage - 1)}
        >
          ◀
        </button>
        <span>
          Page{" "}
          <input
            type="number"
            className="w-14 rounded border border-input bg-background px-1 text-center text-foreground"
            min={1}
            max={numPages || undefined}
            value={currentPage}
            onChange={(event) => goToPage(Number(event.target.value))}
          />{" "}
          / {numPages || "…"}
        </span>
        <button
          className="rounded px-2 py-1 hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-40"
          disabled={numPages > 0 && currentPage >= numPages}
          onClick={() => goToPage(currentPage + 1)}
        >
          ▶
        </button>
        <div className="ml-auto flex items-center gap-2">
          <button
            className="rounded px-2 py-0.5 text-xs hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => applyZoom(-ZOOM_STEP)}
            title="Zoom out"
          >
            −
          </button>
          <button
            className="min-w-[3.5rem] rounded px-2 py-0.5 text-center text-xs hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={resetZoom}
            title="Reset zoom"
          >
            {Math.round(zoomScale * 100)}%
          </button>
          <button
            className="rounded px-2 py-0.5 text-xs hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => applyZoom(ZOOM_STEP)}
            title="Zoom in"
          >
            +
          </button>
          <span className="mx-1 text-border">|</span>
          <span className="text-muted-foreground text-xs">PDF:</span>
          <button
            className={`rounded px-2 py-0.5 text-xs transition-colors ${pdfVariant === "origin" ? "bg-primary text-primary-foreground" : "hover:bg-accent hover:text-accent-foreground"}`}
            onClick={() =>
              dispatch({ type: "SET_PDF_VARIANT", variant: "origin" })
            }
          >
            Original
          </button>
          <button
            className={`rounded px-2 py-0.5 text-xs transition-colors ${pdfVariant === "layout" ? "bg-primary text-primary-foreground" : "hover:bg-accent hover:text-accent-foreground"}`}
            onClick={() =>
              dispatch({ type: "SET_PDF_VARIANT", variant: "layout" })
            }
          >
            Layout
          </button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {hasToc && showToc && (
          <>
            <div
              className="shrink-0 overflow-y-auto bg-card border-r border-border p-2 text-xs"
              style={{ width: tocWidth }}
            >
              <div className="mb-2 font-semibold text-foreground">Contents</div>
              {tocEntries.map((entry) => {
                const indent = entry.level * 12;
                const isBold = entry.level <= 1;
                const isActive = entry.id === activeTocEntryId;
                const label = entry.number
                  ? `${entry.number} ${entry.title}`
                  : entry.title;

                return (
                  <button
                    key={entry.id}
                    className={`block w-full truncate rounded py-0.5 pr-1 text-left hover:bg-accent hover:text-accent-foreground transition-colors ${
                      isActive
                        ? "bg-accent/80 font-medium text-foreground"
                        : "text-muted-foreground"
                    } ${isBold ? "font-semibold" : ""}`}
                    style={{ paddingLeft: `${indent + 8}px` }}
                    title={label}
                    onClick={() => {
                      setSelectedTocEntryId(entry.id);
                      goToPage(entry.pdf_page);
                    }}
                  >
                    {label}
                    <span className="ml-1 font-normal opacity-60">
                      {entry.pdf_page}
                    </span>
                  </button>
                );
              })}
            </div>
            <ResizeHandle
              width={tocWidth}
              onResize={setTocWidth}
              min={160}
              max={500}
            />
          </>
        )}

        <div
          ref={scrollViewportRef}
          className="min-h-0 flex-1 overflow-y-auto bg-muted outline-none"
          tabIndex={0}
          onMouseEnter={() => setIsViewerHovered(true)}
          onMouseLeave={() => setIsViewerHovered(false)}
          onMouseDown={(event) => event.currentTarget.focus()}
        >
          <div
            ref={pageFrameRef}
            className="flex min-h-full justify-center px-4 py-5"
          >
            <Document
              key={pdfUrl}
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              loading={<Loading />}
              error={
                <div className="p-4 text-sm text-destructive">Failed to load PDF.</div>
              }
            >
              <div className="flex flex-col items-center" style={{ gap: scaledPageGap }}>
                {pageNumbers.map((pageNumber) => {
                  const pageDims = pageDimsByPage[pageNumber];
                  const shouldRenderPage = renderedPages.has(pageNumber);
                  const isPageLoaded = loadedPages.has(pageNumber);
                  const renderedHeight = pageDims
                    ? Math.round(
                        (pageDims.height / pageDims.width) * stableRenderWidth,
                      )
                    : estimatedPageHeight;
                  const scaledWidth = Math.round(stableRenderWidth * zoomScale);
                  const scaledHeight = renderedHeight
                    ? Math.round(renderedHeight * zoomScale)
                    : undefined;

                  return (
                    <div
                      key={pageNumber}
                      ref={(node) => setPageNode(pageNumber, node)}
                      data-page-number={pageNumber}
                      className={`relative transition-shadow ${
                        pageNumber === currentPage ? "z-10" : ""
                      }`}
                      style={{
                        width: scaledWidth,
                        minHeight: scaledHeight,
                      }}
                    >
                      <div
                        className="absolute left-0 top-0"
                        style={{
                          width: stableRenderWidth,
                          transform: `scale(${zoomScale})`,
                          transformOrigin: "top left",
                        }}
                      >
                          <div
                            className={`relative rounded bg-white shadow-sm ring-1 ring-border ${
                              pageNumber === currentPage
                                ? "shadow-md ring-primary/50 ring-2"
                                : ""
                            }`}
                            style={{ width: stableRenderWidth }}
                          >
                            <div
                              className={`absolute inset-0 rounded bg-gradient-to-br from-muted via-card to-muted transition-opacity duration-500 ${
                                isPageLoaded ? "opacity-0" : "opacity-100"
                              }`}
                            />
                            {shouldRenderPage ? (
                              <div
                                className={`relative transition-all duration-500 ${
                                  isPageLoaded
                                    ? "opacity-100 blur-0"
                                    : "opacity-0 blur-[2px]"
                                }`}
                              >
                                <PdfPageCanvas
                                  pageNumber={pageNumber}
                                  renderWidth={stableRenderWidth}
                                  onPageLoadSuccess={onPageLoadSuccess}
                                />
                              </div>
                            ) : (
                              <div
                                className="relative overflow-hidden rounded bg-gradient-to-br from-muted via-card to-muted"
                                style={{ height: renderedHeight }}
                              >
                                <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_infinite] bg-gradient-to-r from-transparent via-background/40 to-transparent" />
                                <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                                  Page {pageNumber}
                                </div>
                              </div>
                            )}
                            <div className="pointer-events-none absolute right-3 top-3 rounded bg-background/80 px-2 py-0.5 text-[11px] font-medium text-foreground shadow-sm backdrop-blur-[2px]">
                              {pageNumber}
                            </div>

                          </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Document>
          </div>
        </div>
      </div>
    </div>
  );
}
