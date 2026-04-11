"""GET /engine/books — book listing, PDF serving, TOC.

Serves PDFs from local filesystem and provides book metadata
from the engine SQLite database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from engine.config import DATABASE_PATH, DATA_DIR

router = APIRouter(tags=["books"])

# All PDF source directories
PDF_DIRS = [
    DATA_DIR / "raw_pdfs" / "textbooks",
    DATA_DIR / "raw_pdfs" / "ecdev",
    DATA_DIR / "raw_pdfs" / "real_estate",
    DATA_DIR / "raw_pdfs" / "uploads",
]


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _find_pdf(book_id: str) -> Path | None:
    """Find PDF file across all known directories."""
    # 1. Check book_assets table
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT ba.path FROM book_assets ba "
            "JOIN books b ON ba.book_id = b.id "
            "WHERE b.book_id = ? AND ba.asset_kind IN ('source_pdf', 'origin_pdf') "
            "ORDER BY CASE ba.asset_kind WHEN 'source_pdf' THEN 1 ELSE 2 END "
            "LIMIT 1",
            (book_id,),
        ).fetchone()
        conn.close()
        if row:
            p = DATA_DIR.parent / row["path"]
            if p.exists():
                return p
    except Exception:
        pass

    # 2. Scan directories
    for d in PDF_DIRS:
        p = d / f"{book_id}.pdf"
        if p.exists():
            return p

    return None


def _find_layout_pdf(book_id: str) -> Path | None:
    """Find MinerU layout-analyzed PDF.
    
    Mirrors v1.0 logic: look up origin_pdf in book_assets,
    then replace _origin.pdf → _layout.pdf in the path.
    """
    _PROJECT_ROOT = DATA_DIR.parent

    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT ba.path FROM book_assets ba "
            "JOIN books b ON ba.book_id = b.id "
            "WHERE b.book_id = ? AND ba.asset_kind = 'origin_pdf'",
            (book_id,),
        ).fetchone()
        conn.close()
        if row:
            rel = row["path"].replace("_origin.pdf", "_layout.pdf")
            full = _PROJECT_ROOT / rel
            if full.exists():
                return full
    except Exception:
        pass

    # Fallback to source PDF
    return _find_pdf(book_id)


@router.get("/books")
def list_books():
    """List all books with metadata."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, book_id, title, authors, page_count, chapter_count, chunk_count "
        "FROM books ORDER BY title"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "book_id": r["book_id"],
            "title": r["title"],
            "authors": r["authors"],
            "page_count": r["page_count"],
            "chapter_count": r["chapter_count"],
            "chunk_count": r["chunk_count"],
        }
        for r in rows
    ]


@router.get("/books/{book_id}/pdf")
def get_pdf(book_id: str, variant: str = "origin"):
    """Serve PDF file for a book (by engine book_id string).
    
    variant=origin  → source PDF (raw_pdfs/)
    variant=layout  → MinerU layout-analyzed PDF (*_origin.pdf in auto/)
    """
    if variant == "layout":
        pdf_path = _find_layout_pdf(book_id)
    else:
        pdf_path = _find_pdf(book_id)
    
    if not pdf_path:
        raise HTTPException(404, f"PDF not found for book: {book_id} (variant={variant})")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"{book_id}.pdf",
    )


@router.get("/books/{book_id}/toc")
def get_toc(book_id: str):
    """Get table of contents for a book."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT t.level, t.number, t.title, t.pdf_page "
        "FROM toc_entries t "
        "JOIN books b ON t.book_id = b.id "
        "WHERE b.book_id = ? "
        "ORDER BY t.sort_order",
        (book_id,),
    ).fetchall()

    if not rows:
        # Fallback to chapters table
        rows = conn.execute(
            "SELECT 1 as level, c.chapter_key as number, c.title, 1 as pdf_page "
            "FROM chapters c "
            "JOIN books b ON c.book_id = b.id "
            "WHERE b.book_id = ? "
            "ORDER BY c.id",
            (book_id,),
        ).fetchall()

    conn.close()
    return [
        {
            "id": i,
            "level": r["level"],
            "number": r["number"],
            "title": r["title"],
            "pdf_page": r["pdf_page"],
        }
        for i, r in enumerate(rows, 1)
    ]
