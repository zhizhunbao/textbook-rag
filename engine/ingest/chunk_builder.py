"""chunk_builder.py — MinerU content_list.json → chunks + source_locators.

v2.0: Extracted from scripts/rebuild_db.py (ingest_book function).
Core logic is unchanged; returns structured dicts instead of writing to SQLite.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from dataclasses import dataclass

MAX_CHAPTERS_PER_BOOK = 80


@dataclass
class ChunkData:
    """A single chunk extracted from MinerU output."""
    chunk_id: str
    book_dir_name: str
    content_type: str
    text: str
    reading_order: int
    page_idx: int
    bbox: list[float]           # [x0, y0, x1, y1] in PDF points
    chapter_key: str | None = None


@dataclass
class IngestResult:
    """Result of building chunks from one book's MinerU output."""
    book_dir_name: str
    category: str
    title: str
    authors: str
    total_pages: int
    page_sizes: dict[int, tuple[float, float]]  # page_idx → (w, h)
    chapters: list[dict]        # [{chapter_key, title}]
    chunks: list[ChunkData]


def build_chunks(
    book_dir_name: str,
    category: str,
    mineru_dir: Path,
    book_registry: dict[str, dict] | None = None,
) -> IngestResult | None:
    """Build chunks from MinerU output for one book.

    Args:
        book_dir_name: Directory name of the book under mineru_dir/category/
        category: textbook | ecdev | real_estate
        mineru_dir: Path to data/mineru_output/
        book_registry: Optional metadata registry. Falls back to auto-title.

    Returns:
        IngestResult with all chunks, or None if content_list.json not found.
    """
    auto_dir = mineru_dir / category / book_dir_name / book_dir_name / "auto"
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"
    middle_json_path = auto_dir / f"{book_dir_name}_middle.json"

    if not content_list_path.exists():
        return None

    # Book metadata
    meta = (book_registry or {}).get(book_dir_name) or _auto_meta(book_dir_name, category)
    title = meta.get("title", book_dir_name.replace("_", " ").title())
    authors = meta.get("authors", "")

    # Load content list
    with open(content_list_path, "r", encoding="utf-8") as f:
        content_list = json.load(f)

    # Page sizes
    page_sizes = _load_page_sizes(middle_json_path)

    max_page_idx = max((item.get("page_idx", 0) for item in content_list), default=0)
    total_pages = max_page_idx + 1

    # Chapters
    chapters = _extract_chapters(content_list)

    # Chapter page ranges
    chapter_keys = [ch["chapter_key"] for ch in chapters]
    chapter_first_pages = _find_chapter_first_pages(content_list, chapters)
    chapter_ranges = _build_ranges(chapter_first_pages, total_pages)

    # Build chunks
    chunks: list[ChunkData] = []
    reading_order = 0

    for item in content_list:
        item_type = item.get("type", "")
        if item_type == "discarded":
            continue

        text = item.get("text", "").strip()
        if not text and item_type not in ("image", "table"):
            continue
        if item_type == "table" and not text:
            text = item.get("table_body", "")
        if item_type == "image" and not text:
            captions = item.get("image_caption", [])
            text = " ".join(captions) if captions else ""
        if not text:
            continue

        page_idx = item.get("page_idx", 0)
        raw_bbox = item.get("bbox", [0, 0, 0, 0])
        if len(raw_bbox) < 4:
            raw_bbox = [0, 0, 0, 0]

        # Convert normalised 1000×1000 canvas → PDF points
        pw, ph = page_sizes.get(page_idx, (0.0, 0.0))
        if pw and ph:
            bbox = [
                raw_bbox[0] / 1000 * pw, raw_bbox[1] / 1000 * ph,
                raw_bbox[2] / 1000 * pw, raw_bbox[3] / 1000 * ph,
            ]
        else:
            bbox = [float(v) for v in raw_bbox]

        # Chapter assignment
        ch_list_idx = _assign_chapter(page_idx, chapter_ranges)
        chapter_key = chapter_keys[ch_list_idx] if ch_list_idx is not None else None

        chunk_id = f"{book_dir_name}_{reading_order:06d}"
        chunks.append(ChunkData(
            chunk_id=chunk_id,
            book_dir_name=book_dir_name,
            content_type=item_type,
            text=text,
            reading_order=reading_order,
            page_idx=page_idx,
            bbox=bbox,
            chapter_key=chapter_key,
        ))
        reading_order += 1

    return IngestResult(
        book_dir_name=book_dir_name,
        category=category,
        title=title,
        authors=authors,
        total_pages=total_pages,
        page_sizes=page_sizes,
        chapters=chapters,
        chunks=chunks,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _auto_meta(book_dir_name: str, category: str) -> dict:
    return {"title": book_dir_name.replace("_", " ").title(), "authors": category}


def _load_page_sizes(middle_json_path: Path) -> dict[int, tuple[float, float]]:
    try:
        with open(middle_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return {}

    pages = data.get("pdf_info", data) if isinstance(data, dict) else data
    if not isinstance(pages, list):
        return {}

    result: dict[int, tuple[float, float]] = {}
    for page in pages:
        idx = page.get("page_idx")
        size = page.get("page_size")
        if idx is not None and size and len(size) == 2:
            result[idx] = (float(size[0]), float(size[1]))
    return result


def _extract_chapters(content_list: list[dict]) -> list[dict]:
    chapters: list[dict] = []
    seen: set[str] = set()

    for item in content_list:
        if item.get("type") != "text" or item.get("text_level") != 1:
            continue
        text = item.get("text", "").strip()
        if not (3 <= len(text) <= 300):
            continue

        m = re.match(r"(?:chapter\s+)?(\d+)[.:\s]+(.{3,120})", text, re.IGNORECASE)
        if m:
            key = f"ch{m.group(1).zfill(2)}"
            if key not in seen:
                seen.add(key)
                chapters.append({"chapter_key": key, "title": m.group(2).strip().rstrip(".,: ")})
            continue

        m = re.match(r"appendix\s+([A-Z])[.:\s]*(.{3,120})", text, re.IGNORECASE)
        if m:
            key = f"app{m.group(1)}"
            if key not in seen:
                seen.add(key)
                chapters.append({"chapter_key": key, "title": m.group(2).strip().rstrip(".,: ")})

    return chapters[:MAX_CHAPTERS_PER_BOOK]


def _find_chapter_first_pages(content_list: list[dict], chapters: list[dict]) -> list[int]:
    result = []
    for ch in chapters:
        key = ch["chapter_key"]
        m = re.match(r"ch(\d+)", key)
        found = False
        if m:
            pattern = re.compile(rf"(?:chapter\s+)?{re.escape(m.group(1))}\b", re.IGNORECASE)
            for item in content_list:
                if item.get("type") == "text" and item.get("text_level") == 1:
                    if pattern.search(item.get("text", "")):
                        result.append(item.get("page_idx", 0))
                        found = True
                        break
        if not found:
            result.append(0)
    return result


def _build_ranges(first_pages: list[int], total_pages: int) -> list[tuple[int, int]]:
    ranges = []
    for i, start in enumerate(first_pages):
        end = first_pages[i + 1] if i + 1 < len(first_pages) else total_pages
        ranges.append((start, end))
    return ranges


def _assign_chapter(page_idx: int, ranges: list[tuple[int, int]]) -> int | None:
    for i, (start, end) in enumerate(ranges):
        if start <= page_idx < end:
            return i
    return None
