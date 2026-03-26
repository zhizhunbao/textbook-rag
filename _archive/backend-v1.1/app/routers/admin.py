"""
Admin router — pipeline status monitoring.

GET /api/v1/admin/pipeline-status
    Returns per-PDF ingestion pipeline status across all categories.

Each document entry reports:
  - mineru_done   : MinerU output (content_list.json) exists
  - chunked       : present in SQLite books table with chunk_count > 0
  - toc_indexed   : toc_entries rows exist for this book
  - embedded      : chroma_document_id is populated for at least one chunk
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

BASE_DIR = Path(__file__).resolve().parents[3]
MINERU_DIR = BASE_DIR / "data" / "mineru_output"
CHROMA_DIR = BASE_DIR / "data" / "chroma_persist"
DB_PATH = BASE_DIR / "data" / "textbook_rag.sqlite3"

SOURCE_DIRS: dict[str, Path] = {
    "textbook":    BASE_DIR / "data" / "raw_pdfs" / "textbooks",
    "ecdev":       BASE_DIR / "data" / "raw_pdfs" / "ecdev",
    "real_estate": BASE_DIR / "data" / "raw_pdfs" / "real_estate",
}


def _get_db_stats() -> dict[str, dict]:
    """Return {book_id: {chunk_count, toc_count, embedded_count}} from SQLite."""
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            b.book_id,
            b.chunk_count,
            COUNT(DISTINCT te.id)  AS toc_count,
            COUNT(DISTINCT CASE WHEN c.chroma_document_id IS NOT NULL THEN c.id END) AS embedded_count
        FROM books b
        LEFT JOIN toc_entries te ON te.book_id = b.id
        LEFT JOIN chunks c       ON c.book_id  = b.id
        GROUP BY b.book_id
        """
    ).fetchall()
    conn.close()
    return {
        r["book_id"]: {
            "chunk_count":    r["chunk_count"],
            "toc_count":      r["toc_count"],
            "embedded_count": r["embedded_count"],
        }
        for r in rows
    }


@router.get("/pipeline-status")
def pipeline_status() -> dict:
    """Return ingestion pipeline status for every PDF in the corpus."""
    db_stats = _get_db_stats()
    chroma_ready = CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir())

    categories: list[dict] = []

    for category, src_dir in SOURCE_DIRS.items():
        if not src_dir.exists():
            continue

        docs: list[dict] = []
        for pdf in sorted(src_dir.rglob("*.pdf")):
            name = pdf.stem

            # Stage 1: MinerU output exists?
            mineru_out = MINERU_DIR / category / name / name / "auto"
            content_list = mineru_out / f"{name}_content_list.json"
            mineru_done = content_list.exists()

            # Stage 2-4: SQLite stats
            stats = db_stats.get(name, {})
            chunk_count    = stats.get("chunk_count", 0)
            toc_count      = stats.get("toc_count", 0)
            embedded_count = stats.get("embedded_count", 0)

            chunked  = chunk_count > 0
            toc_done = toc_count > 0
            # embedded: SQLite has chroma_document_id populated
            embedded = embedded_count > 0 and chroma_ready

            # Overall status
            if embedded:
                status = "ready"
            elif chunked:
                status = "partial"  # chunked but not embedded yet
            elif mineru_done:
                status = "mineru_only"
            else:
                status = "pending"

            docs.append({
                "name":           name,
                "pdf_path":       str(pdf.relative_to(BASE_DIR)),
                "status":         status,
                "mineru_done":    mineru_done,
                "chunked":        chunked,
                "chunk_count":    chunk_count,
                "toc_indexed":    toc_done,
                "toc_count":      toc_count,
                "embedded":       embedded,
                "embedded_count": embedded_count,
            })

        categories.append({
            "category": category,
            "total":    len(docs),
            "ready":    sum(1 for d in docs if d["status"] == "ready"),
            "partial":  sum(1 for d in docs if d["status"] == "partial"),
            "pending":  sum(1 for d in docs if d["status"] == "pending"),
            "docs":     docs,
        })

    # Global summary
    all_docs = [d for cat in categories for d in cat["docs"]]
    summary = {
        "total":       len(all_docs),
        "ready":       sum(1 for d in all_docs if d["status"] == "ready"),
        "partial":     sum(1 for d in all_docs if d["status"] == "partial"),
        "mineru_only": sum(1 for d in all_docs if d["status"] == "mineru_only"),
        "pending":     sum(1 for d in all_docs if d["status"] == "pending"),
        "chroma_store_exists": chroma_ready,
    }

    return {"summary": summary, "categories": categories}
