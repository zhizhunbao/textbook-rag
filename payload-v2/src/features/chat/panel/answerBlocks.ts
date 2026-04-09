/**
 * answerBlocks — Parse LLM output into semantic AnswerBlocks.
 *
 * Splits continuous text into paragraphs (by \n\n), extracts ALL
 * [N] citation markers from each paragraph, and returns an array of
 * AnswerBlock objects for structured rendering in MessageBubble.
 *
 * Usage: const blocks = parseAnswerBlocks(llmText)
 */

// ============================================================
// Types
// ============================================================

/** A single semantic paragraph with its bound citations. */
export interface AnswerBlock {
  /** Paragraph text with [N] markers removed. */
  text: string;
  /** Citation indices extracted from the paragraph. */
  citationIndices: number[];
}

// ============================================================
// Constants
// ============================================================

/**
 * Regex to find ALL [N] or [N.N.N] markers anywhere in a paragraph.
 * The captured group contains the full number (e.g. "3", "3.2", "3.2.2").
 */
const ALL_CITATIONS_RE = /\[(\d+(?:\.\d+)*)\]/g;

// ============================================================
// Parser
// ============================================================

/**
 * Parse LLM output text into an array of AnswerBlocks.
 *
 * Rules:
 *   1. Split by double newline (\n\n) into raw paragraphs.
 *   2. For each paragraph, extract ALL [N] markers into citationIndices
 *      and remove them from the displayed text.
 *   3. Consecutive Markdown headings (## / ###) are merged with the
 *      following paragraph so headings are not rendered as standalone blocks.
 *   4. Empty input returns [].
 *   5. If no \n\n split is possible, return a single block (fallback).
 *   6. Dotted citations like [3.2] are mapped to their integer part (3).
 */
export function parseAnswerBlocks(text: string): AnswerBlock[] {
  if (!text || !text.trim()) return [];

  // Split into raw paragraphs by double newline
  const rawParagraphs = text.split(/\n\n+/);

  const merged: string[] = [];
  let pendingHeading = "";

  for (const para of rawParagraphs) {
    const trimmed = para.trim();
    if (!trimmed) continue;

    // Detect Markdown headings (## or ###)
    if (/^#{2,3}\s+/.test(trimmed)) {
      // Accumulate heading — will be merged with next non-heading paragraph
      pendingHeading += (pendingHeading ? "\n\n" : "") + trimmed;
      continue;
    }

    // Merge any pending heading with this paragraph
    if (pendingHeading) {
      merged.push(`${pendingHeading}\n\n${trimmed}`);
      pendingHeading = "";
    } else {
      merged.push(trimmed);
    }
  }

  // If only headings remain (no body text followed), flush them as a block
  if (pendingHeading) {
    merged.push(pendingHeading);
  }

  // Fallback: if nothing was produced, return the whole text as a single block
  if (merged.length === 0) {
    return [{ text: text.trim(), citationIndices: [] }];
  }

  // Extract ALL citations from each paragraph and strip them from text
  return merged.map((paragraph) => {
    const indices: number[] = [];
    const seen = new Set<number>();

    // Collect all [N] indices from anywhere in the paragraph
    let m: RegExpExecArray | null;
    ALL_CITATIONS_RE.lastIndex = 0;
    while ((m = ALL_CITATIONS_RE.exec(paragraph)) !== null) {
      const intIdx = Number.parseInt(m[1], 10);
      if (!seen.has(intIdx)) {
        seen.add(intIdx);
        indices.push(intIdx);
      }
    }

    // Remove all [N] markers from the text
    const cleanText = paragraph
      .replace(ALL_CITATIONS_RE, "")
      // Clean up extra whitespace left behind after removal
      .replace(/  +/g, " ")
      .trim();

    return { text: cleanText, citationIndices: indices };
  });
}
