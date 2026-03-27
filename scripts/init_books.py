"""
Unified book initialization pipeline.

Orchestrates all stages of book ingestion in a single command:
  1. ingest   — Parse MinerU output → SQLite (books, chapters, pages, chunks, FTS)
  2. toc      — Extract PDF bookmarks → toc_entries table
  3. vectors  — Embed chunks → ChromaDB (GPU-accelerated)
  4. sync     — Push books/chapters → Payload CMS via REST API

Usage:
    # Full pipeline (all stages):
    .venv/Scripts/python scripts/init_books.py

    # Single book, all stages:
    .venv/Scripts/python scripts/init_books.py --book ramalho_fluent_python

    # Specific stages only:
    .venv/Scripts/python scripts/init_books.py --stages ingest,toc
    .venv/Scripts/python scripts/init_books.py --stages vectors
    .venv/Scripts/python scripts/init_books.py --stages sync --dry-run

    # Skip vectors (fast rebuild for schema/data changes):
    .venv/Scripts/python scripts/init_books.py --skip-vectors

    # List available books:
    .venv/Scripts/python scripts/init_books.py --list
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "textbook_rag.sqlite3"
MINERU_DIR = BASE_DIR / "data" / "mineru_output"
CHROMA_DIR = BASE_DIR / "data" / "chroma_persist"

CATEGORIES = ["textbooks", "ecdev", "real_estate"]

# ── Stage definitions ────────────────────────────────────────────────────────

ALL_STAGES = ["ingest", "toc", "vectors", "sync"]


def stage_ingest(book: str | None = None, nuke: bool = True) -> dict:
    """Stage 1: Parse MinerU output → SQLite.
    
    Imports rebuild_db logic and runs ingestion.
    """
    print("\n" + "=" * 60)
    print("📥 STAGE 1: Ingest (MinerU → SQLite)")
    print("=" * 60)

    from rebuild_db import (
        SCHEMA_SQL, DB_PATH as _DB_PATH, MINERU_DIR as _MINERU_DIR,
        ingest_book,
    )

    if nuke and not book:
        # Full rebuild: nuke existing DB
        print("💣 Nuking existing SQLite DB...")
        if _DB_PATH.exists():
            _DB_PATH.unlink()
            print(f"  Deleted {_DB_PATH}")
        for suffix in ("-wal", "-shm"):
            p = _DB_PATH.parent / (_DB_PATH.name + suffix)
            if p.exists():
                p.unlink()
    elif book:
        # Single book: delete only that book's data
        if _DB_PATH.exists():
            conn = sqlite3.connect(str(_DB_PATH))
            conn.execute("PRAGMA foreign_keys = ON")
            row = conn.execute(
                "SELECT id FROM books WHERE book_id = ?", (book,)
            ).fetchone()
            if row:
                book_pk = row[0]
                # Delete in dependency order
                conn.execute("DELETE FROM source_locators WHERE chunk_id IN (SELECT id FROM chunks WHERE book_id = ?)", (book_pk,))
                conn.execute("DELETE FROM chunk_fts WHERE rowid IN (SELECT id FROM chunks WHERE book_id = ?)", (book_pk,))
                conn.execute("DELETE FROM chunks WHERE book_id = ?", (book_pk,))
                conn.execute("DELETE FROM toc_entries WHERE book_id = ?", (book_pk,))
                conn.execute("DELETE FROM chapters WHERE book_id = ?", (book_pk,))
                conn.execute("DELETE FROM pages WHERE book_id = ?", (book_pk,))
                conn.execute("DELETE FROM book_assets WHERE book_id = ?", (book_pk,))
                conn.execute("DELETE FROM books WHERE id = ?", (book_pk,))
                conn.commit()
                print(f"  🗑  Cleared existing data for {book}")
            conn.close()

    # Create schema (idempotent)
    print("\n📐 Creating schema...")
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    print("  ✅ Schema ready")

    # Scan and ingest
    print("\n📚 Ingesting books...")
    stats = {"books": 0, "pages": 0, "chapters": 0, "chunks": 0}

    for category in CATEGORIES:
        cat_dir = _MINERU_DIR / category
        if not cat_dir.is_dir():
            continue

        for book_dir in sorted(cat_dir.iterdir()):
            if not book_dir.is_dir() or book_dir.name.endswith(".processing"):
                continue
            if book and book_dir.name != book:
                continue

            result = ingest_book(conn, book_dir.name, category, None)
            if result["status"] == "ok":
                stats["books"] += 1
                stats["pages"] += result["pages"]
                stats["chapters"] += result["chapters"]
                stats["chunks"] += result["chunks"]
                print(f"  ✓ [{category}] {book_dir.name}: "
                      f"{result['pages']} pg, {result['chapters']} ch, "
                      f"{result['chunks']} chunks")
            else:
                print(f"  ✗ [{category}] {book_dir.name}: {result.get('reason')}")

    conn.close()

    size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
    print(f"\n  📊 {stats['books']} books, {stats['pages']} pages, "
          f"{stats['chapters']} chapters, {stats['chunks']} chunks "
          f"({size_kb:.0f} KB)")
    return stats


def stage_toc(book: str | None = None) -> dict:
    """Stage 2: Extract PDF bookmarks → toc_entries."""
    print("\n" + "=" * 60)
    print("📑 STAGE 2: TOC (PDF bookmarks → toc_entries)")
    print("=" * 60)

    from rebuild_toc import (
        ensure_schema, extract_toc_from_pdf,
        clear_toc, insert_toc_entries,
    )

    if not DB_PATH.exists():
        print("  ❌ Database not found — run ingest stage first")
        return {"processed": 0, "entries": 0}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)

    # Query books with source_pdf assets
    query = """
        SELECT b.id, b.book_id, ba.path AS pdf_rel
        FROM books b
        JOIN book_assets ba ON ba.book_id = b.id AND ba.asset_kind = 'source_pdf'
    """
    if book:
        query += " WHERE b.book_id = ?"
        books = conn.execute(query, (book,)).fetchall()
    else:
        query += " ORDER BY b.book_id"
        books = conn.execute(query).fetchall()

    stats = {"processed": 0, "skipped": 0, "entries": 0}

    for row in books:
        pdf_path = BASE_DIR / row["pdf_rel"]
        if not pdf_path.exists():
            print(f"  ⚠ {row['book_id']}: PDF not found")
            stats["skipped"] += 1
            continue

        entries = extract_toc_from_pdf(pdf_path)
        if not entries:
            print(f"  ⚠ {row['book_id']}: no bookmarks")
            clear_toc(conn, row["id"])
            stats["skipped"] += 1
            continue

        clear_toc(conn, row["id"])
        count = insert_toc_entries(conn, row["id"], entries)
        stats["processed"] += 1
        stats["entries"] += count
        print(f"  ✓ {row['book_id']}: {count} toc entries")

    conn.close()
    print(f"\n  📊 {stats['processed']} books, {stats['entries']} TOC entries")
    return stats


def stage_vectors(batch_size: int = 256, model: str = "all-MiniLM-L6-v2") -> dict:
    """Stage 3: Embed chunks → ChromaDB (GPU-accelerated)."""
    print("\n" + "=" * 60)
    print("🔮 STAGE 3: Vectors (chunks → ChromaDB)")
    print("=" * 60)

    from build_vectors import check_gpu, load_chunks_from_sqlite, build_chroma_gpu

    device = check_gpu()
    chunks = load_chunks_from_sqlite()
    print(f"  {len(chunks):,} chunks loaded")

    build_chroma_gpu(chunks, model, device, batch_size)
    return {"chunks": len(chunks), "device": device}


def stage_sync(
    book: str | None = None,
    dry_run: bool = False,
    email: str = "402707192@qq.com",
    password: str = "123123",
    url: str = "http://localhost:3000",
) -> dict:
    """Stage 4: Push books/chapters → Payload CMS."""
    print("\n" + "=" * 60)
    print("📤 STAGE 4: Sync (SQLite → Payload CMS)")
    print("=" * 60)

    from sync_to_payload import (
        PayloadClient, read_engine_books, read_engine_chapters, detect_category,
    )

    if not DB_PATH.exists():
        print("  ❌ Database not found — run ingest stage first")
        return {"books_created": 0}

    conn = sqlite3.connect(str(DB_PATH))
    books = read_engine_books(conn, book)
    if not books:
        print("  ❌ No books found")
        conn.close()
        return {"books_created": 0}

    print(f"  📚 {len(books)} books to sync")

    if dry_run:
        print("\n  🔍 DRY RUN:")
        for b in books:
            cat = detect_category(b["book_id"])
            print(f"    [{cat}] {b['book_id']}: {b['title']} "
                  f"({b['chunk_count']} chunks)")
        conn.close()
        return {"books": len(books), "dry_run": True}

    # Login and sync
    client = PayloadClient(url)
    client.login(email, password)

    existing = client.find("books", limit=500)
    existing_map = {d.get("engineBookId"): d for d in existing if d.get("engineBookId")}
    print(f"  📋 {len(existing_map)} books already in Payload")

    stats = {"books_created": 0, "books_skipped": 0,
             "chapters_created": 0, "chapters_skipped": 0}
    book_id_map: dict[str, int] = {}

    for i, b in enumerate(books, 1):
        eid = b["book_id"]
        cat = detect_category(eid)

        if eid in existing_map:
            book_id_map[eid] = existing_map[eid]["id"]
            stats["books_skipped"] += 1
            print(f"  ⏭  [{i}/{len(books)}] {eid} (exists)")
            continue

        doc = client.create("books", {
            "engineBookId": eid,
            "title": b["title"],
            "authors": b["authors"],
            "category": cat,
            "status": "indexed",
            "chunkCount": b["chunk_count"],
            "pipeline": {k: "done" for k in ["chunked", "stored", "vector", "fts", "toc"]},
            "metadata": {
                "pageCount": b["page_count"],
                "chapterCount": b["chapter_count"],
                "source": "init_pipeline",
            },
        })

        if doc.get("_skipped"):
            stats["books_skipped"] += 1
        else:
            book_id_map[eid] = doc["id"]
            stats["books_created"] += 1
            print(f"  ✅ [{i}/{len(books)}] {eid} → ID {doc['id']}")

    # Sync chapters
    existing_chapters = client.find("chapters", limit=5000)
    existing_ch_keys = set()
    for ch in existing_chapters:
        br = ch.get("book")
        bid = br if isinstance(br, int) else (br.get("id") if isinstance(br, dict) else None)
        if bid:
            existing_ch_keys.add(f"{bid}_{ch.get('chapterKey')}")

    for eid, pid in book_id_map.items():
        chapters = read_engine_chapters(conn, eid)
        for ch in chapters:
            key = f"{pid}_{ch['chapter_key']}"
            if key in existing_ch_keys:
                stats["chapters_skipped"] += 1
                continue
            doc = client.create("chapters", {
                "book": pid,
                "chapterKey": ch["chapter_key"],
                "title": ch["title"],
                "contentType": ch["content_type"],
            })
            if not doc.get("_skipped"):
                stats["chapters_created"] += 1
            else:
                stats["chapters_skipped"] += 1

    conn.close()
    print(f"\n  📊 Books: {stats['books_created']} created, {stats['books_skipped']} skipped")
    print(f"     Chapters: {stats['chapters_created']} created, {stats['chapters_skipped']} skipped")
    return stats


def list_available_books():
    """Show all books available in mineru_output."""
    print("\n📚 Available books in mineru_output:\n")
    total = 0
    for category in CATEGORIES:
        cat_dir = MINERU_DIR / category
        if not cat_dir.is_dir():
            continue
        books = sorted(d.name for d in cat_dir.iterdir()
                       if d.is_dir() and not d.name.endswith(".processing"))
        if books:
            print(f"  [{category}] ({len(books)} books)")
            for b in books:
                print(f"    • {b}")
            total += len(books)
            print()
    print(f"  Total: {total} books")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified book initialization pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stages (in order):
  ingest   Parse MinerU output → SQLite
  toc      Extract PDF bookmarks → toc_entries
  vectors  Embed chunks → ChromaDB (GPU)
  sync     Push to Payload CMS

Examples:
  %(prog)s                           # Full pipeline
  %(prog)s --book cormen_CLRS        # Single book
  %(prog)s --stages ingest,toc       # Specific stages
  %(prog)s --skip-vectors            # Skip GPU embedding
  %(prog)s --list                    # List available books
        """,
    )
    parser.add_argument("--book", type=str, default=None,
                        help="Process only a specific book")
    parser.add_argument("--stages", type=str, default=None,
                        help="Comma-separated stages to run (default: all)")
    parser.add_argument("--skip-vectors", action="store_true",
                        help="Skip the vectors stage (fast rebuild)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be synced without changes")
    parser.add_argument("--batch-size", type=int, default=256,
                        help="Vector embedding batch size")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2",
                        help="SentenceTransformer model name")
    parser.add_argument("--list", action="store_true",
                        help="List all available books and exit")
    parser.add_argument("--no-nuke", action="store_true",
                        help="Don't nuke the DB before ingest (incremental)")
    args = parser.parse_args()

    if args.list:
        list_available_books()
        return

    # Determine which stages to run
    if args.stages:
        stages = [s.strip() for s in args.stages.split(",")]
        invalid = [s for s in stages if s not in ALL_STAGES]
        if invalid:
            print(f"❌ Unknown stages: {invalid}")
            print(f"   Valid: {ALL_STAGES}")
            sys.exit(1)
    else:
        stages = list(ALL_STAGES)
        if args.skip_vectors:
            stages.remove("vectors")

    print("🚀 Textbook RAG Initialization Pipeline")
    print("=" * 60)
    print(f"  Stages:  {' → '.join(stages)}")
    if args.book:
        print(f"  Book:    {args.book}")
    print(f"  DB:      {DB_PATH}")
    print(f"  Chroma:  {CHROMA_DIR}")

    t_total = time.time()
    results: dict[str, dict] = {}

    # Run stages in order
    if "ingest" in stages:
        t0 = time.time()
        results["ingest"] = stage_ingest(args.book, nuke=not args.no_nuke)
        print(f"  ⏱  Ingest: {time.time() - t0:.1f}s")

    if "toc" in stages:
        t0 = time.time()
        results["toc"] = stage_toc(args.book)
        print(f"  ⏱  TOC: {time.time() - t0:.1f}s")

    if "vectors" in stages:
        t0 = time.time()
        results["vectors"] = stage_vectors(args.batch_size, args.model)
        print(f"  ⏱  Vectors: {time.time() - t0:.1f}s")

    if "sync" in stages:
        t0 = time.time()
        results["sync"] = stage_sync(args.book, args.dry_run)
        print(f"  ⏱  Sync: {time.time() - t0:.1f}s")

    # Final summary
    total_time = time.time() - t_total
    print("\n" + "=" * 60)
    print(f"✅ Pipeline complete! ({total_time / 60:.1f} min)")
    for stage_name, stage_result in results.items():
        print(f"   {stage_name}: {stage_result}")
    print("=" * 60)


if __name__ == "__main__":
    main()
