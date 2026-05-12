"""section_merger — Merge small MinerU content items into appropriately-sized chunks.

MinerU outputs one content item per visual text block (title, paragraph,
bullet, etc.).  For RAG retrieval these items are often too small: a
definition split across title + 3 bullets produces 4 chunks of ~60 chars
each, none of which has enough semantic signal for accurate vector or
BM25 retrieval.

This module merges consecutive body-text items into chunks of 300–500
characters.  The strategy follows Unstructured.io's ``chunk_by_title``
pattern:

    - Accumulate body-text items into a buffer.
    - Flush when buffer >= MIN_CHUNK_CHARS (300) — chunk is "big enough".
    - Flush BEFORE adding an item that would push buffer > MAX_CHUNK_CHARS
      (500) — prevent oversized chunks.
    - **True headings** trigger a flush (don't merge across sections).
    - **Sub-headings** (text starts with numbers like "1.", "2." or
      bullets like "·", "•", "-") are treated as body text belonging
      to the previous section, not as section boundaries.
    - Tables and images are never merged — they stay standalone.
    - Single items > MAX_CHUNK_CHARS stay as-is (can't split without
      breaking bbox).

Cross-page merges are supported; multiple bboxes are preserved for
accurate frontend PDF highlighting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


# ── Tunables ──────────────────────────────────────────────────
MIN_CHUNK_CHARS = 300   # Keep accumulating until buffer reaches this
MAX_CHUNK_CHARS = 500   # Don't let buffer exceed this
# Items of these types are never merged (kept standalone).
# Tables are intentionally NOT in this set — they merge into sections
# for context (e.g., NOC occupation table belongs with its heading).
STANDALONE_TYPES = {"image", "discarded"}

# Regex: heading text that looks like a numbered sub-item or bullet point.
# These are NOT true section boundaries — they belong to the previous heading.
# Examples:
#   "1. General rounds"          → numbered sub-item
#   "2 Program-specific rounds"  → numbered (no dot)
#   "a. within the previous..."  → lettered sub-item
#   "· some bullet"              → bullet
#   "• item"                     → bullet
#   "- item"                     → dash bullet
_SUB_HEADING_RE = re.compile(
    r"^(?:"
    r"\d+[.)]?\s"          # 1. / 1) / 1 + space
    r"|[a-z][.)]\s"         # a. / a)
    r"|[\u00b7\u2022\-\*]\s"          # bullet: · • - *
    r")",
)

# Unicode / HTML cleanup for embedding-ready text
_SPECIAL_SPACES_RE = re.compile(r"[\u2002\u2003\u2009\u200a\u00a0\u200b]")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_MULTI_SPACE_RE = re.compile(r"  +")


def _normalize_text(text: str) -> str:
    """Clean text for embedding: strip special Unicode, HTML remnants, encoding artifacts."""
    # Replace special Unicode spaces (en-space, em-space, thin-space, NBSP, ZWSP)
    text = _SPECIAL_SPACES_RE.sub(" ", text)
    # Fix common MinerU encoding artifacts
    text = text.replace("\ufffd", "")  # replacement char �
    text = text.replace("\u0092", "'").replace("\u0093", '"').replace("\u0094", '"')
    # Strip any residual HTML tags (shouldn't be many after MinerU processing)
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple whitespace
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _html_table_to_text(html: str) -> str:
    """Convert HTML table to plain pipe-separated text for embedding."""
    if not html:
        return ""
    # Strip tags, keep cell content separated by pipes
    text = re.sub(r"</?(?:table|thead|tbody|tfoot)[^>]*>", "", html)
    text = re.sub(r"<tr[^>]*>", "", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"<t[dh][^>]*>", "", text)
    text = re.sub(r"</t[dh]>", " | ", text)
    text = re.sub(r"<[^>]+>", "", text)  # remaining tags
    # Clean up
    text = re.sub(r"\| *\n", "\n", text)  # trailing pipe before newline
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


@dataclass
class _BboxEntry:
    """One bounding box on one PDF page."""
    page_idx: int
    bbox: list[float]       # [x0, y0, x1, y1] in PDF points
    page_width: float = 0.0
    page_height: float = 0.0


@dataclass
class MergedItem:
    """A merged content chunk — may contain text from multiple MinerU items.

    Attributes:
        text:         Merged text content.
        content_type: "text" for merged body text, original type for standalone.
        page_idx:     Page index of the FIRST item (used for navigation).
        bboxes:       All bboxes from constituent items (multi-page aware).
        text_level:   Heading level if this chunk IS a heading (None for body).
        section_title: The heading text that precedes this body chunk (context).
    """
    text: str = ""
    content_type: str = "text"
    page_idx: int = 0
    bboxes: list[_BboxEntry] = field(default_factory=list)
    text_level: int | None = None
    section_title: str | None = None

    @property
    def primary_bbox(self) -> list[float]:
        """Union bbox of ALL constituent items (for simple single-bbox display)."""
        if not self.bboxes:
            return [0.0, 0.0, 0.0, 0.0]
        x0 = min(b.bbox[0] for b in self.bboxes)
        y0 = min(b.bbox[1] for b in self.bboxes)
        x1 = max(b.bbox[2] for b in self.bboxes)
        y1 = max(b.bbox[3] for b in self.bboxes)
        return [x0, y0, x1, y1]

    @property
    def primary_page_width(self) -> float:
        return self.bboxes[0].page_width if self.bboxes else 0.0

    @property
    def primary_page_height(self) -> float:
        return self.bboxes[0].page_height if self.bboxes else 0.0


def _classify_headings(items: list[dict[str, Any]]) -> set[str]:
    """Pre-pass: analyse ALL headings to find which are top-level section breaks.

    Strategy (works across all document types without per-PDF customisation):

    1. Collect every heading's **normalised text** and **bbox height**
       (proxy for font size — taller bbox = bigger font = higher-level heading).
    2. Group headings by their *canonical form* (exact text for short headings,
       or a regex-normalised form for numbered headings like "Round #414: ...").
    3. Classify:
       - A heading whose canonical form repeats AND whose bbox height is among
         the **tallest** group → top-level section break.
       - A heading whose canonical form repeats AND bbox is shorter → sub-heading
         (merged into the parent section).
       - A heading with a unique canonical form → top-level by default.
       - The _SUB_HEADING_RE pattern (numbered/bulleted) always → sub-heading.

    Returns:
        Set of heading texts classified as **sub-headings** (to be merged,
        not treated as section breaks).
    """
    from collections import Counter, defaultdict

    headings: list[dict] = []
    for item in items:
        text = (item.get("text", "") or "").strip()
        if not text or item.get("text_level") is None:
            continue
        bbox = item.get("bbox", [0, 0, 0, 0])
        # bbox height = proxy for font size (MinerU normalises to 1000x1000)
        bbox_h = (bbox[3] - bbox[1]) if len(bbox) >= 4 else 0
        headings.append({"text": text, "bbox_h": bbox_h})

    if len(headings) < 3:
        # Too few headings — no meaningful hierarchy to infer.
        return set()

    # ── Step 1: Compute canonical form ──
    # "Round #414: French-Language..." → "Round #NNN: ..."
    # "Definitions" → "Definitions"
    _num_pattern = re.compile(r"#\d+")
    def canonical(text: str) -> str:
        return _num_pattern.sub("#NNN", text).strip()

    # ── Step 2: Group by canonical form and compute stats ──
    canon_heights: defaultdict[str, list[float]] = defaultdict(list)
    canon_texts: defaultdict[str, list[str]] = defaultdict(list)
    for h in headings:
        c = canonical(h["text"])
        canon_heights[c].append(h["bbox_h"])
        canon_texts[c].append(h["text"])

    # ── Step 3: Find the tallest heading group (= top-level font size) ──
    # Use median bbox height for each group to be robust against outliers.
    def median(vals: list[float]) -> float:
        s = sorted(vals)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    group_median_h = {
        canon: median(heights)
        for canon, heights in canon_heights.items()
    }

    if not group_median_h:
        return set()

    max_h = max(group_median_h.values())

    # Tolerance: headings within 20% of the tallest are considered top-level.
    top_level_threshold = max_h * 0.80

    # ── Step 4: Build sub-heading set ──
    sub_heading_texts: set[str] = set()
    top_level_canons: list[str] = []
    sub_level_canons: list[str] = []

    for canon, med_h in group_median_h.items():
        count = len(canon_heights[canon])
        is_tall = med_h >= top_level_threshold
        is_repeated = count >= 3  # appears at least 3 times

        if is_tall:
            top_level_canons.append(canon)
        elif is_repeated:
            # Shorter font AND repeats → sub-heading
            sub_level_canons.append(canon)
            sub_heading_texts.update(canon_texts[canon])
        # Unique short headings: keep as top-level (they may be one-off sections)

    # Also mark any heading matching _SUB_HEADING_RE as sub-heading
    for h in headings:
        if _SUB_HEADING_RE.match(h["text"]):
            sub_heading_texts.add(h["text"])

    # Log the classification
    if sub_heading_texts:
        logger.info(
            "HeadingClassifier: {} top-level groups, {} sub-heading groups "
            "({} texts merged into parent sections)",
            len(top_level_canons), len(sub_level_canons), len(sub_heading_texts),
        )
        for canon in top_level_canons[:3]:
            example = canon_texts[canon][0][:60]
            logger.debug("  TOP: '{}' (h={:.0f}, n={})",
                         example, group_median_h[canon], len(canon_heights[canon]))
        for canon in sub_level_canons[:5]:
            example = canon_texts[canon][0][:60]
            logger.debug("  SUB: '{}' (h={:.0f}, n={})",
                         example, group_median_h[canon], len(canon_heights[canon]))

    return sub_heading_texts


def merge_content_items(
    items: list[dict[str, Any]],
    *,
    page_sizes: dict[int, tuple[float, float]] | None = None,
    min_chars: int = MIN_CHUNK_CHARS,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[MergedItem]:
    """Merge consecutive body-text items into 300-500 char chunks.

    Algorithm:
        0. **Pre-pass**: Analyse all headings to classify top-level vs
           sub-headings using bbox height (font size) and text frequency.
        1. Walk items in reading order.
        2. Skip discarded / empty items.
        3. When hitting a **top-level heading** → flush and start new section.
           When hitting a **sub-heading** → treat as body text (merge in).
        4. Images always emit as standalone chunks.
        5. For body text (no text_level):
           - If buffer + item > max_chars AND buffer is non-empty: flush first.
           - Accumulate item into buffer.
           - If buffer >= min_chars: flush (chunk is big enough).

    Args:
        items:      Raw MinerU content_list items (dicts with type, text, etc.)
        page_sizes: Optional {page_idx: (width, height)} for bbox context.
        min_chars:  Minimum character count to flush (default 300).
        max_chars:  Maximum character count before forced flush (default 500).

    Returns:
        List of MergedItem instances ready for Document creation.
    """
    page_sizes = page_sizes or {}
    result: list[MergedItem] = []

    # ── Pre-pass: classify headings ──
    sub_headings = _classify_headings(items)

    # Current merge buffer
    buf_texts: list[str] = []
    buf_bboxes: list[_BboxEntry] = []
    buf_first_page: int = 0
    buf_section_title: str | None = None
    buf_char_count: int = 0
    prev_heading_bbox_h: float = 0   # Font size of last heading
    heading_had_body: bool = True     # Did body text appear since last heading?

    def _flush() -> None:
        """Emit the current buffer as a MergedItem and reset."""
        nonlocal buf_texts, buf_bboxes, buf_first_page, buf_char_count
        if not buf_texts:
            return
        merged_text = "\n\n".join(buf_texts)
        # Prepend section title for context (helps retrieval)
        if buf_section_title:
            merged_text = f"{buf_section_title}\n\n{merged_text}"
        # Clean for embedding
        merged_text = _normalize_text(merged_text)
        result.append(MergedItem(
            text=merged_text,
            content_type="text",
            page_idx=buf_first_page,
            bboxes=list(buf_bboxes),
            section_title=buf_section_title,
        ))
        buf_texts = []
        buf_bboxes = []
        buf_char_count = 0

    def _make_bbox(item: dict) -> _BboxEntry:
        """Create a _BboxEntry from an item's raw data."""
        raw = item.get("bbox", [0, 0, 0, 0])
        page_idx = item.get("page_idx", 0)
        pw, ph = page_sizes.get(page_idx, (0.0, 0.0))
        return _BboxEntry(
            page_idx=page_idx,
            bbox=[float(v) for v in (raw[:4] if len(raw) >= 4 else [0, 0, 0, 0])],
            page_width=pw,
            page_height=ph,
        )

    for item in items:
        item_type = item.get("type", "")
        text = (item.get("text", "") or "").strip()

        # For tables: extract text from table_body HTML if text is empty
        if not text and item_type == "table":
            text = _html_table_to_text(item.get("table_body", ""))
            # Large tables: split by rows into multiple pseudo-items
            if text and len(text) > max_chars:
                rows = text.split("\n")
                row_buf = []
                row_buf_len = 0
                for row in rows:
                    if row_buf and row_buf_len + len(row) > max_chars:
                        # Emit current row buffer as a body-text item
                        chunk_text = "\n".join(row_buf)
                        _flush()
                        if not buf_texts:
                            bbox_entry = _make_bbox(item)
                            buf_first_page = item.get("page_idx", 0)
                            buf_bboxes = [bbox_entry]
                        buf_texts.append(chunk_text)
                        buf_char_count += len(chunk_text)
                        heading_had_body = True
                        row_buf = []
                        row_buf_len = 0
                    row_buf.append(row)
                    row_buf_len += len(row) + 1
                # Remaining rows
                if row_buf:
                    text = "\n".join(row_buf)
                else:
                    continue  # all rows already emitted

        # Skip discarded / empty
        if item_type == "discarded" or not text:
            continue

        text_level = item.get("text_level")

        # ── Standalone types (image only) — always emit independently ──
        if item_type in STANDALONE_TYPES:
            _flush()
            bbox_entry = _make_bbox(item)
            result.append(MergedItem(
                text=text,
                content_type=item_type,
                page_idx=item.get("page_idx", 0),
                bboxes=[bbox_entry],
                text_level=text_level,
                section_title=buf_section_title,
            ))
            heading_had_body = True
            continue

        # ── Heading: decide if it's a true section break or a sub-heading ──
        if text_level is not None:
            cur_bbox = item.get("bbox", [0, 0, 0, 0])
            cur_bbox_h = (cur_bbox[3] - cur_bbox[1]) if len(cur_bbox) >= 4 else 0

            if text in sub_headings or _SUB_HEADING_RE.match(text):
                # Sub-heading: treat as body text, merge into current section.
                pass  # fall through to body-text accumulation below
            else:
                # True heading: flush buffer and start a new section.
                _flush()
                # Consecutive headings (no body between them) with smaller
                # font → child heading. Use breadcrumb: "Section 4 > DLI"
                if (not heading_had_body
                        and buf_section_title
                        and prev_heading_bbox_h > 0
                        and cur_bbox_h < prev_heading_bbox_h * 0.97):
                    parent = buf_section_title.rsplit(" > ", 1)[-1]
                    buf_section_title = f"{parent} > {text}"
                else:
                    buf_section_title = text
                prev_heading_bbox_h = cur_bbox_h
                heading_had_body = False  # Reset: no body seen yet for this heading
                continue

        # ── Body text: accumulate with min/max char strategy ──
        heading_had_body = True  # Mark that body appeared after last heading

        # If adding this item would exceed max_chars, flush first
        if buf_texts and (buf_char_count + len(text)) > max_chars:
            _flush()

        # Start new buffer if empty
        if not buf_texts:
            buf_first_page = item.get("page_idx", 0)

        buf_texts.append(text)
        buf_bboxes.append(_make_bbox(item))
        buf_char_count += len(text)

        # If buffer is big enough, flush
        if buf_char_count >= min_chars:
            _flush()

    # Flush remaining buffer (even if < min_chars)
    _flush()

    # Handle trailing section title with no body
    if buf_section_title and (not result or result[-1].section_title != buf_section_title):
        has_title = any(
            r.section_title == buf_section_title or r.text.startswith(buf_section_title)
            for r in result[-3:] if result
        )
        if not has_title:
            result.append(MergedItem(
                text=buf_section_title,
                content_type="text",
                page_idx=items[-1].get("page_idx", 0) if items else 0,
                bboxes=[],
                text_level=1,
                section_title=None,
            ))

    # Stats
    original_count = sum(
        1 for item in items
        if item.get("type", "") not in STANDALONE_TYPES
        and item.get("type", "") != "discarded"
        and (item.get("text", "") or "").strip()
        and item.get("text_level") is None
    )
    merged_count = sum(1 for r in result if r.content_type == "text")
    avg_chars = (
        sum(len(r.text) for r in result if r.content_type == "text") / merged_count
        if merged_count else 0
    )
    if original_count > 0:
        logger.info(
            "SectionMerger: {} body items -> {} chunks "
            "(avg {:.0f} chars, range {}-{})",
            original_count, merged_count, avg_chars, min_chars, max_chars,
        )

    return result
