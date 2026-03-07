# SQLite FTS5 indexer — full-text search with BM25 ranking.
# Ref: Manning, Intro to IR, Ch11 — Probabilistic retrieval (BM25/Okapi)

from __future__ import annotations

import json
import sqlite3
from threading import RLock
from pathlib import Path

from loguru import logger

from backend.app.models import BookInfo, Chunk

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS books (
    book_key      TEXT PRIMARY KEY,
    book_title    TEXT NOT NULL,
    author        TEXT DEFAULT '',
    total_pages   INTEGER DEFAULT 0,
    total_chunks  INTEGER DEFAULT 0,
    indexed_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id      TEXT PRIMARY KEY,
    book_key      TEXT NOT NULL,
    book_title    TEXT NOT NULL,
    chapter       TEXT DEFAULT '',
    section       TEXT DEFAULT '',
    page_number   INTEGER NOT NULL,
    content_type  TEXT NOT NULL,
    text          TEXT NOT NULL,
    bbox_json     TEXT NOT NULL,
    text_level    INTEGER,
    token_count   INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_book   ON chunks(book_key);
CREATE INDEX IF NOT EXISTS idx_chunks_page   ON chunks(book_key, page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_type   ON chunks(content_type);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    book_title,
    chapter,
    text,
    content='chunks',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- Sync triggers: keep FTS5 in sync with the chunks table
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, chunk_id, book_title, chapter, text)
    VALUES (new.rowid, new.chunk_id, new.book_title, new.chapter, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, chunk_id, book_title, chapter, text)
    VALUES ('delete', old.rowid, old.chunk_id, old.book_title, old.chapter, old.text);
END;
"""


class SQLiteIndexer:
    """Create and query a SQLite FTS5 full-text search index."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = RLock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.commit()

    def index_chunks(self, chunks: list[Chunk], book_key: str, book_title: str) -> int:
        """Insert chunks for a book into the index.

        Skips books that are already indexed (idempotent).

        Returns:
            Number of chunks inserted.
        """
        # Check if already indexed
        with self._lock:
            row = self._conn.execute(
                "SELECT total_chunks FROM books WHERE book_key = ?", (book_key,)
            ).fetchone()
        if row and row["total_chunks"] > 0:
            logger.info(
                "Book {} already indexed ({} chunks), skipping",
                book_key,
                row["total_chunks"],
            )
            return 0

        count = 0
        for chunk in chunks:
            try:
                with self._lock:
                    self._conn.execute(
                        """INSERT OR IGNORE INTO chunks
                           (chunk_id, book_key, book_title, chapter, section,
                            page_number, content_type, text, bbox_json, text_level, token_count)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            chunk.chunk_id,
                            chunk.book_key,
                            chunk.book_title,
                            chunk.chapter,
                            chunk.section,
                            chunk.page_number,
                            chunk.content_type,
                            chunk.text,
                            json.dumps(chunk.bbox),
                            chunk.text_level,
                            chunk.token_count,
                        ),
                    )
                count += 1
            except sqlite3.IntegrityError:
                pass

        # Upsert books metadata
        max_page = max((c.page_number for c in chunks), default=0) if chunks else 0
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO books (book_key, book_title, total_pages, total_chunks)
                   VALUES (?, ?, ?, ?)""",
                (book_key, book_title, max_page + 1, count),
            )
            self._conn.commit()
        logger.info("Indexed {} chunks for {}", count, book_key)
        return count

    def search(
        self,
        query: str,
        top_k: int = 10,
        book_filter: list[str] | None = None,
        content_type_filter: list[str] | None = None,
    ) -> list[Chunk]:
        """BM25-ranked full-text search.

        Args:
            query: User question (will be tokenized by FTS5).
            top_k: Max results to return.
            book_filter: Optional list of book_keys to restrict search.
            content_type_filter: Optional content types to include.

        Returns:
            Chunks ranked by BM25 relevance.
        """
        # Build FTS5 MATCH query — escape special chars
        safe_query = query.replace('"', '""')

        sql = """
            SELECT c.*, bm25(chunks_fts) AS rank
            FROM chunks_fts f
            JOIN chunks c ON c.chunk_id = f.chunk_id
            WHERE chunks_fts MATCH ?
        """
        params: list = [f'"{safe_query}"']

        if book_filter:
            placeholders = ",".join("?" * len(book_filter))
            sql += f" AND c.book_key IN ({placeholders})"
            params.extend(book_filter)

        if content_type_filter:
            placeholders = ",".join("?" * len(content_type_filter))
            sql += f" AND c.content_type IN ({placeholders})"
            params.extend(content_type_filter)

        sql += " ORDER BY rank LIMIT ?"
        params.append(top_k)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_chunks_by_pages(
        self,
        book_key: str,
        page_start: int,
        page_end: int,
    ) -> list[Chunk]:
        """Retrieve chunks within a page range (for PageIndex retrieval)."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM chunks
                   WHERE book_key = ? AND page_number BETWEEN ? AND ?
                   ORDER BY page_number""",
                (book_key, page_start, page_end),
            ).fetchall()
        return [self._row_to_chunk(r) for r in rows]

    def get_books(self) -> list[BookInfo]:
        """List all indexed books."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM books ORDER BY book_title"
            ).fetchall()
        return [
            BookInfo(
                book_key=r["book_key"],
                book_title=r["book_title"],
                author=r["author"] or "",
                total_pages=r["total_pages"],
                total_chunks=r["total_chunks"],
            )
            for r in rows
        ]

    def total_chunks(self) -> int:
        """Count total indexed chunks."""
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS cnt FROM chunks").fetchone()
        return row["cnt"] if row else 0

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._conn.close()

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> Chunk:
        """Convert a database row to a Chunk object."""
        return Chunk(
            chunk_id=row["chunk_id"],
            book_key=row["book_key"],
            book_title=row["book_title"],
            chapter=row["chapter"],
            section=row["section"],
            page_number=row["page_number"],
            content_type=row["content_type"],
            text=row["text"],
            bbox=json.loads(row["bbox_json"]),
            text_level=row["text_level"],
            token_count=row["token_count"] or 0,
        )
