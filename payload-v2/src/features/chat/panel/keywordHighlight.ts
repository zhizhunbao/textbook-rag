/**
 * keywordHighlight — Lightweight UI-only rendering utility.
 *
 * ALL extraction + source cross-referencing is handled server-side:
 *   - Keyword extraction: spaCy NLP (engine_v2/consulting/keyword_extractor.py)
 *   - Numeric extraction: regex + source verification (same file)
 *
 * This file provides:
 *   1. Color palettes and types (KeywordEntry, NumericHighlight)
 *   2. injectHighlightMarks() — wraps keyword matches with <mark> tags
 *   3. injectNumericMarks()   — wraps backend-classified numbers with <mark> tags
 *      (colored = verified in sources, gray = unverified / LLM-generated)
 */

// ── Curated highlight palette (soft, accessible on both light/dark) ──
export const HIGHLIGHT_COLORS = [
  { bg: 'rgba(99, 102, 241, 0.18)',  text: 'rgb(99, 102, 241)',   border: 'rgba(99, 102, 241, 0.35)'  },  // indigo
  { bg: 'rgba(236, 72, 153, 0.18)',  text: 'rgb(236, 72, 153)',   border: 'rgba(236, 72, 153, 0.35)'  },  // pink
  { bg: 'rgba(34, 197, 94, 0.18)',   text: 'rgb(34, 197, 94)',    border: 'rgba(34, 197, 94, 0.35)'   },  // green
  { bg: 'rgba(245, 158, 11, 0.18)',  text: 'rgb(245, 158, 11)',   border: 'rgba(245, 158, 11, 0.35)'  },  // amber
  { bg: 'rgba(6, 182, 212, 0.18)',   text: 'rgb(6, 182, 212)',    border: 'rgba(6, 182, 212, 0.35)'   },  // cyan
  { bg: 'rgba(168, 85, 247, 0.18)',  text: 'rgb(168, 85, 247)',   border: 'rgba(168, 85, 247, 0.35)'  },  // purple
  { bg: 'rgba(239, 68, 68, 0.18)',   text: 'rgb(239, 68, 68)',    border: 'rgba(239, 68, 68, 0.35)'   },  // red
  { bg: 'rgba(14, 165, 233, 0.18)',  text: 'rgb(14, 165, 233)',   border: 'rgba(14, 165, 233, 0.35)'  },  // sky
] as const;

export type HighlightColor = { bg: string; text: string; border: string };

export interface KeywordEntry {
  /** The keyword or phrase to highlight (lowercase for matching) */
  keyword: string;
  /** Display form (preserves casing from original question) */
  display: string;
  /** Assigned color from the palette */
  color: HighlightColor;
}

// ── Shared helpers ──────────────────────────────────────────

type Region = { start: number; end: number };

/** Collect regions from regex matches. */
function _collectRegions(text: string, patterns: RegExp[]): Region[] {
  const regions: Region[] = [];
  for (const pat of patterns) {
    let m: RegExpExecArray | null;
    while ((m = pat.exec(text)) !== null) {
      regions.push({ start: m.index, end: m.index + m[0].length });
    }
  }
  return regions;
}

/** Check if a range overlaps with any protected region. */
function _isProtected(start: number, end: number, regions: Region[]): boolean {
  return regions.some(
    (r) => (start >= r.start && start < r.end) ||
           (end > r.start && end <= r.end) ||
           (start <= r.start && end >= r.end),
  );
}

/** Check if a range overlaps with any already-highlighted range. */
function _overlaps(start: number, end: number, ranges: Region[]): boolean {
  return ranges.some((r) => start < r.end && end > r.start);
}

// Numeric protect patterns — shared by both keyword and numeric highlighters.
// Prevents keyword highlighting from splitting numbers at comma boundaries.
const _NUMERIC_PROTECT: RegExp[] = [
  /Q[1-4]\s*\d{4}/gi,                              // Q4 2021
  /[+-]?\d+(?:,\d{3})*(?:\.\d+)?\s?%/g,            // 36.2%, +9.8%
  /\\?\$\d+(?:,\d{3})*(?:\.\d+)?/g,                 // $671,248 or \$671,248
  /\d{1,3}(?:,\d{3})+(?:\.\d+)?/g,                  // 1,882
  /[+-]\d+(?:,\d{3})*(?:\.\d+)?/g,                  // +3.8, -1.3
  /\d+\.\d+/g,                                       // 3.8, 6.0
];

// ── Keyword highlighting ────────────────────────────────────

/**
 * Wrap keyword matches in the text with `<mark>` tags.
 * Preserves the original casing of the matched text in the content.
 *
 * Avoids highlighting inside:
 *   - Existing HTML tags, citation markers [1], LaTeX delimiters
 *   - Markdown link URLs, numeric values (prevents splitting numbers)
 */
