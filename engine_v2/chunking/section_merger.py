"""section_merger — Merge MinerU content items into section-level chunks.

MinerU outputs one content item per visual text block (title, paragraph,
bullet, etc.).  For RAG retrieval these items are often too small: a
definition split across title + 3 bullets produces 4 chunks of ~60 chars
each, none of which has enough semantic signal for accurate vector or
BM25 retrieval.

This module merges consecutive body-text items that belong to the same
logical section (delimited by headings) into larger, semantically richer
chunks.  Cross-page merges are supported; multiple bboxes are preserved
for accurate frontend highlighting.

Design decisions:
    - Headings (text_level != None) START a new section and are PREPENDED
      to the first body chunk as context ("Section title: ...")
    - Tables and images are never merged — they stay as independent chunks
    - A soft character limit (MERGE_CHAR_LIMIT) prevents overly large chunks
    - All original bbox + page_idx data is preserved per sub-item so the
      frontend can highlight across pages
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


# ── Tunables ──────────────────────────────────────────────────
MERGE_CHAR_LIMIT = 800   # Soft limit: flush buffer when text exceeds this
MIN_MERGE_CHARS = 80     # Don't merge items that are already this big on their own
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
    char_limit: int = MERGE_CHAR_LIMIT,
) -> list[MergedItem]:
    """Merge consecutive body-text items into section-level chunks.

    Algorithm:
        1. Walk items in reading order.
        2. Skip discarded items.
        3. When hitting a heading (text_level is set):
           - Flush the current buffer as a merged chunk.
           - Remember the heading text as section_title for the next chunk.
        4. For body text (no text_level):
           - Accumulate into the current buffer.
           - Flush when buffer exceeds char_limit or when item type changes
             to a standalone type.
        5. Tables/images always emit as standalone chunks.

    Args:
        items:      Raw MinerU content_list items (dicts with type, text, etc.)
        page_sizes: Optional {page_idx: (width, height)} for bbox context.
        char_limit: Soft character limit for merged chunks.

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
        merged_text = "\n".join(buf_texts)
        # Prepend section title for context (helps retrieval)
        if buf_section_title:
            merged_text = f"{buf_section_title}\n{merged_text}"
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
            # Don't add heading text to buffer — it will be prepended
            # to the next body chunk via buf_section_title.
            # But if heading stands alone (no body follows), we still
            # want to emit it. We'll handle that at next heading or EOF.
            continue

        # ── Body text: accumulate into buffer ──
        # Check if adding this item would exceed the char limit
        new_len = buf_char_count + len(text)
        if buf_texts and new_len > char_limit:
            _flush()

        if not buf_texts:
            buf_first_page = item.get("page_idx", 0)

        buf_texts.append(text)
        buf_bboxes.append(_make_bbox(item))
        buf_char_count += len(text)

    # Flush remaining buffer
    _flush()

    # Handle trailing section title with no body
    # (section_title was set but no body followed before EOF)
    if buf_section_title and (not result or result[-1].section_title != buf_section_title):
        # Check if the last result already captured this title
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
    original_text_count = sum(
        1 for item in items
        if item.get("type", "") not in STANDALONE_TYPES
        and item.get("type", "") != "discarded"
        and (item.get("text", "") or "").strip()
        and item.get("text_level") is None
    )
    merged_text_count = sum(1 for r in result if r.content_type == "text")
    if original_text_count > 0:
        logger.info(
            "SectionMerger: {} body items → {} merged chunks "
            "(reduction {:.0f}%, char_limit={})",
            original_text_count, merged_text_count,
            (1 - merged_text_count / original_text_count) * 100 if original_text_count else 0,
            char_limit,
        )

    return result
