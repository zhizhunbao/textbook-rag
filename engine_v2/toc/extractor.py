"""TOC extraction — PDF bookmarks (primary) + MinerU fallback.

Project-specific module — no LlamaIndex equivalent.
Extracts structured TOC from two sources in priority order:

  1. PDF embedded bookmarks via PyMuPDF (publisher-authored, clean)
  2. MinerU content_list.json text_level headings (OCR-based, noisy → filtered)

Used by:
    - api/routes/books.py  (GET /engine/books/{id}/toc)
    - readers/             (document structure metadata)
    - chunking/            (chapter-aware splitting)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger

# ── LaTeX artifact cleanup ───────────────────────────────────────────────────

# MinerU OCR sometimes emits raw LaTeX instead of Unicode symbols
_LATEX_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\$\\bullet\$"), "•"),
    (re.compile(r"\$\\cdot\$"), "·"),
    (re.compile(r"\$\\rightarrow\$"), "→"),
    (re.compile(r"\$\\leftarrow\$"), "←"),
    (re.compile(r"\$\\star\$"), "★"),
    (re.compile(r"\$\\circ\$"), "○"),
    (re.compile(r"\$\\times\$"), "×"),
    (re.compile(r"\$\\diamond\$"), "◇"),
    # Catch-all: strip remaining $...$ inline math that looks like a single symbol
    (re.compile(r"\$\\(\w+)\$"), ""),
]


def _clean_latex(text: str) -> str:
    """Replace common LaTeX artifacts with Unicode equivalents."""
    for pat, repl in _LATEX_MAP:
        text = pat.sub(repl, text)
    return text.strip()

# ── Shared helpers ───────────────────────────────────────────────────────────

# Pattern: "Chapter 3: Foo", "3.2 Foo", "A.1 Foo"
_NUMBERED_RE = re.compile(
    r"^(?:Chapter\s+)?(\d{1,3}(?:\.\d{1,3})*)[.:\s]+\s*(.+)$", re.IGNORECASE
)

_APPENDIX_RE = re.compile(
    r"^Appendix\s+([A-Z](?:\.\d+)?)[.:\s]*(.+)$", re.IGNORECASE
)


def _split_number_title(raw_title: str) -> tuple[str, str]:
    """Split a heading/bookmark title into (number, title).

    Returns ("", raw_title) when no leading number is found.
    """
    text = raw_title.strip()
    m = _NUMBERED_RE.match(text)
    if m:
        return m.group(1), m.group(2).strip().rstrip(".,: ")

    m = _APPENDIX_RE.match(text)
    if m:
        return f"App.{m.group(1)}", m.group(2).strip().rstrip(".,: ")

    return "", text


# ── Source 1: PDF bookmarks (primary, high quality) ──────────────────────────


def extract_toc_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract TOC from PDF embedded bookmarks via PyMuPDF.

    This is the preferred source — bookmarks are authored by the publisher
    and contain clean, hierarchical chapter/section structure.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of dicts: { id, level, number, title, pdf_page }
        pdf_page is 1-indexed for frontend display.
        Empty list if no bookmarks found.
    """
    try:
        import pymupdf
    except ImportError:
        logger.warning("pymupdf not installed — PDF bookmark extraction unavailable")
        return []

    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception:
        logger.exception("Failed to open PDF: {}", pdf_path)
        return []

    try:
        toc = doc.get_toc(simple=True)  # [(level, title, page), ...]
    finally:
        doc.close()

    if not toc:
        return []

    entries: list[dict] = []
    for idx, (level, raw_title, page) in enumerate(toc, start=1):
        if page < 1:
            continue
        number, title = _split_number_title(raw_title)
        if not title:
            continue
        entries.append({
            "id": idx,
            "level": level,
            "number": number,
            "title": title,
            "pdf_page": page,
        })

    return entries


# ── Source 2: MinerU content_list.json (fallback, filtered) ──────────────────

# Titles that are clearly NOT TOC headings — common in technical books
_NOISE_TITLES = frozenset({
    "NOTE", "TIP", "WARNING", "CAUTION", "IMPORTANT",
    "EXERCISE", "EXAMPLE", "SOLUTION", "PROOF", "THEOREM",
    "DEFINITION", "LEMMA", "COROLLARY", "PROPOSITION",
    "ABSTRACT", "SUMMARY",
})

# Patterns that indicate noise rather than real headings
_NOISE_PATTERNS = re.compile(
    r"^(?:"
    r"import\s+\w|"                          # code: "import requests"
    r"from\s+\w+\s+import|"                  # code: "from foo import bar"
    r"@\w+|"                                 # decorators: "@dataclass"
    r"def\s+\w+|"                            # code: "def foo"
    r"class\s+\w+|"                          # code: "class Foo"
    r"\d{3,}-\d{3,}|"                        # phone numbers
    r"https?://|"                            # URLs
    r"[A-Z][a-z]+\s+width\s|"               # "Constant width bold"
    r"EXERCISE\s+FOR\s+THE\s+READER"         # admonition titles
    r")",
    re.IGNORECASE,
)


