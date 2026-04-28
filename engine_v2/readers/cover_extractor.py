"""Cover extraction from PDF first page.

Uses PyMuPDF (fitz) to render the first page of a book's source PDF
as a high-quality PNG image for use as book cover thumbnails.

Part of the readers/ module — extends BaseReader with cover extraction
capability that MinerU doesn't provide.
"""

from __future__ import annotations

from io import BytesIO
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
    categories: list[str] | None = None,
) -> bytes | None:
    """Extract cover for a book by scanning known PDF locations.

    Search order:
        1. MinerU auto/{book_id}_origin.pdf
        2. raw_pdfs/{category}/{book_id}.pdf

    Args:
        book_id: Book identifier (directory name).
        mineru_dir: Base MinerU output directory.
        categories: Category directories to scan (default: textbooks/ecdev/real_estate).

    Returns:
        PNG image bytes, or None if no PDF found.
    """
    if categories is None:
        categories = ["textbooks", "ecdev", "real_estate"]

    data_dir = mineru_dir.parent  # mineru_output is under data/

    # Priority 1: MinerU auto/ origin PDF
    for cat in categories:
        auto_dir = mineru_dir / cat / book_id / book_id / "auto"
        origin_pdf = auto_dir / f"{book_id}_origin.pdf"
        if origin_pdf.exists():
            return extract_cover(origin_pdf)

    # Priority 2: raw_pdfs/
    for cat in categories:
        raw_pdf = data_dir / "raw_pdfs" / cat / f"{book_id}.pdf"
        if raw_pdf.exists():
            return extract_cover(raw_pdf)

    logger.debug("No PDF found for cover extraction: {}", book_id)
    return None
