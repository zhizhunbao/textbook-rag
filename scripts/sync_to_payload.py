"""
Sync engine SQLite data → Payload CMS via REST API.

Reads books + chapters from data/textbook_rag.sqlite3 and creates
corresponding documents in Payload CMS (data/payload.db).

Usage:
    uv run python scripts/sync_to_payload.py
    uv run python scripts/sync_to_payload.py --book ramalho_fluent_python
    uv run python scripts/sync_to_payload.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DB = BASE_DIR / "data" / "textbook_rag.sqlite3"

PAYLOAD_URL = "http://localhost:3000"
# Default credentials — override via args
DEFAULT_EMAIL = "402707192@qq.com"
DEFAULT_PASSWORD = "123123"


# ── Payload API helpers ──────────────────────────────────────────────────────

class PayloadClient:
    """Thin wrapper around Payload REST API."""

    def __init__(self, base_url: str, token: str | None = None):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"JWT {token}"

    def login(self, email: str, password: str) -> str:
        """Login and store JWT token. Returns the token."""
        resp = self.session.post(f"{self.base}/api/users/login", json={
            "email": email,
            "password": password,
        })
        resp.raise_for_status()
        token = resp.json().get("token", "")
        self.session.headers["Authorization"] = f"JWT {token}"
        print(f"  ✅ Logged in as {email}")
        return token

    def find(self, collection: str, where: dict | None = None, limit: int = 200) -> list[dict]:
        """Find documents in a collection."""
        params: dict = {"limit": limit}
        if where:
            for key, value in where.items():
                params[f"where[{key}][equals]"] = value
        resp = self.session.get(f"{self.base}/api/{collection}", params=params)
        resp.raise_for_status()
        return resp.json().get("docs", [])

    def create(self, collection: str, data: dict) -> dict:
        """Create a document."""
        resp = self.session.post(f"{self.base}/api/{collection}", json=data)
        if resp.status_code == 400:
            errors = resp.json().get("errors", [])
            # If unique constraint violation, it already exists
            for err in errors:
                if "unique" in str(err).lower() or "duplicate" in str(err).lower():
                    return {"_skipped": True, "reason": "duplicate"}
            raise Exception(f"Create failed: {resp.text}")
        resp.raise_for_status()
        return resp.json().get("doc", resp.json())

    def update(self, collection: str, doc_id: int, data: dict) -> dict:
        """Update a document."""
        resp = self.session.patch(f"{self.base}/api/{collection}/{doc_id}", json=data)
        resp.raise_for_status()
        return resp.json().get("doc", resp.json())


# ── Engine DB readers ────────────────────────────────────────────────────────

def read_engine_books(conn: sqlite3.Connection, book_filter: str | None = None) -> list[dict]:
    """Read books from engine SQLite."""
    query = """
        SELECT book_id, title, authors, page_count, chapter_count, chunk_count
        FROM books
    """
    if book_filter:
        query += " WHERE book_id = ?"
        rows = conn.execute(query, (book_filter,)).fetchall()
    else:
        rows = conn.execute(query).fetchall()

    return [
        {
            "book_id": r[0],
            "title": r[1],
            "authors": r[2],
            "page_count": r[3],
            "chapter_count": r[4],
            "chunk_count": r[5],
        }
        for r in rows
    ]


def read_engine_chapters(conn: sqlite3.Connection, engine_book_id: str) -> list[dict]:
    """Read chapters for a specific book from engine SQLite."""
    query = """
        SELECT c.chapter_key, c.title, c.content_type
        FROM chapters c
        JOIN books b ON c.book_id = b.id
        WHERE b.book_id = ?
        ORDER BY c.id
    """
    rows = conn.execute(query, (engine_book_id,)).fetchall()
    return [
        {"chapter_key": r[0], "title": r[1], "content_type": r[2]}
        for r in rows
    ]


def detect_category(book_id: str) -> str:
    """Detect book category from book_id naming convention."""
    if book_id.startswith("ed_update"):
        return "ecdev"
    if book_id.startswith("oreb"):
        return "real_estate"
    return "textbook"


# ── Main sync logic ──────────────────────────────────────────────────────────

def sync(args: argparse.Namespace):
    # Validate engine DB exists
    if not ENGINE_DB.exists():
        print(f"❌ Engine DB not found: {ENGINE_DB}")
        sys.exit(1)

    # Connect to engine SQLite
    conn = sqlite3.connect(str(ENGINE_DB))
    conn.row_factory = None  # Use tuples

    # Read books
    books = read_engine_books(conn, args.book)
    if not books:
        print("❌ No books found in engine DB")
        sys.exit(1)

    print(f"\n📚 Found {len(books)} books in engine DB")

    if args.dry_run:
        print("\n🔍 DRY RUN — no changes will be made\n")
        for b in books:
            chapters = read_engine_chapters(conn, b["book_id"])
            cat = detect_category(b["book_id"])
            print(f"  📖 [{cat}] {b['book_id']}: {b['title']}")
            print(f"     {b['page_count']} pages, {b['chapter_count']} chapters, {b['chunk_count']} chunks")
            if chapters:
                print(f"     Chapters: {', '.join(c['chapter_key'] for c in chapters[:5])}", end="")
                if len(chapters) > 5:
                    print(f" ... +{len(chapters)-5} more", end="")
                print()
        conn.close()
        return

    # Login to Payload
    print("\n🔑 Logging in to Payload CMS...")
    client = PayloadClient(PAYLOAD_URL)
    client.login(args.email, args.password)

    # Get existing books to avoid duplicates
    existing = client.find("books", limit=500)
    existing_by_engine_id: dict[str, dict] = {}
    for doc in existing:
        eid = doc.get("engineBookId")
        if eid:
            existing_by_engine_id[eid] = doc
    print(f"  📋 {len(existing_by_engine_id)} books already in Payload")

    # Sync books
    stats = {"books_created": 0, "books_skipped": 0, "chapters_created": 0, "chapters_skipped": 0}
    book_id_map: dict[str, int] = {}  # engine_book_id → payload book id

    print(f"\n📤 Syncing {len(books)} books to Payload...\n")

    for i, book in enumerate(books, 1):
        engine_id = book["book_id"]
        category = detect_category(engine_id)

        # Skip if already exists
        if engine_id in existing_by_engine_id:
            payload_doc = existing_by_engine_id[engine_id]
            book_id_map[engine_id] = payload_doc["id"]
            stats["books_skipped"] += 1
            print(f"  ⏭  [{i}/{len(books)}] {engine_id} (already exists)")
            continue

        # Create in Payload
        doc = client.create("books", {
            "engineBookId": engine_id,
            "title": book["title"],
            "authors": book["authors"],
            "category": category,
            "status": "indexed",
            "chunkCount": book["chunk_count"],
            "metadata": {
                "pageCount": book["page_count"],
                "chapterCount": book["chapter_count"],
                "source": "engine_sync",
            },
        })

        if doc.get("_skipped"):
            stats["books_skipped"] += 1
            print(f"  ⏭  [{i}/{len(books)}] {engine_id} (duplicate)")
            continue

        book_id_map[engine_id] = doc["id"]
        stats["books_created"] += 1
        print(f"  ✅ [{i}/{len(books)}] {engine_id} → Payload ID {doc['id']}")

    # Sync chapters
    print(f"\n📤 Syncing chapters...")

    # Get existing chapters
    existing_chapters = client.find("chapters", limit=5000)
    existing_ch_keys: set[str] = set()
    for ch in existing_chapters:
        book_ref = ch.get("book")
        book_id_val = book_ref if isinstance(book_ref, int) else (book_ref.get("id") if isinstance(book_ref, dict) else None)
        if book_id_val:
            existing_ch_keys.add(f"{book_id_val}_{ch.get('chapterKey')}")

    for engine_id, payload_book_id in book_id_map.items():
        chapters = read_engine_chapters(conn, engine_id)
        if not chapters:
            continue

        created = 0
        for ch in chapters:
            ch_key = f"{payload_book_id}_{ch['chapter_key']}"
            if ch_key in existing_ch_keys:
                stats["chapters_skipped"] += 1
                continue

            doc = client.create("chapters", {
                "book": payload_book_id,
                "chapterKey": ch["chapter_key"],
                "title": ch["title"],
                "contentType": ch["content_type"],
            })

            if not doc.get("_skipped"):
                created += 1
                stats["chapters_created"] += 1
            else:
                stats["chapters_skipped"] += 1

        if created:
            print(f"  ✅ {engine_id}: {created} chapters created")

    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Sync complete!")
    print(f"   📖 Books:    {stats['books_created']} created, {stats['books_skipped']} skipped")
    print(f"   📑 Chapters: {stats['chapters_created']} created, {stats['chapters_skipped']} skipped")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Sync engine SQLite → Payload CMS")
    parser.add_argument("--book", type=str, default=None,
                        help="Sync only a specific book (engine book_id)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be synced without making changes")
    parser.add_argument("--email", type=str, default=DEFAULT_EMAIL,
                        help="Payload admin email")
    parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD,
                        help="Payload admin password")
    parser.add_argument("--url", type=str, default=PAYLOAD_URL,
                        help="Payload server URL")
    args = parser.parse_args()

    sync(args)


if __name__ == "__main__":
    main()
