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
    - Headings always trigger a flush (don't merge across sections).
    - Tables and images are never merged — they stay standalone.
    - Single items > MAX_CHUNK_CHARS stay as-is (can't split without
      breaking bbox).

Cross-page merges are supported; multiple bboxes are preserved for
accurate frontend PDF highlighting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


# ── Tunables ──────────────────────────────────────────────────
MIN_CHUNK_CHARS = 300   # Keep accumulating until buffer reaches this
MAX_CHUNK_CHARS = 500   # Don't let buffer exceed this
# Items of these types are never merged (kept standalone)
STANDALONE_TYPES = {"table", "image", "discarded"}


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


def merge_content_items(
    items: list[dict[str, Any]],
    *,
    page_sizes: dict[int, tuple[float, float]] | None = None,
    min_chars: int = MIN_CHUNK_CHARS,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[MergedItem]:
    """Merge consecutive body-text items into 300–500 char chunks.

    Algorithm:
        1. Walk items in reading order.
        2. Skip discarded / empty items.
        3. When hitting a heading (text_level is set):
           - Flush the current buffer.
           - Remember the heading text as section_title for context.
        4. Tables/images always emit as standalone chunks.
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

    # Current merge buffer
    buf_texts: list[str] = []
    buf_bboxes: list[_BboxEntry] = []
    buf_first_page: int = 0
    buf_section_title: str | None = None
    buf_char_count: int = 0

    def _flush() -> None:
        """Emit the current buffer as a MergedItem and reset."""
        nonlocal buf_texts, buf_bboxes, buf_first_page, buf_char_count
        if not buf_texts:
            return
        merged_text = "\n\n".join(buf_texts)
        # Prepend section title for context (helps retrieval)
        if buf_section_title:
            merged_text = f"{buf_section_title}\n\n{merged_text}"
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

        # Skip discarded / empty
        if item_type == "discarded" or not text:
            continue

        text_level = item.get("text_level")

        # ── Standalone types: table, image — always emit independently ──
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
            continue

        # ── Heading: flush buffer, record as new section title ──
        if text_level is not None:
            _flush()
            buf_section_title = text
            continue

        # ── Body text: accumulate with min/max char strategy ──

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
            "SectionMerger: {} body items → {} chunks "
            "(avg {:.0f} chars, range {}-{})",
            original_count, merged_count, avg_chars, min_chars, max_chars,
        )

    return result
