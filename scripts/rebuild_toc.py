"""
Extract table-of-contents bookmarks from original source PDFs and insert
structured TOC entries into the database.

Only books that have a ``source_pdf`` asset with embedded PDF bookmarks will
get TOC entries.  Books without bookmarks are silently skipped (the frontend
will hide the TOC sidebar for those books).

Creates (or re-creates) a ``toc_entries`` table with columns:
    id, book_id (FK), level, number, title, pdf_page, sort_order

Usage:
    uv run python scripts/rebuild_toc.py
    uv run python scripts/rebuild_toc.py --book andriesse_practical_binary_analysis
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

import pymupdf  # PyMuPDF

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "textbook_rag.sqlite3"
TEXTBOOKS_DIR = BASE_DIR / "textbooks"

# ── Schema ───────────────────────────────────────────────────────────────────

TOC_SCHEMA = """
CREATE TABLE IF NOT EXISTS toc_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    level       INTEGER NOT NULL DEFAULT 1,
    number      TEXT    NOT NULL DEFAULT '',
    title       TEXT    NOT NULL,
    pdf_page    INTEGER NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_toc_entries_book ON toc_entries(book_id);
CREATE INDEX IF NOT EXISTS idx_toc_entries_page ON toc_entries(book_id, pdf_page);
"""

# ── Helpers ──────────────────────────────────────────────────────────────────

# Try to split "Chapter 3: Foo" or "3.2 Foo" into (number, title)
_NUMBERED_RE = re.compile(
    r"^(?:Chapter\s+)?(\d{1,3}(?:\.\d{1,3})*)[.:\s]+\s*(.+)$", re.IGNORECASE
)


def _split_number_title(raw_title: str) -> tuple[str, str]:
    """Split a bookmark title into (number, title).

    Returns ("", raw_title) when no leading number is found.
    """
    m = _NUMBERED_RE.match(raw_title.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return "", raw_title.strip()


def extract_toc_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract TOC bookmarks from a PDF.

    Returns a list of dicts with keys: level, number, title, pdf_page.
    ``pdf_page`` is 1-indexed (matching react-pdf's pageNumber prop).
    """
    doc = pymupdf.open(str(pdf_path))
    try:
        toc = doc.get_toc(simple=True)  # [(level, title, page), ...]
    finally:
        doc.close()

    if not toc:
        return []

    entries: list[dict] = []
    for level, raw_title, page in toc:
        if page < 1:
            continue
        number, title = _split_number_title(raw_title)
        if not title:
            continue
        entries.append({
            "level": level,
            "number": number,
            "title": title,
            "pdf_page": page,
        })
    return entries


# ── Database operations ──────────────────────────────────────────────────────

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(TOC_SCHEMA)
    conn.commit()


def clear_toc(conn: sqlite3.Connection, book_pk: int | None = None) -> int:
    """Delete existing TOC entries. Returns count deleted."""
    if book_pk is None:
        cur = conn.execute("DELETE FROM toc_entries")
    else:
        cur = conn.execute("DELETE FROM toc_entries WHERE book_id = ?", (book_pk,))
    conn.commit()
    return cur.rowcount


def insert_toc_entries(
    conn: sqlite3.Connection, book_pk: int, entries: list[dict],
) -> int:
    """Insert TOC entries for one book. Returns count inserted."""
    cur = conn.cursor()
    for i, e in enumerate(entries):
        cur.execute(
            "INSERT INTO toc_entries (book_id, level, number, title, pdf_page, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (book_pk, e["level"], e.get("number", ""), e["title"],
             e["pdf_page"], i),
        )
    conn.commit()
    return len(entries)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract TOC from source PDFs and populate toc_entries table",
    )
    parser.add_argument("--book", type=str, default=None,
                        help="Only process a specific book (by book_id slug)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Run rebuild_db.py first.")
        raise SystemExit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    ensure_schema(conn)

    # Fetch books that have a source_pdf asset
    if args.book:
        books = conn.execute(
            "SELECT b.id, b.book_id, ba.path AS pdf_rel "
            "FROM books b "
            "JOIN book_assets ba ON ba.book_id = b.id AND ba.asset_kind = 'source_pdf' "
            "WHERE b.book_id = ?",
            (args.book,),
        ).fetchall()
        if not books:
            print(f"❌ Book '{args.book}' not found or has no source_pdf")
            raise SystemExit(1)
    else:
        books = conn.execute(
            "SELECT b.id, b.book_id, ba.path AS pdf_rel "
            "FROM books b "
            "JOIN book_assets ba ON ba.book_id = b.id AND ba.asset_kind = 'source_pdf' "
            "ORDER BY b.book_id",
        ).fetchall()

    # Also clear TOC for books with NO source_pdf (were using old md-based entries)
    all_book_ids = {
        r["id"]
        for r in conn.execute("SELECT id FROM books").fetchall()
    }
    books_with_src = {r["id"] for r in books}
    for orphan_pk in all_book_ids - books_with_src:
        clear_toc(conn, orphan_pk)

    total_entries = 0
    processed = 0
    skipped = 0

    for book_row in books:
        book_pk = book_row["id"]
        book_id = book_row["book_id"]
        pdf_rel = book_row["pdf_rel"]

        pdf_path = BASE_DIR / pdf_rel
        if not pdf_path.exists():
            print(f"  ⚠ {book_id}: source PDF not found at {pdf_rel}")
            skipped += 1
            continue

        entries = extract_toc_from_pdf(pdf_path)
        if not entries:
            print(f"  ⚠ {book_id}: no bookmarks in PDF")
            clear_toc(conn, book_pk)
            skipped += 1
            continue

        cleared = clear_toc(conn, book_pk)
        count = insert_toc_entries(conn, book_pk, entries)
        total_entries += count
        processed += 1

        status = f"  ✓ {book_id}: {count} toc entries"
        if cleared:
            status += f" (replaced {cleared})"
        print(status)

    conn.close()

    print(f"\n{'='*60}")
    print(f"✅ TOC rebuild complete!")
    print(f"   📖 {processed} books with TOC, {skipped} skipped")
    print(f"   📑 {total_entries} total TOC entries")


if __name__ == "__main__":
    main()