def load_content_list(auto_dir: Path, book_id: str) -> list[dict]:
    """Load content_list.json for a book from its MinerU auto/ directory.

    Args:
        auto_dir: Path to the MinerU auto/ output directory.
        book_id: Book identifier (directory name).

    Returns:
        Parsed content_list as a list of dicts, or empty list on failure.
    """
    content_list_path = auto_dir / f"{book_id}_content_list.json"
    if not content_list_path.exists():
        return []
    try:
        with open(content_list_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def extract_toc_from_content_list(content_list: list[dict]) -> list[dict]:
    """Fallback: extract TOC from MinerU content_list.json headings.

    MinerU text_level is an OCR/layout-analysis heuristic, not a real TOC.
    We apply aggressive filtering to remove noise (admonition titles,
    code snippets, short fragments, etc.).

    Args:
        content_list: Raw MinerU content_list.json data.

    Returns:
        List of dicts: { id, level, number, title, pdf_page }
        pdf_page is 1-indexed for frontend display.
    """
    entries: list[dict] = []
    entry_id = 0

    for item in content_list:
        if item.get("type") != "text":
            continue

        text_level = item.get("text_level")
        if text_level is None or text_level < 1 or text_level > 3:
            continue

        text = _clean_latex(item.get("text", "").strip())

        # --- Noise filters ---

        # Too short or too long
        if len(text) < 3 or len(text) > 200:
            continue

        # Known noise titles (exact match, case-insensitive)
        if text.upper().rstrip(".!:") in _NOISE_TITLES:
            continue

        # Pattern-based noise rejection
        if _NOISE_PATTERNS.match(text):
            continue

        # All-uppercase short fragments that are likely admonition labels
        if text.isupper() and len(text) < 40:
            continue

        # --- Passed filters → include as TOC entry ---
        number, title = _split_number_title(text)
        if not title or len(title) < 2:
            continue

        entry_id += 1
        entries.append({
            "id": entry_id,
            "level": text_level,
            "number": number,
            "title": title,
            "pdf_page": item.get("page_idx", 0) + 1,  # 0-indexed → 1-indexed
        })

    return entries


# ── Public API: unified extraction with fallback ─────────────────────────────


def find_pdf_for_book(
    book_id: str,
    mineru_output_dir: Path,
    raw_pdf_dirs: list[Path] | None = None,
) -> Path | None:
    """Locate the source PDF for a book (for bookmark extraction).

    Priority (raw PDFs retain publisher bookmarks; MinerU strips them):
      1. raw_pdfs/{category}/{book_id}.pdf  — original with bookmarks
      2. MinerU auto/{book_id}_origin.pdf   — fallback (no bookmarks)

    Args:
        book_id: Book identifier.
        mineru_output_dir: Root MinerU output directory.
        raw_pdf_dirs: Optional list of raw PDF directories to search.

    Returns:
        Path to PDF, or None if not found.
    """

    # Check raw PDF directories first (bookmarks preserved)
    if raw_pdf_dirs:
        for d in raw_pdf_dirs:
            p = d / f"{book_id}.pdf"
            if p.exists():
                return p

    # Fallback: MinerU _origin.pdf (bookmarks usually stripped, but try)
    # Scan all category directories dynamically
    if mineru_output_dir.is_dir():
        for cat_dir in sorted(mineru_output_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            origin = cat_dir / book_id / book_id / "auto" / f"{book_id}_origin.pdf"
            if origin.exists():
                return origin

    return None


def extract_toc(
    content_list: list[dict],
    *,
    pdf_path: Path | None = None,
) -> list[dict]:
    """Unified TOC extraction with automatic fallback.

    Strategy:
      1. If pdf_path is provided, try PDF bookmarks first (high quality).
      2. Fall back to MinerU content_list.json headings (filtered).

    Args:
        content_list: Raw MinerU content_list.json data (always passed
            for fallback).
        pdf_path: Optional path to source PDF for bookmark extraction.

    Returns:
        List of dicts: { id, level, number, title, pdf_page }
    """
    # Strategy 1: PDF bookmarks (preferred)
    if pdf_path and pdf_path.exists():
        entries = extract_toc_from_pdf(pdf_path)
        if entries:
            logger.info(
                "TOC from PDF bookmarks: {} entries ({})",
                len(entries), pdf_path.name,
            )
            return entries
        logger.debug("No PDF bookmarks in {}, falling back to MinerU", pdf_path.name)

    # Strategy 2: MinerU content_list headings (filtered)
    entries = extract_toc_from_content_list(content_list)
    if entries:
        logger.info("TOC from MinerU content_list: {} entries (filtered)", len(entries))
    else:
        logger.debug("No TOC entries extracted from either source")

    return entries
