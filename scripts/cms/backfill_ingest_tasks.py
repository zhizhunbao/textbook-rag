"""Backfill ingest-task records based on real data on disk.

Checks:
  - mineru_output: content_list.json exists → chunked=done
  - ChromaDB: vectors with matching book_id → vector=done, embeddings=done
  - Creates one ingest-task per book with accurate log info

Usage: python scripts/backfill_ingest_tasks.py
"""
import json
from pathlib import Path

import chromadb
import requests

# ── Config ────────────────────────────────────────────────────
PAYLOAD_URL = "http://localhost:3001"
EMAIL = "402707192@qq.com"
PASSWORD = "123123"

MINERU_OUTPUT_DIR = Path("data/mineru_output")
CHROMA_PERSIST_DIR = Path("data/chroma_persist")
CHROMA_COLLECTION = "textbook_chunks"


def get_chroma_collection():
    """Get ChromaDB collection handle (lazy, query per-book later)."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    try:
        col = client.get_collection(CHROMA_COLLECTION)
        print(f"  ChromaDB: collection '{CHROMA_COLLECTION}' has {col.count()} total vectors")
        return col
    except Exception:
        print("  ⚠️  ChromaDB collection not found")
        return None


def get_vector_count(collection, book_id: str) -> int:
    """Query vector count for a single book from ChromaDB."""
    if collection is None:
        return 0
    try:
        result = collection.get(where={"book_id": book_id}, include=[])
        return len(result["ids"])
    except Exception:
        return 0


def get_mineru_stats() -> dict[str, dict]:
    """Scan mineru_output to find which books have content_list.json."""
    stats: dict[str, dict] = {}
    for category_dir in MINERU_OUTPUT_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        for book_dir in category_dir.iterdir():
            if not book_dir.is_dir():
                continue
            book_id = book_dir.name
            auto_dir = book_dir / book_id / "auto"
            content_list = auto_dir / f"{book_id}_content_list.json"
            chunk_count = 0
            if content_list.exists():
                try:
                    data = json.loads(content_list.read_text(encoding="utf-8"))
                    chunk_count = len(data) if isinstance(data, list) else 0
                except Exception:
                    pass

            stats[book_id] = {
                "category": category,
                "has_content_list": content_list.exists(),
                "content_list_chunks": chunk_count,
                "has_middle_json": (auto_dir / f"{book_id}_middle.json").exists(),
            }

    print(f"  MinerU: {len(stats)} books scanned")
    return stats


def main():
    print("📊 Scanning real data on disk...\n")

    # 1. Scan local data
    mineru = get_mineru_stats()
    chroma_col = get_chroma_collection()

    # 2. Login to Payload CMS
    print(f"\n🔐 Logging into Payload CMS...")
    r = requests.post(
        f"{PAYLOAD_URL}/api/users/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    token = r.json().get("token")
    if not token:
        print("Login failed:", r.text)
        return
    headers = {"Authorization": f"JWT {token}", "Content-Type": "application/json"}
    print("  ✅ Logged in")

    # 3. Fetch all books from Payload
    print("\n📚 Fetching books from Payload CMS...")
    all_books = []
    page = 1
    while True:
        r = requests.get(
            f"{PAYLOAD_URL}/api/books",
            params={"limit": 100, "depth": 0, "page": page},
            headers=headers,
        )
        data = r.json()
        all_books.extend(data.get("docs", []))
        if not data.get("hasNextPage"):
            break
        page += 1
    print(f"  Found {len(all_books)} books")

    # 4. Fetch existing ingest-tasks to avoid duplicates
    r = requests.get(
        f"{PAYLOAD_URL}/api/ingest-tasks",
        params={"limit": 500, "depth": 0},
        headers=headers,
    )
    existing_book_ids = {t["book"] for t in r.json().get("docs", []) if t.get("book")}
    print(f"  Existing tasks: {len(existing_book_ids)} books already have tasks")

    # 5. Backfill
    print("\n🔧 Backfilling ingest-tasks...\n")
    created = 0
    skipped = 0
    errors = 0

    for book in all_books:
        book_id = book["id"]
        engine_id = book.get("engineBookId") or ""
        title = book.get("title", "?")
        status = book.get("status", "pending")

        # Skip if already has a task
        if book_id in existing_book_ids:
            skipped += 1
            continue

        # Skip pending books that haven't been processed
        if status == "pending" and engine_id not in mineru:
            skipped += 1
            continue

        # Determine real pipeline state from disk data
        m = mineru.get(engine_id, {})
        vector_count = get_vector_count(chroma_col, engine_id) if engine_id else 0

        has_chunks = m.get("has_content_list", False)
        chunk_count = m.get("content_list_chunks", 0)
        has_vectors = vector_count > 0

        # Build log with real data
        log_lines = []
        if has_chunks:
            log_lines.append(f"MinerU output: {chunk_count} content blocks parsed")
        if has_vectors:
            log_lines.append(f"ChromaDB: {vector_count} vectors indexed")
        log_lines.append("Backfilled from real data on disk.")

        # Determine task status
        if has_chunks and has_vectors:
            task_status = "done"
            progress = 100
        elif has_chunks:
            task_status = "done"
            progress = 50
        else:
            task_status = "queued"
            progress = 0

        payload = {
            "taskType": "ingest",
            "book": book_id,
            "status": task_status,
            "progress": progress,
            "log": "\n".join(log_lines),
            "startedAt": book.get("createdAt"),
            "finishedAt": book.get("updatedAt") if task_status == "done" else None,
        }

        try:
            resp = requests.post(
                f"{PAYLOAD_URL}/api/ingest-tasks",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            created += 1
            flag = "✅" if task_status == "done" else "⏳"
            print(
                f"  {flag} [{book_id}] {title[:40]:<40} "
                f"chunks={chunk_count:<6} vectors={vector_count:<6} → {task_status}"
            )
        except Exception as e:
            errors += 1
            print(f"  ❌ [{book_id}] {title}: {e}")

    print(f"\n🎯 Done: {created} created, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
