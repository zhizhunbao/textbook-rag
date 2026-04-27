"""
Patch ChromaDB metadata with chapter_key for all books.

Problem: ChromaDB chunks were built without chapter_key metadata,
so the question generator cannot filter by chapter.

Solution: For each book, extract TOC entries (pdf_page → title),
build page ranges, then update each chunk's metadata with the
matching chapter title.

Usage:
    uv run python scripts/patch_chroma_chapter_keys.py
    uv run python scripts/patch_chroma_chapter_keys.py --book oreb_market_update_july25
    uv run python scripts/patch_chroma_chapter_keys.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure engine_v2 is importable
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import chromadb

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    DATA_DIR,
    MINERU_OUTPUT_DIR,
)
from engine_v2.toc import extract_toc, find_pdf_for_book, load_content_list

# Category directories under mineru_output/
CATEGORIES = ["textbooks", "ecdev", "real_estate"]

# Raw PDF source directories (for bookmark-based TOC)
RAW_PDF_DIRS = [
    DATA_DIR / "raw_pdfs" / "textbooks",
    DATA_DIR / "raw_pdfs" / "ecdev",
    DATA_DIR / "raw_pdfs" / "real_estate",
    DATA_DIR / "raw_pdfs" / "uploads",
]


def discover_book_ids() -> list[str]:
    """Scan mineru_output/ for all book IDs."""
    book_ids: list[str] = []
    for category in CATEGORIES:
        cat_dir = MINERU_OUTPUT_DIR / category
        if not cat_dir.is_dir():
            continue
        for book_dir in sorted(cat_dir.iterdir()):
            if not book_dir.is_dir():
                continue
            book_id = book_dir.name
            auto_dir = book_dir / book_id / "auto"
            content_list_path = auto_dir / f"{book_id}_content_list.json"
            if content_list_path.exists():
                book_ids.append(book_id)
    return book_ids


def get_auto_dir(book_id: str) -> Path | None:
    """Get the MinerU auto/ directory for a book."""
    for category in CATEGORIES:
        auto_dir = MINERU_OUTPUT_DIR / category / book_id / book_id / "auto"
        if auto_dir.is_dir():
            return auto_dir
    return None


def build_chapter_page_ranges(toc_entries: list[dict]) -> list[tuple[str, int, int]]:
    """Build (chapter_label, start_page_0idx, end_page_0idx) ranges from TOC.

    TOC entries have pdf_page (1-indexed).
    ChromaDB chunks have page_idx (0-indexed).
    We convert TOC pages to 0-indexed for matching.

    Deduplication: when multiple entries share the same page, only the
    first one is kept — each page belongs to exactly one chapter.

    Returns:
        List of (chapter_label, start_page, end_page) tuples.
        end_page is exclusive (i.e., range = [start, end)).
    """
    if not toc_entries:
        return []

    # Only use top-level entries (level 1) for chapter assignment
    top_entries = [e for e in toc_entries if e.get("level", 1) == 1]
    if not top_entries:
        top_entries = toc_entries

    # Deduplicate: keep first entry per unique page
    seen_pages: set[int] = set()
    unique_entries: list[dict] = []
    for entry in top_entries:
        page = entry["pdf_page"]
        if page not in seen_pages:
            seen_pages.add(page)
            unique_entries.append(entry)

    ranges: list[tuple[str, int, int]] = []
    for i, entry in enumerate(unique_entries):
        label = entry.get("number", "")
        title = entry.get("title", "")
        chapter_label = f"{label} {title}".strip() if label else title

        start_page = entry["pdf_page"] - 1  # 1-indexed → 0-indexed

        if i + 1 < len(unique_entries):
            end_page = unique_entries[i + 1]["pdf_page"] - 1
        else:
            end_page = 999999

        ranges.append((chapter_label, start_page, end_page))

    return ranges


def assign_chapter_label(page_idx: int, ranges: list[tuple[str, int, int]]) -> str | None:
    """Match a page_idx (0-indexed) to a chapter label."""
    for label, start, end in ranges:
        if start <= page_idx < end:
            return label
    return None


def patch_book(
    collection: chromadb.Collection,
    book_id: str,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """Patch chapter_key metadata for all chunks of one book.

    Returns stats: { total, patched, no_chapter, already_set }
    """
    auto_dir = get_auto_dir(book_id)
    if not auto_dir:
        return {"status": "skip", "reason": "no auto dir"}

    # Load content_list and extract TOC
    content_list = load_content_list(auto_dir, book_id)
    if not content_list:
        return {"status": "skip", "reason": "no content_list"}

    pdf_path = find_pdf_for_book(book_id, MINERU_OUTPUT_DIR, RAW_PDF_DIRS)
    toc = extract_toc(content_list, pdf_path=pdf_path)
    if not toc:
        return {"status": "skip", "reason": "no TOC entries"}

    # Build page → chapter ranges
    ranges = build_chapter_page_ranges(toc)
    if not ranges:
        return {"status": "skip", "reason": "no chapter ranges"}

    # Get all chunks for this book from ChromaDB
    results = collection.get(
        where={"book_id": book_id},
        limit=50000,
        include=["metadatas"],
    )

    total = len(results["ids"])
    if total == 0:
        return {"status": "skip", "reason": "no chunks in ChromaDB"}

    # Build update lists
    update_ids: list[str] = []
    update_metadatas: list[dict] = []
    already_set = 0
    no_chapter = 0

    for idx, (chunk_id, meta) in enumerate(zip(results["ids"], results["metadatas"])):
        # Skip if already has chapter_key (unless --force)
        if meta.get("chapter_key") and not force:
            already_set += 1
            continue

        page_idx = meta.get("page_idx", 0)
        chapter_label = assign_chapter_label(page_idx, ranges)

        if not chapter_label:
            no_chapter += 1
            continue

        # Build updated metadata (keep all existing fields)
        new_meta = dict(meta)
        new_meta["chapter_key"] = chapter_label
        update_ids.append(chunk_id)
        update_metadatas.append(new_meta)

    patched = len(update_ids)

    if not dry_run and update_ids:
        # ChromaDB update in batches (max 5000 per call)
        batch_size = 5000
        for i in range(0, len(update_ids), batch_size):
            batch_ids = update_ids[i : i + batch_size]
            batch_metas = update_metadatas[i : i + batch_size]
            collection.update(ids=batch_ids, metadatas=batch_metas)

    return {
        "status": "ok",
        "total": total,
        "patched": patched,
        "already_set": already_set,
        "no_chapter": no_chapter,
        "toc_entries": len(toc),
        "chapter_ranges": len(ranges),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Patch ChromaDB chunks with chapter_key metadata"
    )
    parser.add_argument(
        "--book", type=str, default=None,
        help="Only patch a specific book (by book_id)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be patched without writing",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing chapter_key values (re-patch all chunks)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Patch ChromaDB: Add chapter_key to chunk metadata")
    if args.dry_run:
        print("  ⚠  DRY RUN — no writes")
    print("=" * 60)

    # Open ChromaDB
    print(f"\n📦 Opening ChromaDB at {CHROMA_PERSIST_DIR}...")
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(name=CHROMA_COLLECTION)
    print(f"  Collection '{CHROMA_COLLECTION}': {collection.count():,} vectors")

    # Discover books
    if args.book:
        book_ids = [args.book]
    else:
        book_ids = discover_book_ids()
    print(f"\n📚 Processing {len(book_ids)} books...\n")

    # Patch each book
    t0 = time.time()
    total_patched = 0
    total_skipped = 0

    for book_id in book_ids:
        result = patch_book(collection, book_id, dry_run=args.dry_run, force=args.force)
        if result["status"] == "ok":
            total_patched += result["patched"]
            symbol = "🔧" if result["patched"] > 0 else "✅"
            print(
                f"  {symbol} {book_id}: "
                f"{result['patched']}/{result['total']} patched "
                f"({result['already_set']} already set, "
                f"{result['no_chapter']} no chapter, "
                f"{result['toc_entries']} TOC entries)"
            )
        else:
            total_skipped += 1
            print(f"  ⏭  {book_id}: {result.get('reason', 'skipped')}")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"✅ Done in {elapsed:.1f}s")
    print(f"   🔧 {total_patched:,} chunks patched")
    print(f"   ⏭  {total_skipped} books skipped")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
