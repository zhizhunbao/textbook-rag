"""Books route — GET /engine/books, PDF serving, TOC.

Scans the MinerU output directory to discover processed books,
serves PDFs from both MinerU auto/ and raw_pdfs/ directories,
and extracts TOC from content_list.json headings.

Unlike Engine v1 (which read from SQLite), Engine v2 derives
everything from the filesystem.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from loguru import logger

from engine_v2.settings import DATA_DIR, MINERU_OUTPUT_DIR
from engine_v2.toc import extract_toc as _toc_extract, load_content_list as _toc_load, find_pdf_for_book as _toc_find_pdf

router = APIRouter(tags=["books"])

# Raw PDF root
RAW_PDF_ROOT = DATA_DIR / "raw_pdfs"


def _list_categories() -> list[str]:
    """Discover all category directories under mineru_output/.

    Dynamic instead of hardcoded — any new category (e.g. professional_profile)
    created by classify or manual upload is automatically included.
    """
    cats: list[str] = []
    if MINERU_OUTPUT_DIR.is_dir():
        for d in sorted(MINERU_OUTPUT_DIR.iterdir()):
            if d.is_dir():
                cats.append(d.name)
    return cats


def _list_raw_pdf_dirs() -> list[Path]:
    """Discover all subdirectories under data/raw_pdfs/ for PDF lookup."""
    dirs: list[Path] = []
    if RAW_PDF_ROOT.is_dir():
        for d in sorted(RAW_PDF_ROOT.iterdir()):
            if d.is_dir():
                dirs.append(d)
    return dirs


# ── Internal helpers ─────────────────────────────────────────────────────────


def _count_content_items(content_list_path: Path) -> int:
    """Count items in content_list.json (proxy for chunk_count)."""
    try:
        with open(content_list_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return 0


def _count_pages(middle_json_path: Path) -> int:
    """Count pages from middle.json."""
    try:
        with open(middle_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pages = data.get("pdf_info", data) if isinstance(data, dict) else data
        return len(pages) if isinstance(pages, list) else 0
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return 0


def _humanize_title(book_id: str) -> str:
    """Convert book_id like 'bishop_prml' → 'Bishop Prml'."""
    return book_id.replace("_", " ").title()


def _find_book_dir(book_id: str) -> Path | None:
    """Locate the MinerU book directory across all categories.

    book_id can be either:
      - Simple name: 'bishop_prml' (textbooks)
      - Nested path: 'en/immigration-refugees-citizenship/services/study-canada' (web crawls)
    """
    for category in _list_categories():
        book_dir = MINERU_OUTPUT_DIR / category / book_id
        if book_dir.is_dir():
            return book_dir
    return None


def _get_auto_dir(book_id: str) -> Path | None:
    """Get the MinerU auto/ output directory for a book.

    Supports layouts:
      - Flat: mineru_output/{category}/{book_id}/auto/
      - Legacy nested: mineru_output/{category}/{book_id}/{stem}/auto/

    book_id may be a deep path (e.g. 'en/ircc/services/study-canada').
    """
    book_dir = _find_book_dir(book_id)
    if not book_dir:
        return None
    # Flat layout (post-flatten or web-crawled)
    auto_dir = book_dir / "auto"
    if auto_dir.is_dir():
        return auto_dir
    # Legacy nested layout: {book_dir}/{stem}/auto/
    stem = Path(book_id).name  # last component
    auto_dir = book_dir / stem / "auto"
    if auto_dir.is_dir():
        return auto_dir
    # Fallback: scan for any inner dir with auto/
    for inner in book_dir.iterdir():
        if inner.is_dir() and inner.name != "auto":
            nested_auto = inner / "auto"
            if nested_auto.is_dir():
                return nested_auto
    return None


def _find_origin_pdf(book_id: str) -> Path | None:
    """Find origin (source) PDF.

    Priority:
      1. MinerU auto/{stem}_origin.pdf  (stem = last component of book_id)
      2. MinerU auto/{book_id}_origin.pdf  (flat book_id)
      3. raw_pdfs/{category}/{book_id}.pdf
    """
    auto_dir = _get_auto_dir(book_id)
    if auto_dir:
        # MinerU uses the stem (last path component) as the PDF filename
        stem = Path(book_id).name
        origin_pdf = auto_dir / f"{stem}_origin.pdf"
        if origin_pdf.exists():
            return origin_pdf
        # Fallback: try full book_id (flat layout)
        if stem != book_id:
            origin_pdf = auto_dir / f"{book_id}_origin.pdf"
            if origin_pdf.exists():
                return origin_pdf

    # Fallback: scan raw_pdfs directories
    for d in _list_raw_pdf_dirs():
        p = d / f"{book_id}.pdf"
        if p.exists():
            return p

    return None


def _find_layout_pdf(book_id: str) -> Path | None:
    """Find MinerU layout-analysed PDF.

    Falls back to origin PDF if layout variant is not available.
    """
    auto_dir = _get_auto_dir(book_id)
    if auto_dir:
        # MinerU uses the stem (last path component) as the PDF filename
        stem = Path(book_id).name
        layout_pdf = auto_dir / f"{stem}_layout.pdf"
        if layout_pdf.exists():
            return layout_pdf
        # Fallback: try full book_id (flat layout)
        if stem != book_id:
            layout_pdf = auto_dir / f"{book_id}_layout.pdf"
            if layout_pdf.exists():
                return layout_pdf

    # Fallback to origin
    return _find_origin_pdf(book_id)


def _load_content_list(book_id: str) -> list[dict]:
    """Load content_list.json for a book (delegates to toc/)."""
    auto_dir = _get_auto_dir(book_id)
    if not auto_dir:
        return []
    return _toc_load(auto_dir, book_id)


def _extract_toc(book_id: str, content_list: list[dict]) -> list[dict]:
    """Extract TOC entries — PDF bookmarks first, MinerU fallback."""
    pdf_path = _toc_find_pdf(book_id, MINERU_OUTPUT_DIR, _list_raw_pdf_dirs())
    return _toc_extract(content_list, pdf_path=pdf_path)


def _discover_books() -> list[dict]:
    """Scan mineru_output/ for all processed books.

    Supports both flat layouts (textbooks) and deeply nested
    layouts from web crawls (federal-ircc/en/ircc/services/study-canada/).
    A "book" is identified by having an auto/ subdirectory with content_list.json.
    """
    books: list[dict] = []

    for category in _list_categories():
        category_dir = MINERU_OUTPUT_DIR / category
        if not category_dir.is_dir():
            continue

        # Walk the entire tree to find directories containing auto/
        for dirpath, dirnames, _filenames in os.walk(category_dir):
            dirpath = Path(dirpath)
            # Look for auto/ as a direct child
            if "auto" not in dirnames:
                continue

            auto_dir = dirpath / "auto"
            # book_id = relative path from category_dir
            book_id = str(dirpath.relative_to(category_dir)).replace("\\", "/")

            # Find content_list.json (may use book_id stem or full name)
            content_list_files = list(auto_dir.glob("*_content_list.json"))
            if not content_list_files:
                logger.debug("Skipping {}: no content_list.json", book_id)
                dirnames.clear()
                continue

            content_list_path = content_list_files[0]
            file_stem = content_list_path.stem.replace("_content_list", "")
            middle_json_path = auto_dir / f"{file_stem}_middle.json"

            # Get PDF file size if available
            origin_pdf = _find_origin_pdf(book_id)
            pdf_size = origin_pdf.stat().st_size if origin_pdf else 0

            books.append({
                "book_id": book_id,
                "title": _humanize_title(Path(book_id).name),
                "category": category,
                "page_count": _count_pages(middle_json_path),
                "chunk_count": _count_content_items(content_list_path),
                "pdf_size_bytes": pdf_size,
            })
            # Don't descend into auto/ — this is a leaf book
            dirnames.clear()

    return books


# ── Route handlers ───────────────────────────────────────────────────────────


@router.get("/books")
async def list_books():
    """List all processed books discovered from the filesystem.

    Scans data/mineru_output/{category}/{book_dir}/ for content_list.json
    to determine which books have been parsed by MinerU.
    """
    return _discover_books()


@router.get("/books/pdf/{book_id:path}")
async def get_pdf(book_id: str, variant: str = "origin"):
    """Serve PDF file for a book.

    variant=origin  → source PDF (MinerU *_origin.pdf or raw_pdfs/)
    variant=layout  → MinerU layout-analysed PDF (*_layout.pdf)
    """
    if variant == "layout":
        pdf_path = _find_layout_pdf(book_id)
    else:
        pdf_path = _find_origin_pdf(book_id)

    if not pdf_path:
        raise HTTPException(
            404, f"PDF not found for book: {book_id} (variant={variant})"
        )

    from starlette.responses import Response as RawResponse
    from urllib.parse import quote

    pdf_bytes = pdf_path.read_bytes()
    # RFC 5987: use filename* for non-ASCII names, with ASCII fallback
    safe_name = quote(f"{book_id}.pdf", safe="")
    content_disp = f'inline; filename="document.pdf"; filename*=UTF-8\'\'{safe_name}'
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disp,
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/books/toc/{book_id:path}")
async def get_toc(book_id: str):
    """Get table of contents for a book.

    Extracts TOC from MinerU content_list.json heading items
    (text_level 1-3). Returns list of { id, level, number, title, pdf_page }.
    """
    content_list = _load_content_list(book_id)
    if not content_list:
        raise HTTPException(
            404, f"No content data found for book: {book_id}"
        )

    toc = _extract_toc(book_id, content_list)
    if not toc:
        # Even if content_list exists, there may be no headings.
        # Return empty list instead of 404 (the book exists, just no TOC).
        return []

    return toc


@router.get("/books/cover/{book_id:path}")
async def get_cover(book_id: str):
    """Get book cover image (rendered from PDF page 1).

    Returns a PNG image of the first page of the book's source PDF,
    suitable for use as a cover thumbnail.
    """
    from fastapi.responses import Response as FastAPIResponse

    from engine_v2.readers.cover_extractor import extract_cover_for_book

    png_bytes = extract_cover_for_book(book_id, MINERU_OUTPUT_DIR)
    if not png_bytes:
        raise HTTPException(
            404, f"Could not extract cover for book: {book_id}"
        )

    return FastAPIResponse(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/books/chunks/{book_id:path}")
async def get_chunks(book_id: str, toc_id: int | None = None, limit: int = 30):
    """Get text content for a book chapter from MinerU content_list.json.

    Uses the TOC entry's pdf_page to determine the page range for the chapter,
    then extracts text content from content_list items within that range.

    Args:
        book_id: Book identifier.
        toc_id: TOC entry ID (from GET /books/{id}/toc). If provided, filters
                content to the page range of that chapter.
        limit: Max number of content items to return.
    """
    content_list = _load_content_list(book_id)
    if not content_list:
        raise HTTPException(404, f"No content data found for book: {book_id}")

    # If toc_id is specified, determine the content range
    start_idx = 0
    end_idx = len(content_list)

    if toc_id is not None:
        toc = _extract_toc(book_id, content_list)
        # Find the TOC entry
        entry = None
        next_entry = None
        for i, t in enumerate(toc):
            if t["id"] == toc_id:
                entry = t
                for j in range(i + 1, len(toc)):
                    if toc[j]["level"] <= t["level"]:
                        next_entry = toc[j]
                        break
                break

        if entry:
            entry_page = entry["pdf_page"] - 1  # Convert to 0-indexed
            # Find the content_list index where this chapter starts
            # Match by page_idx >= entry_page
            for ci, item in enumerate(content_list):
                if item.get("page_idx", -1) >= entry_page:
                    start_idx = ci
                    break

            if next_entry:
                next_page = next_entry["pdf_page"] - 1
                for ci, item in enumerate(content_list):
                    if item.get("page_idx", -1) >= next_page:
                        end_idx = ci
                        break

    # Extract content items from the determined range
    chunks = []
    for item in content_list[start_idx:end_idx]:
        content_type = item.get("type", "text")
        text = item.get("text", "").strip()
        if not text or len(text) < 5:
            continue

        page_idx = item.get("page_idx", 0)
        chunks.append({
            "id": f"{book_id}_p{page_idx}_{len(chunks)}",
            "text": text,
            "page_idx": page_idx + 1,  # Return as 1-indexed for display
            "content_type": content_type,
        })

        if len(chunks) >= limit:
            break

    return {"chunks": chunks, "count": len(chunks)}


@router.get("/books/parse-stats/{book_id:path}")
async def get_parse_stats(
    book_id: str,
    content_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get MinerU parse statistics for a book.

    Reads content_list.json and middle.json to return:
      - totalItems / totalPages / filteredCount
      - typeCounts (text, table, image, title, equation, discarded breakdown)
      - samples (paginated, optionally filtered by content_type)

    Query params (AQ-07):
      content_type — filter by type (text/image/table/equation/discarded)
      limit — max samples to return (default 50)
      offset — pagination offset (default 0)

    Ref: AQ-03 + AQ-07 — Parse Preview Tab data source + sub-tabs
    """
    auto_dir = _get_auto_dir(book_id)
    if not auto_dir:
        raise HTTPException(
            404, f"No MinerU output found for book: {book_id}"
        )

    # MinerU uses the stem (last path component) for output filenames
    stem = Path(book_id).name
    content_list_path = auto_dir / f"{stem}_content_list.json"
    middle_json_path = auto_dir / f"{stem}_middle.json"

    if not content_list_path.exists():
        raise HTTPException(
            404, f"No content_list.json found for book: {book_id}"
        )

    # Load content list
    try:
        with open(content_list_path, "r", encoding="utf-8") as f:
            content_list = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(500, f"Failed to read content_list.json: {exc}")

    if not isinstance(content_list, list):
        content_list = []

    # Type distribution (always computed from full list)
    type_counts: dict[str, int] = {}
    for item in content_list:
        ctype = item.get("type", "unknown")
        type_counts[ctype] = type_counts.get(ctype, 0) + 1

    # Filter by content_type if specified (AQ-07)
    if content_type:
        filtered = [
            item for item in content_list
            if item.get("type", "unknown") == content_type
        ]
    else:
        filtered = content_list

    filtered_count = len(filtered)

    # Paginated samples
    page_slice = filtered[offset : offset + limit]
    samples = []
    for item in page_slice:
        text = item.get("text", "").strip()
        sample: dict = {
            "text": text[:300] if text else "",
            "pageIdx": item.get("page_idx", 0),
            "contentType": item.get("type", "text"),
            "bbox": item.get("bbox"),
        }
        # For image items, include the image path if available (AQ-07)
        if item.get("type") == "image":
            img_path = item.get("img_path") or item.get("image_path")
            if img_path:
                sample["imgPath"] = img_path
        samples.append(sample)

    return {
        "bookId": book_id,
        "bookTitle": _humanize_title(book_id),
        "totalItems": len(content_list),
        "totalPages": _count_pages(middle_json_path),
        "typeCounts": type_counts,
        "filteredCount": filtered_count,
        "samples": samples,
        "offset": offset,
        "limit": limit,
    }

