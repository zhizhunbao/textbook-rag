/**
 * markdownNormalizer — Normalize LLM markdown output before rendering.
 *
 * Sits between raw LLM text and react-markdown to guarantee stable rendering
 * regardless of model-specific formatting quirks.
 *
 * Inspired by DeepTutor's markdown-display.ts (404-line normalizer).
 *
 * Pipeline:
 *   LLM raw text → normalizeMarkdown() → answerBlocks parser → react-markdown
 *
 * Handles:
 *   1. Citation format unification ([Source 5] → [5])
 *   2. Disclaimer extraction (separate from answer body)
 *   3. Unknown HTML tag escaping (LLM pseudo-tags)
 *   4. Zero-width character stripping
 *   5. Empty markdown table removal
 */

// ============================================================
// Constants & Regex
// ============================================================

/** Zero-width characters that LLMs sometimes inject. */
const ZERO_WIDTH_RE = /[\u200B-\u200D\uFEFF]/g;

/**
 * Citation format variants that LLMs produce.
 * All normalized to `[N]` format.
 */
const CITATION_VARIANTS: Array<{ pattern: RegExp; replacement: string }> = [
  // [Source 5], [Source: 5], [source 5]
  { pattern: /\[(?:Source|source)\s*:?\s*(\d+)\]/g, replacement: "[$1]" },
  // (Source 5), (source: 5)
  { pattern: /\((?:Source|source)\s*:?\s*(\d+)\)/g, replacement: "[$1]" },
  // 【5】(fullwidth brackets, common in Chinese LLM output)
  { pattern: /【(\d+)】/g, replacement: "[$1]" },
  // [Ref 5], [ref: 5]
  { pattern: /\[(?:Ref|ref)\s*:?\s*(\d+)\]/g, replacement: "[$1]" },
  // [Citation 5]
  { pattern: /\[(?:Citation|citation)\s*:?\s*(\d+)\]/g, replacement: "[$1]" },
];

/**
 * HTML-like tags we allow through to rehype-raw.
 * Everything else gets escaped to inline code.
 * (Subset — only tags likely in LLM markdown output.)
 */
const ALLOWED_HTML_TAGS = new Set([
  // structural
  "p", "div", "span", "section", "article", "aside",
  // text-level
  "a", "em", "strong", "b", "i", "u", "s", "del", "ins", "small",
  "sub", "sup", "mark", "kbd", "code", "samp", "var", "q", "cite",
  "abbr", "br", "hr", "wbr",
  // lists
  "ol", "ul", "li", "dl", "dt", "dd",
  // headings
  "h1", "h2", "h3", "h4", "h5", "h6",
  // block
  "blockquote", "pre", "figure", "figcaption", "details", "summary",
  // tables
  "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
  // media
  "img", "video", "audio", "source",
]);

const HTML_TAG_RE = /<\/?([A-Za-z][A-Za-z0-9_-]*)\b[^<>]*?\/?>/g;
const CODE_FENCE_RE = /```[\s\S]*?```|`[^`\n]*`/g;
const PLACEHOLDER_RE = /\u0000P_(\d+)\u0000/g;

/**
 * Disclaimer patterns to extract from answer body.
 * These get returned separately so the UI can render them compactly.
 */
const DISCLAIMER_PATTERNS = [
  // Python-appended disclaimer (after ---)
  /\n\n---\n⚠️?\s*\*{0,2}(?:Disclaimer|免责声明)\*{0,2}\s*[:：].*$/s,
  // LLM-generated data notice with ⚠ emoji
  /\n\n⚠️?\s*(?:The above|以上).*?(?:official\s+figures|官方数据)\.?\s*$/s,
];

// ============================================================
// Core normalization functions
// ============================================================

/** Strip zero-width invisible characters. */
function stripInvisible(text: string): string {
  return text.replace(ZERO_WIDTH_RE, "");
}

/** Normalize all citation format variants to `[N]`. */
function normalizeCitations(text: string): string {
  let result = text;

  // Pre-pass: expand comma-separated multi-citations
  //   [Source 1, Source 3]  → [Source 1][Source 3]
  //   [Source 1, 3]         → [Source 1][Source 3]
  //   (Source 1, Source 3)  → (Source 1)(Source 3)
  result = result.replace(
    /\[(?:Source|source)\s*:?\s*(\d+)(?:\s*,\s*(?:Source|source)?\s*:?\s*(\d+))+\]/g,
    (match) => {
      const nums = match.match(/\d+/g) || [];
      return nums.map((n) => `[Source ${n}]`).join("");
    },
  );
  result = result.replace(
    /\((?:Source|source)\s*:?\s*(\d+)(?:\s*,\s*(?:Source|source)?\s*:?\s*(\d+))+\)/g,
    (match) => {
      const nums = match.match(/\d+/g) || [];
      return nums.map((n) => `[Source ${n}]`).join("");
    },
  );

  for (const { pattern, replacement } of CITATION_VARIANTS) {
    // Reset lastIndex for global regex reuse
    pattern.lastIndex = 0;
    result = result.replace(pattern, replacement);
  }
  return result;
}

/**
 * Escape LLM pseudo-tags like <think>, <tool_call>, <answer>.
 * Protects code fences first, then escapes unknown tags into inline code.
 */
function escapeUnknownTags(text: string): string {
  if (!text.includes("<")) return text;

  // Protect code fences from modification
  const protected_: string[] = [];
  const masked = text.replace(CODE_FENCE_RE, (match) => {
    protected_.push(match);
    return `\u0000P_${protected_.length - 1}\u0000`;
  });

  // Escape unknown HTML-like tags
  const escaped = masked.replace(HTML_TAG_RE, (match, name: string) => {
    return ALLOWED_HTML_TAGS.has(name.toLowerCase()) ? match : `\`${match}\``;
  });

  // Restore protected code fences
  return escaped.replace(
    PLACEHOLDER_RE,
    (_, idx: string) => protected_[Number(idx)] ?? "",
  );
}