export function injectHighlightMarks(
  text: string,
  keywords: KeywordEntry[],
): string {
  if (!keywords.length || !text) return text;

  // Build set of keyword texts (lowercase) so we can skip numeric-protect
  // for regions that ARE themselves explicit keywords from the backend.
  // e.g., "Q4 2024" is both a numeric-protect pattern AND a keyword —
  // the backend explicitly extracted it, so it should be highlighted.
  const keywordTextsLower = new Set(keywords.map((k) => k.keyword));

  // Build protected regions
  const rawProtected = _collectRegions(text, [
    /\[([^\]]*)\]\(([^)]*)\)/g,   // markdown link URLs (protect URL part)
    /\[\d+\]/g,                    // citation markers [1], [2]
    /\$\$[\s\S]*?\$\$|\$[^$\n]+?\$/g,  // LaTeX
    ..._NUMERIC_PROTECT,           // numeric values
  ]);

  // Filter out protected regions that exactly match a keyword
  // (the backend explicitly extracted these, so they should be highlighted)
  const protectedRegions = rawProtected.filter((region) => {
    const regionText = text.slice(region.start, region.end).toLowerCase();
    return !keywordTextsLower.has(regionText);
  });

  // Sort keywords by length descending so longer phrases match first
  const sorted = [...keywords].sort((a, b) => b.keyword.length - a.keyword.length);

  // Build a combined regex for all keywords (longest first)
  const escapedKeywords = sorted.map((k) =>
    k.keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
  );
  const combinedRegex = new RegExp(`(${escapedKeywords.join('|')})`, 'gi');

  const highlightedRanges: Region[] = [];
  const matches: Array<{
    index: number;
    length: number;
    matched: string;
    keyword: KeywordEntry;
  }> = [];

  let match: RegExpExecArray | null;
  while ((match = combinedRegex.exec(text)) !== null) {
    const matchedText = match[0];
    const idx = match.index;
    const end = idx + matchedText.length;

    if (_isProtected(idx, end, protectedRegions)) continue;

    // Word boundary check (avoids \b issues with unicode)
    const charBefore = idx > 0 ? text[idx - 1] : ' ';
    const charAfter = end < text.length ? text[end] : ' ';
    const isBoundaryBefore = /[\s,.:;!?()[\]{}"'`\-/]/.test(charBefore) || idx === 0;
    const isBoundaryAfter = /[\s,.:;!?()[\]{}"'`\-/]/.test(charAfter) || end === text.length;
    if (!isBoundaryBefore || !isBoundaryAfter) continue;

    if (_overlaps(idx, end, highlightedRanges)) continue;

    const kw = sorted.find((k) => k.keyword === matchedText.toLowerCase());
    if (!kw) continue;

    matches.push({ index: idx, length: matchedText.length, matched: matchedText, keyword: kw });
    highlightedRanges.push({ start: idx, end });
  }

  if (matches.length === 0) return text;

  matches.sort((a, b) => a.index - b.index);

  let result = '';
  let lastEnd = 0;
  for (const m of matches) {
    result += text.slice(lastEnd, m.index);
    result += `<mark style="background:${m.keyword.color.bg};color:${m.keyword.color.text};padding:1px 4px;border-radius:3px;border-bottom:2px solid ${m.keyword.color.border};font-weight:500;">${m.matched}</mark>`;
    lastEnd = m.index + m.length;
  }
  result += text.slice(lastEnd);

  return result;
}

// ── Numeric data value highlighting (backend-driven) ────────

/** Backend-provided numeric highlight entry. */
export interface NumericHighlight {
  /** The matched numeric value (e.g. "9.8%", "$801,524", "3,941") */
  text: string;
  /** True if found in source texts, False if LLM-generated */
  verified: boolean;
  /** Character offset in the answer text */
  offset: number;
}

/** Curated palette for verified numeric values.
 *  Each distinct number gets its own color so users can visually
 *  distinguish different data points at a glance.
 *  Uses dashed borders to stay visually distinct from keyword highlights. */
const NUMERIC_COLORS = [
  { bg: 'rgba(225,29,72,0.12)',   text: 'rgb(225,29,72)',   border: 'rgba(225,29,72,0.40)'   },  // rose
  { bg: 'rgba(37,99,235,0.12)',   text: 'rgb(37,99,235)',   border: 'rgba(37,99,235,0.40)'   },  // blue
  { bg: 'rgba(22,163,74,0.12)',   text: 'rgb(22,163,74)',   border: 'rgba(22,163,74,0.40)'   },  // green
  { bg: 'rgba(217,119,6,0.12)',   text: 'rgb(217,119,6)',   border: 'rgba(217,119,6,0.40)'   },  // amber
  { bg: 'rgba(124,58,237,0.12)',  text: 'rgb(124,58,237)',  border: 'rgba(124,58,237,0.40)'  },  // violet
  { bg: 'rgba(14,165,233,0.12)',  text: 'rgb(14,165,233)',  border: 'rgba(14,165,233,0.40)'  },  // sky
  { bg: 'rgba(236,72,153,0.12)',  text: 'rgb(236,72,153)',  border: 'rgba(236,72,153,0.40)'  },  // pink
  { bg: 'rgba(20,184,166,0.12)',  text: 'rgb(20,184,166)',  border: 'rgba(20,184,166,0.40)'  },  // teal
  { bg: 'rgba(245,158,11,0.12)',  text: 'rgb(245,158,11)',  border: 'rgba(245,158,11,0.40)'  },  // yellow
  { bg: 'rgba(168,85,247,0.12)',  text: 'rgb(168,85,247)',  border: 'rgba(168,85,247,0.40)'  },  // purple
] as const;

/** Style for unverified numeric values — muted slate (not in sources). */
const NUMERIC_UNVERIFIED = {
  bg: 'rgba(148,163,184,0.10)',
  text: 'rgb(148,163,184)',
  border: 'rgba(148,163,184,0.25)',
} as const;

/** Normalize a numeric value for consistent color mapping.
 *  Strips sign, $, spaces, trailing zeros so '-17.8%' and '$17.8 %' share the same key. */
function _normalizeNumericKey(text: string): string {
  return text
    .replace(/\s+/g, '')
    .replace(/^[+-]/, '')
    .replace(/^\$|^\\?\$/g, '')
    .replace(/(\.[0-9]*[1-9])0+(?=[^0-9]|$)/g, '$1')
    .replace(/(\d)\.0+(?=[^0-9]|$)/g, '$1')
    .toLowerCase();
}

/** Build a deterministic color map from answer-level numeric highlights.
 *  Call once per message, share across question/answer/citation panels
 *  so the same numeric value always gets the same color everywhere. */
export type NumericColorMap = Map<string, typeof NUMERIC_COLORS[number]>;
export function buildNumericColorMap(highlights: NumericHighlight[]): NumericColorMap {
  const map = new Map<string, typeof NUMERIC_COLORS[number]>();
  let idx = 0;
  for (const h of highlights) {
    if (!h.verified) continue;
    const key = _normalizeNumericKey(h.text);
    if (!map.has(key)) {
      map.set(key, NUMERIC_COLORS[idx % NUMERIC_COLORS.length]);
      idx++;
    }
  }
  return map;
}

/**
 * Inject `<mark>` tags for numeric data values using backend-provided highlights.
 *
 * Color assignment:
 *   - Unverified → gray (always)
 *   - Verified   → distinct color per unique numeric value
 */
export function injectNumericMarks(
  text: string,
  highlights: NumericHighlight[],
  options?: { colorMap?: NumericColorMap },
): string {
  if (!text || !highlights?.length) return text;

  const colorMap = options?.colorMap ?? buildNumericColorMap(highlights);

  // Protect HTML tags (prevents matching numbers in style="rgba(...)")
  const protectedRegions = _collectRegions(text, [
    /<mark[^>]*>[\s\S]*?<\/mark>/gi,  // full <mark> blocks
    /<[^>]+>/gi,                       // all HTML tags
  ]);

  const matches: Array<{ index: number; length: number; text: string; verified: boolean }> = [];
  const highlightedRanges: Region[] = [];

  for (const h of highlights) {
    // Skip very short values (single digits cause massive false positives)
    if (h.text.replace(/\s+/g, '').length < 2) continue;

    const escaped = h.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(escaped, 'g');
    let match: RegExpExecArray | null;
    while ((match = regex.exec(text)) !== null) {
      const idx = match.index;
      const end = idx + match[0].length;
      if (_isProtected(idx, end, protectedRegions)) continue;
      if (_overlaps(idx, end, highlightedRanges)) continue;

      // Boundary check: don't match inside larger numbers
      const cBefore = idx > 0 ? text[idx - 1] : '';
      const cAfter = end < text.length ? text[end] : '';
      if (/\d/.test(cBefore) || /\d/.test(cAfter)) continue;

      matches.push({ index: idx, length: match[0].length, text: match[0], verified: h.verified });
      highlightedRanges.push({ start: idx, end });
    }
  }

  if (matches.length === 0) return text;

  matches.sort((a, b) => a.index - b.index);

  let result = '';
  let lastEnd = 0;
  for (const m of matches) {
    const style = m.verified
      ? (colorMap.get(_normalizeNumericKey(m.text)) ?? NUMERIC_COLORS[0])
      : NUMERIC_UNVERIFIED;
    result += text.slice(lastEnd, m.index);
    result += `<mark style="background:${style.bg};color:${style.text};padding:1px 3px;border-radius:3px;border-bottom:2px dashed ${style.border};font-weight:600;font-variant-numeric:tabular-nums;" title="${m.verified ? '✓ Verified in source' : '? Not found in sources'}">${m.text}</mark>`;
    lastEnd = m.index + m.length;
  }
  result += text.slice(lastEnd);

  return result;
}
