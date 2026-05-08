"""Batch re-ingest ecdev + real_estate books with LaTeX-cleaned text.

Calls ingest_book() directly (no HTTP — runs in-process).
Skips MinerU parse (data already exists), only does:
    Reader (with LaTeX cleanup) → Embedding → ChromaDB upsert → Payload sync

Usage:
    uv run python scripts/batch_reingest_ecdev.py
"""

from __future__ import annotations

import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Initialize LlamaIndex Settings before importing pipeline
from engine_v2.settings import init_settings
init_settings()

from engine_v2.ingestion.pipeline import ingest_book
from engine_v2.settings import MINERU_OUTPUT_DIR

import httpx

PAYLOAD_URL = "http://localhost:3001"
API_KEY = "BHTdK273zAnTBPDayNmb97OLNsavV8yyGWqhhtkM8Kw"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}


def get_payload_books(category_filter: str) -> list[dict]:
    """Fetch books from Payload that match a category."""
    resp = httpx.get(
        f"{PAYLOAD_URL}/api/books",
        params={"limit": "100", "depth": "0"},
        headers=headers,
        timeout=30.0,
    )
    if not resp.is_success:
        print(f"[ERROR] Failed to fetch books: {resp.status_code}")
        return []
    
    docs = resp.json().get("docs", [])
    return [
        d for d in docs
        if d.get("category") == category_filter
        or (d.get("engineBookId") or "").startswith(
            "oreb_" if category_filter == "ecdev" else "economic_"
        )
    ]


def main():
    print("=" * 60)
    print("Batch Re-Ingest: ecdev + real_estate (LaTeX cleanup)")
    print("=" * 60)

    # Discover all ecdev/real_estate books in Payload
    resp = httpx.get(
        f"{PAYLOAD_URL}/api/books",
        params={"limit": "100", "depth": "0"},
        headers=headers,
        timeout=30.0,
    )
    if not resp.is_success:
        print(f"[ERROR] Failed to fetch books: {resp.status_code}")
        sys.exit(1)

    docs = resp.json().get("docs", [])
    target_books = [
        d for d in docs
        if d.get("category") == "ecdev"
        or (d.get("engineBookId") or "").startswith("oreb_")
        or (d.get("engineBookId") or "").startswith("economic_")
    ]

    print(f"\nFound {len(target_books)} books to re-ingest:")
    for d in target_books:
        eid = d.get("engineBookId", "?")
        print(f"  ID={d['id']:>3}  {eid}")

    # Determine category for each book's MinerU output
    total = len(target_books)
    success = 0
    errors = []

    for i, book in enumerate(target_books, 1):
        eid = book.get("engineBookId", "")
        book_id = book["id"]

        # Determine the MinerU category directory
        if eid.startswith("oreb_"):
            category = "real_estate"
        elif eid.startswith("economic_"):
            category = "ecdev"
        else:
            category = book.get("category", "ecdev")

        # Verify MinerU output exists
        auto_dir = MINERU_OUTPUT_DIR / category / eid / eid / "auto"
        if not auto_dir.exists():
            # Try other categories
            for cat_try in ["ecdev", "real_estate", "textbook"]:
                alt = MINERU_OUTPUT_DIR / cat_try / eid / eid / "auto"
                if alt.exists():
                    category = cat_try
                    auto_dir = alt
                    break

        if not auto_dir.exists():
            print(f"\n[{i}/{total}] SKIP {eid} — no MinerU output at {auto_dir}")
            continue

        print(f"\n[{i}/{total}] Ingesting {eid} (category={category})...")
        t0 = time.time()

        try:
            result = ingest_book(
                book_id=book_id,
                book_dir_name=eid,
                category=category,
            )
            elapsed = time.time() - t0
            chunks = result.get("chunk_count", 0)
            print(f"  ✓ Done: {chunks} chunks in {elapsed:.1f}s")
            success += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ✗ Error after {elapsed:.1f}s: {e}")
            errors.append(eid)

    # Summary
    print("\n" + "=" * 60)
    print("RE-INGEST COMPLETE")
    print("=" * 60)
    print(f"  Success: {success}/{total}")
    if errors:
        print(f"  Errors: {', '.join(errors)}")
    print("\nRestart engine to apply resolver.py changes, then test chat.")


if __name__ == "__main__":
    main()
