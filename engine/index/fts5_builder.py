"""fts5_builder.py — build SQLite FTS5 index from IngestResult.

v2.0: Extracted from scripts/rebuild_db.py (FTS5 portion).
Engine internal SQLite — not Payload PostgreSQL.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from engine.ingest.chunk_builder import IngestResult

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    authors         TEXT    NOT NULL DEFAULT '',
    category        TEXT    NOT NULL DEFAULT 'textbook',
    page_count      INTEGER NOT NULL DEFAULT 0,
    chunk_count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id        TEXT    NOT NULL UNIQUE,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    content_type    TEXT    NOT NULL DEFAULT 'text',
    text            TEXT    NOT NULL DEFAULT '',
    reading_order   INTEGER NOT NULL DEFAULT 0,
    page_number     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chunks_book ON chunks(book_id);

CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES('delete', old.id, old.text);
    INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


def build_fts5(result: IngestResult, db_path: Path) -> int:
    """Insert chunks into Engine SQLite FTS5 index.

    Returns count of inserted chunks. Safe to call multiple times (uses
    INSERT OR IGNORE on chunk_id unique constraint).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)

    cur = conn.cursor()

    # Upsert book record
    cur.execute(
        "INSERT OR IGNORE INTO books (book_id, title, authors, category, page_count)"
        " VALUES (?, ?, ?, ?, ?)",
        (result.book_dir_name, result.title, result.authors, result.category, result.total_pages),
    )
    cur.execute("SELECT id FROM books WHERE book_id = ?", (result.book_dir_name,))
    book_pk = cur.fetchone()[0]

    # Insert chunks (FTS trigger fires automatically)
    inserted = 0
    for c in result.chunks:
        try:
            cur.execute(
                "INSERT OR IGNORE INTO chunks"
                " (chunk_id, book_id, content_type, text, reading_order, page_number)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (c.chunk_id, book_pk, c.content_type, c.text, c.reading_order, c.page_idx),
            )
            inserted += cur.rowcount
        except sqlite3.Error as e:
            logger.warning("fts5_builder: skip chunk %s: %s", c.chunk_id, e)

    # Update chunk_count
    cur.execute("UPDATE books SET chunk_count = ? WHERE id = ?", (inserted, book_pk))
    conn.commit()
    conn.close()

    logger.info("fts5_builder: inserted %d chunks for %s", inserted, result.book_dir_name)
    return inserted