/**
 * Detect and remove empty markdown tables.
 * LLMs sometimes generate table headers with no data rows.
 */
function removeEmptyTables(text: string): string {
  const lines = text.split("\n");
  const cleaned: string[] = [];

  for (let i = 0; i < lines.length; ) {
    const line = lines[i].trim();
    // Detect table start: header row with | followed by separator row
    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(lines[i + 1].trim())
    ) {
      // Count columns from header
      const colCount = line.split("|").length;
      let end = i + 2;

      // Find end of table
      while (
        end < lines.length &&
        lines[end].trim().includes("|") &&
        lines[end].trim().split("|").length === colCount
      ) {
        end++;
      }

      // Check if table has any non-empty data cells
      const dataRows = lines.slice(i + 2, end);
      const hasData = dataRows.some((row) =>
        row
          .split("|")
          .some((cell) => cell.trim().replace(/\s/g, "").length > 0),
      );

      if (hasData || dataRows.length > 0) {
        // Keep the table
        for (let j = i; j < end; j++) cleaned.push(lines[j]);
      }
      // else: skip empty table entirely
      i = end;
    } else {
      cleaned.push(lines[i]);
      i++;
    }
  }

  return cleaned.join("\n");
}

/**
 * Extract disclaimer blocks from answer text.
 * Returns the cleaned answer and any extracted disclaimers.
 */
export function extractDisclaimers(text: string): {
  answer: string;
  disclaimers: string[];
} {
  let answer = text;
  const disclaimers: string[] = [];

  for (const pattern of DISCLAIMER_PATTERNS) {
    const match = answer.match(pattern);
    if (match) {
      disclaimers.push(match[0].trim().replace(/^---\n/, ""));
      answer = answer.replace(pattern, "");
    }
  }

  return { answer: answer.trimEnd(), disclaimers };
}

// ============================================================
// Public API
// ============================================================

export interface NormalizedMarkdown {
  /** Cleaned answer text, ready for react-markdown. */
  content: string;
  /** Extracted disclaimer blocks (render separately in compact UI). */
  disclaimers: string[];
}

/**
 * Normalize raw LLM markdown output for stable rendering.
 *
 * Call this BEFORE passing text to answerBlocks parser or react-markdown.
 *
 * @example
 * ```ts
 * import { normalizeMarkdown } from "@/features/shared/markdownNormalizer";
 *
 * const { content, disclaimers } = normalizeMarkdown(llmRawText);
 * const blocks = parseAnswerBlocks(content);
 * ```
 */
export function normalizeMarkdown(raw: string): NormalizedMarkdown {
  if (!raw?.trim()) return { content: "", disclaimers: [] };

  let text = raw;

  // 1. Strip invisible characters
  text = stripInvisible(text);

  // 2. Normalize line endings
  text = text.replace(/\r\n/g, "\n");

  // 3. Normalize citation formats → [N]
  text = normalizeCitations(text);

  // 4. Escape unknown HTML tags (LLM pseudo-tags)
  text = escapeUnknownTags(text);

  // 5. Remove empty tables
  text = removeEmptyTables(text);

  // 6. Collapse excessive blank lines
  text = text.replace(/\n{3,}/g, "\n\n");

  // 7. Extract disclaimers
  const { answer, disclaimers } = extractDisclaimers(text);

  return { content: answer.trim(), disclaimers };
}
