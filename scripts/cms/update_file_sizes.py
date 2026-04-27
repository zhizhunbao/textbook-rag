"""Update file sizes in Payload CMS books from engine data.

Usage:
    python scripts/update_file_sizes.py

Reads pdf_size_bytes from GET /engine/books, then PATCHes each
matching book in Payload CMS to set metadata.fileSize.
"""

import os
import sys
import json
import httpx

# Load .env from project root
from pathlib import Path
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

PAYLOAD_URL = os.getenv("PAYLOAD_URL", "http://localhost:3001")
ENGINE_URL = os.getenv("ENGINE_URL", "http://localhost:8001")
PAYLOAD_API_KEY = os.getenv("PAYLOAD_API_KEY", "dev-api-key-change-me")


def main():
    client = httpx.Client(timeout=120)

    # 1. Get engine books with pdf_size_bytes
    print(f"Fetching engine books from {ENGINE_URL}/engine/books ...")
    resp = client.get(f"{ENGINE_URL}/engine/books")
    resp.raise_for_status()
    engine_books = resp.json()
    print(f"  Found {len(engine_books)} engine books")

    # Build lookup: book_id → pdf_size_bytes
    size_map: dict[str, int] = {}
    for eb in engine_books:
        book_id = eb.get("book_id", "")
        size = eb.get("pdf_size_bytes", 0)
        if book_id and size > 0:
            size_map[book_id] = size

    print(f"  {len(size_map)} books have PDF size data")

    # 2. Get all Payload books
    print(f"\nFetching Payload books from {PAYLOAD_URL}/api/books ...")
    headers = {"Authorization": f"Bearer {PAYLOAD_API_KEY}"}
    resp = client.get(
        f"{PAYLOAD_URL}/api/books",
        params={"limit": 500, "depth": 0},
        headers=headers,
    )
    resp.raise_for_status()
    payload_books = resp.json().get("docs", [])
    print(f"  Found {len(payload_books)} Payload books")

    # 3. Update each book
    updated = 0
    skipped = 0
    for pb in payload_books:
        book_id = pb.get("engineBookId", "")
        payload_id = pb.get("id")
        current_meta = pb.get("metadata") or {}

        # Already has fileSize?
        if isinstance(current_meta, dict) and current_meta.get("fileSize", 0) > 0:
            skipped += 1
            continue

        size = size_map.get(book_id, 0)
        if size <= 0:
            skipped += 1
            continue

        # Merge into existing metadata
        new_meta = {**(current_meta if isinstance(current_meta, dict) else {}), "fileSize": size}

        print(f"  Updating [{payload_id}] {book_id}: {size:,} bytes ({size / 1024 / 1024:.1f} MB)")
        patch_resp = client.patch(
            f"{PAYLOAD_URL}/api/books/{payload_id}",
            json={"metadata": new_meta},
            headers=headers,
        )
        if patch_resp.status_code == 200:
            updated += 1
        else:
            print(f"    ⚠ PATCH failed: {patch_resp.status_code} {patch_resp.text[:200]}")

    print(f"\nDone: {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    main()
