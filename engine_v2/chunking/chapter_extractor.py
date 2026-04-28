"""Chapter/section extraction and chunk assignment.

Aligns with llama_index.core.node_parser — provides chunk-level
structure detection (chapters, sections, appendices) for MinerU
content_list.json output.

Extracted from readers/mineru_reader.py to allow reuse by:
    - readers/   (assign chapter_key to Documents)
    - toc/       (build structured TOC)
    - ingestion/ (chapter-aware chunking strategies)
"""

from __future__ import annotations

import re

from loguru import logger

MAX_CHAPTERS_PER_BOOK = 80


def extract_chapters(content_list: list[dict]) -> list[dict]:
    """Extract chapter headings from MinerU content_list.

    Detects text_level==1 items that match chapter/appendix patterns.

    Args:
        content_list: Raw MinerU content_list.json data.

    Returns:
        List of dicts: { chapter_key, title, page_idx }
    """
    chapters: list[dict] = []
    seen: set[str] = set()

    for item in content_list:
        if item.get("type") != "text" or item.get("text_level") != 1:
            continue
        text = item.get("text", "").strip()
        if not (3 <= len(text) <= 300):
            continue

        # Match: "Chapter 1: ..." or "1. ..." or "1 ..."
        m = re.match(
            r"(?:chapter\s+)?(\d+)[.:\s]+(.{3,120})", text, re.IGNORECASE
        )
        if m:
            key = f"ch{m.group(1).zfill(2)}"
            if key not in seen:
                seen.add(key)
                chapters.append({
                    "chapter_key": key,
                    "title": m.group(2).strip().rstrip(".,: "),
                    "page_idx": item.get("page_idx", 0),
                })
            continue

        # Match: "Appendix A: ..."
        m = re.match(
            r"appendix\s+([A-Z])[.:\s]*(.{3,120})", text, re.IGNORECASE
        )
        if m:
            key = f"app{m.group(1)}"
            if key not in seen:
                seen.add(key)
                chapters.append({
                    "chapter_key": key,
                    "title": m.group(2).strip().rstrip(".,: "),
                    "page_idx": item.get("page_idx", 0),
                })

    return chapters[:MAX_CHAPTERS_PER_BOOK]


def build_chapter_ranges(
    content_list: list[dict],
    chapters: list[dict],
) -> list[tuple[str, int, int]]:
    """Build (chapter_key, start_page, end_page) page ranges.

    Args:
        content_list: Raw content_list for max page calculation.
        chapters: Output from extract_chapters().

    Returns:
        List of (chapter_key, start_page_idx, end_page_idx) tuples.
    """
    if not chapters:
        return []

    max_page = max(
        (item.get("page_idx", 0) for item in content_list), default=0
    )
    total_pages = max_page + 1

    ranges = []
    for i, ch in enumerate(chapters):
        start = ch["page_idx"]
        end = chapters[i + 1]["page_idx"] if i + 1 < len(chapters) else total_pages
        ranges.append((ch["chapter_key"], start, end))
    return ranges


def assign_chapter(
    page_idx: int,
    ranges: list[tuple[str, int, int]],
) -> str | None:
    """Assign a chapter key to a page index.

    Args:
        page_idx: 0-based page index.
        ranges: Output from build_chapter_ranges().

    Returns:
        Chapter key string, or None if not within any range.
    """
    for key, start, end in ranges:
        if start <= page_idx < end:
            return key
    return None
