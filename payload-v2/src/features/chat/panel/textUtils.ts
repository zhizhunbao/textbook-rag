/**
 * textUtils — Shared text preprocessing for Markdown + KaTeX rendering.
 *
 * Consolidates LaTeX delimiter conversion and currency symbol escaping
 * used across: AnswerBlockRenderer, MessageBubble, SourceCard, CitationPopover.
 */

/**
 * Escape currency `$` signs so KaTeX doesn't treat them as math delimiters.
 *
 * Strategy: first protect genuine LaTeX math pairs (`$$...$$` and `$...$`),
 * then escape all remaining `$` signs (which are currency), then restore
 * the protected math delimiters.
 *
 * This avoids the subtle bug where two separate currency amounts like
 * `$38.2% increase ... $722,400` form a false KaTeX math pair.
 */
function escapeCurrencyDollars(text: string): string {
  // Step 0: Protect <mark>...</mark> tags (injected by highlight pipeline).
  // These may contain $ signs (e.g. <mark>$722,400</mark>) that must NOT
  // be treated as math delimiters.
  const markTags: string[] = [];
  text = text.replace(/<mark[^>]*>[\s\S]*?<\/mark>/gi, (match) => {
    markTags.push(match);
    return `\x00MARK${markTags.length - 1}\x00`;
  });

  // Protect display math: $$ ... $$
  const displayMath: string[] = [];
  text = text.replace(/\$\$[\s\S]*?\$\$/g, (match) => {
    displayMath.push(match);
    return `\x00DMATH${displayMath.length - 1}\x00`;
  });

  // Protect inline math: $ ... $ (content must NOT start with a digit
  // and must NOT be just whitespace/numbers — heuristic for real math)
  const inlineMath: string[] = [];
  text = text.replace(/\$([^\$\n]+?)\$/g, (match, inner) => {
    const trimmed = inner.trim();
    // If the content looks like math (contains letters, operators, etc.), protect it
    // If it looks like currency/numbers only, don't protect — let it be escaped
    if (/[a-zA-Z\\{}_^]/.test(trimmed)) {
      inlineMath.push(match);
      return `\x00IMATH${inlineMath.length - 1}\x00`;
    }
    return match;
  });

  // Escape all remaining $ signs (these are currency)
  text = text.replace(/\$/g, '\\$');

  // Restore protected regions (reverse order)
  text = text.replace(/\x00DMATH(\d+)\x00/g, (_, i) => displayMath[Number(i)]);
  text = text.replace(/\x00IMATH(\d+)\x00/g, (_, i) => inlineMath[Number(i)]);
  text = text.replace(/\x00MARK(\d+)\x00/g, (_, i) => markTags[Number(i)]);

  return text;
}

/**
 * Convert LaTeX delimiters that remark-math does not recognise,
 * and escape currency dollar signs.
 *
 *   `\( ... \)`  →  `$ ... $`   (inline math)
 *   `\[ ... \]`  →  `$$ ... $$` (display math)
 *   `$48`        →  `\$48`      (currency, not math)
 */
export function prepareForKatex(text: string): string {
  // Step 1: escape currency $ before converting delimiters
  text = escapeCurrencyDollars(text);
  // Step 2: convert \[ \] and \( \) to $$ and $
  text = text.replace(/\\\[([\\s\S]*?)\\\]/g, (_m, math) => `$$${math}$$`);
  text = text.replace(/\\\((.+?)\\\)/g, (_m, math) => `$${math}$`);
  return text;
}

/**
 * Smart newline normalization for citation/source content.
 *
 * Old chunks from ChromaDB use single `\n` (soft line breaks, collapsed by
 * Markdown). We need double `\n\n` for paragraph separation, BUT we must
 * NOT insert blank lines between consecutive list items or inside indented
 * blocks — that would break the Markdown list structure.
 *
 * Rules:
 *   - If BOTH current and next line are list items (- / * / 1.), keep single \n
 *   - If current or next line is indented (leading spaces/tab), keep single \n
 *   - If current or next line is a heading (#), keep single \n
 *   - If current or next line is a blockquote (>), keep single \n
 *   - Otherwise, convert single \n to \n\n for paragraph spacing
 */
export function normalizeNewlines(text: string): string {
  // If there are already double newlines, the content is properly formatted
  if (text.includes('\n\n')) return text;

  const lines = text.split('\n');
  if (lines.length <= 1) return text;

  // Patterns that indicate structured Markdown content
  const isList = (line: string) => /^\s*[-*+]\s/.test(line) || /^\s*\d+[.)]\s/.test(line);
  const isIndented = (line: string) => /^[ \t]+\S/.test(line);
  const isHeading = (line: string) => /^#{1,6}\s/.test(line);
  const isBlockquote = (line: string) => /^\s*>/.test(line);
  const isStructured = (line: string) =>
    isList(line) || isIndented(line) || isHeading(line) || isBlockquote(line);

  let result = lines[0];
  for (let i = 1; i < lines.length; i++) {
    const prev = lines[i - 1];
    const curr = lines[i];

    // Keep single newline between structured lines (lists, indents, etc.)
    if (isStructured(prev) || isStructured(curr)) {
      result += '\n' + curr;
    } else if (curr.trim() === '') {
      // Already a blank line
      result += '\n' + curr;
    } else {
      // Plain text → inject paragraph break
      result += '\n\n' + curr;
    }
  }

  return result;
}
