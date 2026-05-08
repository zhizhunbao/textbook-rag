"""delete routes — DELETE /engine/books/{book_id} cleanup.

Removes all engine-side data for a book:
  - ChromaDB vectors (filtered by book metadata)
  - MinerU output directory
  - Raw PDF uploads

Ref: AQ-06 — Book delete with engine cleanup
"""

from __future__ import annotations

import shutil

import chromadb
from fastapi import APIRouter
from loguru import logger

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    DATA_DIR,
    MINERU_OUTPUT_DIR,
)

# ============================================================
# Router
# ============================================================
router = APIRouter(tags=["books"])

# ============================================================
# Category directories under mineru_output/
# ============================================================
CATEGORIES = ["textbooks", "ecdev", "real_estate"]

# ============================================================
# Endpoints
# ============================================================


@router.delete("/books/{book_dir_name:path}")
async def delete_book_data(book_dir_name: str):
    """Delete all engine-side data for a book.

    Cleans up:
      1. ChromaDB vectors where metadata.book_id matches
      2. MinerU output directory
      3. Raw PDF files
    """
    logger.info("Deleting engine data for book: {}", book_dir_name)
    results: dict[str, str] = {}

    # ── 1. Delete ChromaDB vectors ───────────────────────────────
    try:
        client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION)

        # Query for vectors with matching book metadata
        existing = collection.get(
            where={"book_id": book_dir_name},
        )

        if existing and existing["ids"]:
            count = len(existing["ids"])
            collection.delete(ids=existing["ids"])
            results["chroma"] = f"Deleted {count} vectors"
            logger.info("Deleted {} ChromaDB vectors for {}", count, book_dir_name)
        else:
            results["chroma"] = "No vectors found"
            logger.info("No ChromaDB vectors found for {}", book_dir_name)

    except Exception as exc:
        results["chroma"] = f"Error: {exc}"
        logger.warning("ChromaDB cleanup failed for {}: {}", book_dir_name, exc)

    # ── 2. Delete MinerU output directory ────────────────────────
    deleted_dirs: list[str] = []
    for category in CATEGORIES:
        book_dir = MINERU_OUTPUT_DIR / category / book_dir_name
        if book_dir.is_dir():
            shutil.rmtree(book_dir, ignore_errors=True)
            deleted_dirs.append(str(book_dir))
            logger.info("Deleted MinerU output: {}", book_dir)

    # Also check for non-standard category directories
    if MINERU_OUTPUT_DIR.is_dir():
        for cat_dir in MINERU_OUTPUT_DIR.iterdir():
            if not cat_dir.is_dir():
                continue
            book_dir = cat_dir / book_dir_name
            if book_dir.is_dir() and str(book_dir) not in deleted_dirs:
                shutil.rmtree(book_dir, ignore_errors=True)
                deleted_dirs.append(str(book_dir))
                logger.info("Deleted MinerU output: {}", book_dir)

    results["mineru"] = (
        f"Deleted {len(deleted_dirs)} directories"
        if deleted_dirs
        else "No directories found"
    )

    # ── 3. Delete raw PDF uploads ────────────────────────────────
    raw_pdf_dirs = [
        DATA_DIR / "raw_pdfs" / "textbooks",
        DATA_DIR / "raw_pdfs" / "ecdev",
        DATA_DIR / "raw_pdfs" / "real_estate",
        DATA_DIR / "raw_pdfs" / "uploads",
    ]
    deleted_pdfs = 0
    for d in raw_pdf_dirs:
        pdf_path = d / f"{book_dir_name}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
            deleted_pdfs += 1
            logger.info("Deleted raw PDF: {}", pdf_path)

    # Also scan all subdirectories for dynamic categories
    raw_pdfs_root = DATA_DIR / "raw_pdfs"
    if raw_pdfs_root.is_dir():
        for sub in raw_pdfs_root.iterdir():
            if not sub.is_dir():
                continue
            pdf_path = sub / f"{book_dir_name}.pdf"
            if pdf_path.exists():
                pdf_path.unlink()
                deleted_pdfs += 1

    results["raw_pdfs"] = (
        f"Deleted {deleted_pdfs} PDF files"
        if deleted_pdfs > 0
        else "No PDF files found"
    )

    logger.info("Cleanup complete for {}: {}", book_dir_name, results)
    return {"bookId": book_dir_name, "cleanup": results}
