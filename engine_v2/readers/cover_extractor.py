"""Cover extraction from PDF first page.

Uses PyMuPDF (fitz) to render the first page of a book's source PDF
as a high-quality PNG image for use as book cover thumbnails.

Part of the readers/ module — extends BaseReader with cover extraction
capability that MinerU doesn't provide.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

# Default cover dimensions (portrait book aspect ratio)
DEFAULT_WIDTH = 400
DEFAULT_DPI = 150


def extract_cover(pdf_path: Path, width: int = DEFAULT_WIDTH) -> bytes | None:
    """Render the first page of a PDF as a PNG image.

    Args:
        pdf_path: Path to the source PDF file.
        width: Target width in pixels (height auto-calculated from aspect ratio).

    Returns:
        PNG image bytes, or None if extraction fails.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed — cover extraction unavailable")
        return None

    if not pdf_path.exists():
        logger.warning("PDF not found for cover extraction: {}", pdf_path)
        return None

    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count == 0:
            doc.close()
            return None

        page = doc[0]
        # Calculate zoom to achieve target width
        page_rect = page.rect
        zoom = width / page_rect.width
        mat = fitz.Matrix(zoom, zoom)

        # Render to pixmap (high quality)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")

        doc.close()
        logger.info(
            "Extracted cover from {} ({}x{} px)",
            pdf_path.name, pix.width, pix.height,
        )
        return png_bytes

    except Exception as exc:
        logger.error("Failed to extract cover from {}: {}", pdf_path, exc)
        return None


def extract_cover_for_book(
    book_id: str,
    mineru_dir: Path,
) -> bytes | None:
    """Extract cover for a book by scanning all category directories.

    Search order:
        1. MinerU auto/{book_id}_origin.pdf  (all categories, dynamic scan)
        2. raw_pdfs/{category}/{book_id}.pdf  (all categories, dynamic scan)

    Args:
        book_id: Book identifier (directory name).
        mineru_dir: Base MinerU output directory.

    Returns:
        PNG image bytes, or None if no PDF found.
    """
    data_dir = mineru_dir.parent  # mineru_output is under data/

    # Priority 1: MinerU auto/ origin PDF (scan all category dirs dynamically)
    if mineru_dir.is_dir():
        for cat_dir in sorted(mineru_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            # MinerU uses the stem (last path component) for output filenames
            stem = Path(book_id).name
            # New flat layout: {cat}/{book_id}/auto/
            origin_pdf = cat_dir / book_id / "auto" / f"{stem}_origin.pdf"
            if origin_pdf.exists():
                return extract_cover(origin_pdf)
            # Legacy nested layout: {cat}/{book_id}/{stem}/auto/
            origin_pdf = cat_dir / book_id / stem / "auto" / f"{stem}_origin.pdf"
            if origin_pdf.exists():
                return extract_cover(origin_pdf)

    # Priority 2: raw_pdfs/ (scan all subdirectories dynamically)
    raw_pdf_root = data_dir / "raw_pdfs"
    if raw_pdf_root.is_dir():
        for raw_dir in sorted(raw_pdf_root.iterdir()):
            if not raw_dir.is_dir():
                continue
            raw_pdf = raw_dir / f"{book_id}.pdf"
            if raw_pdf.exists():
                return extract_cover(raw_pdf)

    logger.debug("No PDF found for cover extraction: {}", book_id)
    return None
