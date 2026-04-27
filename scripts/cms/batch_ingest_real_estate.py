"""Batch ingest real_estate MinerU data → Payload + ChromaDB + BM25.

Workflow:
    1. Call GET /engine/books to discover all real_estate books
    2. Call POST /api/books/sync-engine to create Book records in Payload
    3. For each real_estate book, call POST /engine/ingest to run ingestion
       (MinerU output already exists, so parsing is skipped — only embedding + ChromaDB)
    4. Wait for each pipeline to complete via polling

Usage:
    uv run python scripts/batch_ingest_real_estate.py
"""

from __future__ import annotations

import sys
import time

import httpx

ENGINE_URL = "http://localhost:8001"
PAYLOAD_URL = "http://localhost:3001"

PAYLOAD_ADMIN_EMAIL = "402707192@qq.com"
PAYLOAD_ADMIN_PASSWORD = "123123"


def login_payload() -> str:
    """Login to Payload CMS and return JWT token."""
    resp = httpx.post(
        f"{PAYLOAD_URL}/api/users/login",
        json={"email": PAYLOAD_ADMIN_EMAIL, "password": PAYLOAD_ADMIN_PASSWORD},
        timeout=10.0,
    )
    if not resp.is_success:
        print(f"[ERROR] Payload login failed: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)
    token = resp.json().get("token")
    if not token:
        print("[ERROR] No token in login response")
        sys.exit(1)
    print(f"[OK] Logged into Payload as {PAYLOAD_ADMIN_EMAIL}")
    return token


def get_payload_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"JWT {token}",
    }


def main():
    print("=" * 60)
    print("Batch Ingest: real_estate → ChromaDB + Payload")
    print("=" * 60)

    # Step 1: Discover real_estate books from engine
    print("\n[1/4] Discovering real_estate books from engine...")
    resp = httpx.get(f"{ENGINE_URL}/engine/books", timeout=30.0)
    if not resp.is_success:
        print(f"[ERROR] Engine /books returned {resp.status_code}")
        sys.exit(1)

    all_books = resp.json()
    re_books = [b for b in all_books if b["category"] == "real_estate"]
    print(f"  Found {len(re_books)} real_estate books (of {len(all_books)} total)")
    for b in re_books:
        print(f"    - {b['book_id']} ({b['chunk_count']} items, {b['page_count']} pages)")

    if not re_books:
        print("[ERROR] No real_estate books found. Check data/mineru_output/real_estate/")
        sys.exit(1)

    # Step 2: Sync to Payload (creates Book records if missing)
    print("\n[2/4] Syncing books to Payload CMS...")
    sync_resp = httpx.post(f"{PAYLOAD_URL}/api/books/sync-engine", timeout=60.0)
    if sync_resp.is_success:
        result = sync_resp.json()
        print(f"  Sync result: created={result.get('created')}, updated={result.get('updated')}, total={result.get('total')}")
    else:
        print(f"  [WARN] Sync returned {sync_resp.status_code}: {sync_resp.text[:200]}")
        print("  Continuing anyway — books may already exist...")

    # Step 3: Login and get Payload book IDs
    print("\n[3/4] Looking up Payload book IDs for real_estate...")
    token = login_payload()
    headers = get_payload_headers(token)

    # Fetch all books with engineBookId matching real_estate ones
    payload_books = []
    for rb in re_books:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/books",
            params={
                "where[engineBookId][equals]": rb["book_id"],
                "limit": "1",
            },
            headers=headers,
            timeout=15.0,
        )
        if resp.is_success:
            docs = resp.json().get("docs", [])
            if docs:
                payload_books.append({
                    "payload_id": docs[0]["id"],
                    "engine_book_id": rb["book_id"],
                    "title": docs[0].get("title", rb["book_id"]),
                    "category": "real_estate",
                    "status": docs[0].get("status", "unknown"),
                })
                print(f"    ✓ {rb['book_id']} → Payload ID {docs[0]['id']} (status: {docs[0].get('status')})")
            else:
                print(f"    ✗ {rb['book_id']} — not found in Payload, skipping")
        else:
            print(f"    ✗ {rb['book_id']} — query failed: {resp.status_code}")

    if not payload_books:
        print("[ERROR] No books found in Payload. Sync may have failed.")
        sys.exit(1)

    # Step 4: Trigger ingest for each book (skip already indexed)
    print(f"\n[4/4] Triggering ingest pipeline for {len(payload_books)} books...")
    triggered = []
    skipped = []

    for pb in payload_books:
        if pb["status"] == "indexed":
            print(f"  [SKIP] {pb['engine_book_id']} — already indexed")
            skipped.append(pb["engine_book_id"])
            continue

        print(f"  [RUN] {pb['engine_book_id']} (Payload ID: {pb['payload_id']})...")
        try:
            ingest_resp = httpx.post(
                f"{ENGINE_URL}/engine/ingest",
                json={
                    "book_id": pb["payload_id"],
                    "title": pb["engine_book_id"],
                    "category": "real_estate",
                    "force_parse": False,
                },
                timeout=30.0,
            )
            if ingest_resp.is_success:
                print(f"    → Accepted: {ingest_resp.json()}")
                triggered.append(pb)
            else:
                print(f"    → Failed: {ingest_resp.status_code} {ingest_resp.text[:200]}")
        except Exception as e:
            print(f"    → Error: {e}")

        # Small delay between triggers to avoid overwhelming the engine
        time.sleep(2)

    # Summary
    print("\n" + "=" * 60)
    print("BATCH INGEST SUMMARY")
    print("=" * 60)
    print(f"  Total real_estate books: {len(re_books)}")
    print(f"  Skipped (already indexed): {len(skipped)}")
    print(f"  Triggered for ingest: {len(triggered)}")

    if triggered:
        print(f"\n  ⏳ {len(triggered)} pipelines running in background.")
        print("  Monitor progress:")
        print("    - Pipeline Tab in UI: http://localhost:3001/engine/acquisition?tab=pipeline")
        print("    - Or watch engine logs in terminal")

        # Optional: poll until all done
        print("\n  Polling for completion (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(10)
                all_done = True
                for pb in triggered:
                    resp = httpx.get(
                        f"{PAYLOAD_URL}/api/books/{pb['payload_id']}",
                        headers=headers,
                        timeout=10.0,
                    )
                    if resp.is_success:
                        status = resp.json().get("status", "unknown")
                        if status in ("indexed", "error"):
                            print(f"    ✓ {pb['engine_book_id']} → {status}")
                        else:
                            all_done = False
                    else:
                        all_done = False

                if all_done:
                    print("\n  ✅ All pipelines complete!")
                    break
        except KeyboardInterrupt:
            print("\n  Stopped polling. Pipelines still running in background.")

    print("\nDone.")


if __name__ == "__main__":
    main()
