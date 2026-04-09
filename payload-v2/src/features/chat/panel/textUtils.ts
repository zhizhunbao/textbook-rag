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

  // Restore protected math
  text = text.replace(/\x00DMATH(\d+)\x00/g, (_, i) => displayMath[Number(i)]);
  text = text.replace(/\x00IMATH(\d+)\x00/g, (_, i) => inlineMath[Number(i)]);

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
