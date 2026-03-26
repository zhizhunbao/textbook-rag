"""Book repository — read-only access to books, chapters, pages, and assets."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from backend.app.config import TEXTBOOKS_DIR

# Project root: three levels up from backend/app/repositories/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def list_books(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        "SELECT b.id, b.book_id, b.title, b.authors, b.page_count, "
        "b.chapter_count, b.chunk_count "
        "FROM books b "
        "WHERE EXISTS (SELECT 1 FROM toc_entries t WHERE t.book_id = b.id) "
        "ORDER BY b.title"
    ).fetchall()
    return [dict(r) for r in rows]


def get_book(db: sqlite3.Connection, book_id: int) -> dict | None:
    row = db.execute(
        "SELECT id, book_id, title, authors, page_count, chapter_count, chunk_count "
        "FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()
    if row is None:
        return None
    book = dict(row)
    chapters = db.execute(
        "SELECT c.id, c.chapter_key, c.title, "
        "MIN(p.page_number) + 1 AS start_page "
        "FROM chapters c "
        "LEFT JOIN chunks ck ON ck.chapter_id = c.id "
        "LEFT JOIN pages p ON p.id = ck.primary_page_id "
        "WHERE c.book_id = ? "
        "GROUP BY c.id ORDER BY c.id",
        (book_id,),
    ).fetchall()
    book["chapters"] = _enrich_chapters([dict(c) for c in chapters])
    return book


def _chapter_sort_key(ch: dict) -> tuple:
    """Natural sort key: 'ch01' -> (0, 1), 'appA' -> (1, 'A')."""
    key = ch.get("chapter_key", "")
    m = re.match(r"ch(\d+)", key)
    if m:
        return (0, int(m.group(1)))
    return (1, key)


def _enrich_chapters(chapters: list[dict]) -> list[dict]:
    """Sort chapters naturally and extract page numbers from titles."""
    chapters.sort(key=_chapter_sort_key)
    for ch in chapters:
        # Many chapter titles end with a page number, e.g. "Linear Regression 59"
        m = re.search(r"\s+(\d+)\s*$", ch.get("title", ""))
        if m:
            # Title-embedded page number is more reliable than chunk-derived one
            ch["start_page"] = int(m.group(1))
    return chapters


def get_toc(db: sqlite3.Connection, book_id: int) -> list[dict] | None:
    """Return TOC entries for a book, or None if book not found."""
    book = db.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return None
    rows = db.execute(
        "SELECT id, level, number, title, pdf_page "
        "FROM toc_entries WHERE book_id = ? ORDER BY sort_order",
        (book_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_suggestions(db: sqlite3.Connection, book_id: int, count: int = 4) -> list[str] | None:
    """Generate contextual starter questions from the book's TOC/chapters."""
    import random

    book = get_book(db, book_id)
    if book is None:
        return None

    title = book["title"]
    chapters = book.get("chapters", [])
    toc_rows = db.execute(
        "SELECT title FROM toc_entries WHERE book_id = ? AND level <= 1 ORDER BY sort_order",
        (book_id,),
    ).fetchall()
    toc_titles = [r["title"] for r in toc_rows if r["title"]]

    # Collect chapter/section names for template filling
    topic_pool: list[str] = []
    for ch in chapters:
        t = re.sub(r"\s+\d+\s*$", "", ch.get("title", "")).strip()
        if t and len(t) > 3:
            topic_pool.append(t)
    for t in toc_titles:
        t = t.strip()
        if t and len(t) > 3 and t not in topic_pool:
            topic_pool.append(t)

    # Templates — {book} = book title, {topic} = chapter/section title
    _GLOBAL = [
        "What are the main topics and structure of {book}?",
        "What prerequisites does {book} assume?",
        "What distinguishes {book} from other texts in the field?",
        "Summarize the core thesis or approach of {book}.",
    ]
    _TOPIC = [
        "Explain the key ideas in \u201c{topic}\u201d.",
        "What are the most important concepts covered in \u201c{topic}\u201d?",
        "Give a concise summary of \u201c{topic}\u201d.",
        "What practical examples or exercises appear in \u201c{topic}\u201d?",
        "How does \u201c{topic}\u201d relate to earlier chapters?",
    ]

    suggestions: list[str] = []

    # Always include one global question
    suggestions.append(random.choice(_GLOBAL).format(book=title))

    # Fill remaining slots with topic-specific questions
    if topic_pool:
        sampled = random.sample(topic_pool, min(len(topic_pool), count - 1))
        templates = random.sample(_TOPIC, min(len(_TOPIC), len(sampled)))
        for topic, tmpl in zip(sampled, templates):
            suggestions.append(tmpl.format(topic=topic))

    # Pad with more global questions if needed
    while len(suggestions) < count:
        q = random.choice(_GLOBAL).format(book=title)
        if q not in suggestions:
            suggestions.append(q)
        else:
            break

    return suggestions[:count]


def get_pdf_path(
    db: sqlite3.Connection, book_id: int, *, variant: str = "origin"
) -> Path | None:
    """Return the filesystem path to the PDF for *book_id*.

    *variant* can be ``"origin"`` (default) or ``"layout"``.

    Lookup priority:
      1. ``book_assets`` row with ``asset_kind = 'source_pdf'`` (original PDFs
         kept in ``textbooks/``) — only when variant is ``"origin"``.
      2. ``book_assets`` row with ``asset_kind = 'origin_pdf'`` (MinerU copy
         under ``data/mineru_output/``).  When *variant* is ``"layout"``,
         the ``_origin.pdf`` suffix is replaced with ``_layout.pdf``.
    """
    if variant == "origin":
        # Try source_pdf first (original in textbooks/)
        row = db.execute(
            "SELECT path FROM book_assets WHERE book_id = ? AND asset_kind = 'source_pdf'",
            (book_id,),
        ).fetchone()
        if row:
            full = TEXTBOOKS_DIR / row["path"]
            if full.exists():
                return full

    # Fall back to origin_pdf (or derive layout from it)
    row = db.execute(
        "SELECT path FROM book_assets WHERE book_id = ? AND asset_kind = 'origin_pdf'",
        (book_id,),
    ).fetchone()
    if row is None:
        return None

    rel = row["path"]
    if variant == "layout":
        rel = rel.replace("_origin.pdf", "_layout.pdf")
    full = _PROJECT_ROOT / rel
    return full if full.exists() else None
