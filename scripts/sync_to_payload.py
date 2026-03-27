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


# ── Subcategory registry (mirrors README.md sections) ────────────────────────
# Maps engine book_id → subcategory string shown in Library sidebar
SUBCATEGORY_REGISTRY: dict[str, str] = {
    # Python
    "ramalho_fluent_python":       "Python",
    "beazley_python_cookbook":      "Python",
    "downey_think_python_2e":      "Python",
    "downey_how_to_think_like_cs": "Python",
    "okken_python_testing_pytest": "Python",
    "percival_cosmic_python":      "Python",
    # JavaScript / TypeScript
    "flanagan_js_definitive_guide":         "JavaScript",
    "haverbeke_eloquent_javascript":        "JavaScript",
    "simpson_ydkjs_up_going":               "JavaScript",
    "simpson_ydkjs_scope_closures":         "JavaScript",
    "simpson_ydkjs_this_object_prototypes": "JavaScript",
    "simpson_ydkjs_types_grammar":          "JavaScript",
    "simpson_ydkjs_async_performance":      "JavaScript",
    "simpson_ydkjs_es6_beyond":             "JavaScript",
    "basarat_typescript_deep_dive":         "TypeScript",
    # Algorithms
    "cormen_CLRS": "Algorithms",
    # Machine Learning
    "goodfellow_deep_learning":    "Machine Learning",
    "Deep-Learning-with-PyTorch":  "Machine Learning",
    "bishop_prml":                 "Machine Learning",
    "hastie_esl":                  "Machine Learning",
    "james_ISLR":                  "Machine Learning",
    "kelleher_ml_fundamentals":    "Machine Learning",
    "murphy_pml1":                 "Machine Learning",
    "murphy_pml2":                 "Machine Learning",
    "barber_brml":                 "Machine Learning",
    "shalev-shwartz_uml":          "Machine Learning",
    # Mathematics
    "deisenroth_mml":              "Mathematics",
    "boyd_convex_optimization":    "Mathematics",
    "grinstead_snell_probability": "Mathematics",
    "downey_think_stats_2e":       "Mathematics",
    "mackay_information_theory":   "Mathematics",
    # NLP / IR
    "jurafsky_slp3":       "NLP",
    "jurafsky_slp3_jan2026":"NLP",
    "eisenstein_nlp":      "NLP",
    "manning_intro_to_ir": "NLP",
    # Computer Vision
    "szeliski_cv": "Computer Vision",
    # Reinforcement Learning
    "sutton_barto_rl_intro": "Reinforcement Learning",
    # Graph Learning
    "hamilton_grl": "Graph Learning",
    # Software Engineering
    "martin_clean_code":         "Software Engineering",
    "martin_clean_code_excerpt": "Software Engineering",
    "martin_clean_architecture":  "Software Engineering",
    "gof_design_patterns":        "Software Engineering",
    "kleppmann_ddia":             "Software Engineering",
    "hunt_pragmatic_programmer":  "Software Engineering",
    "fowler_refactoring":         "Software Engineering",
    "ejsmont_web_scalability":    "Software Engineering",
    "google_swe":                 "Software Engineering",
    # DevOps
    "chacon_pro_git":    "DevOps",
    "google_sre":        "DevOps",
    "nygard_release_it": "DevOps",
    # Security
    "seitz_black_hat_python":             "Security",
    "aumasson_serious_cryptography":      "Security",
    "andriesse_practical_binary_analysis": "Security",
    "zalewski_tangled_web":               "Security",
    # Networking
    "gourley_http_definitive_guide": "Networking",
    "barrett_ssh_definitive_guide":  "Networking",
    # Database / Frameworks
    "kreibich_using_sqlite":       "Database",
    "fontaine_art_of_postgresql":  "Database",
    "lubanovic_fastapi_modern_web": "Frameworks",
    # UX / Design
    "krug_dont_make_me_think":       "UX Design",
    "norman_design_everyday_things": "UX Design",
    "williams_non_designers_design_book": "UX Design",
    # Video / Educational Design
    "mayer_multimedia_learning":       "Educational Design",
    "clark_mayer_elearning":           "Educational Design",
    "knaflic_storytelling_with_data":   "Educational Design",
    "williams_animators_survival_kit": "Educational Design",
    "heath_made_to_stick":             "Educational Design",
    "mckee_story":                     "Educational Design",
    "snyder_save_the_cat":             "Educational Design",
    # LLM / Post-training slides
    "post_training_llms_slides":           "LLM",
    "sociotechnical_challenges_llms_slides":"LLM",
}


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


def detect_category(book_id: str) -> tuple[str, str]:
    """Detect book (category, subcategory) from book_id.

    Returns:
        (category, subcategory) — subcategory may be empty string.
    """
    if book_id.startswith("ed_update"):
        return ("ecdev", "")
    if book_id.startswith("oreb"):
        return ("real_estate", "")
    subcategory = SUBCATEGORY_REGISTRY.get(book_id, "")
    return ("textbook", subcategory)


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
            cat, sub = detect_category(b["book_id"])
            sub_label = f" / {sub}" if sub else ""
            print(f"  📖 [{cat}{sub_label}] {b['book_id']}: {b['title']}")
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
        category, subcategory = detect_category(engine_id)

        # Skip if already exists
        if engine_id in existing_by_engine_id:
            payload_doc = existing_by_engine_id[engine_id]
            book_id_map[engine_id] = payload_doc["id"]
            stats["books_skipped"] += 1
            print(f"  ⏭  [{i}/{len(books)}] {engine_id} (already exists)")
            continue

        # Create in Payload
        create_data: dict = {
            "engineBookId": engine_id,
            "title": book["title"],
            "authors": book["authors"],
            "category": category,
            "status": "indexed",
            "chunkCount": book["chunk_count"],
            "pipeline": {
                "chunked": "done",
                "stored": "done",
                "vector": "done",
                "fts": "done",
                "toc": "done",
            },
            "metadata": {
                "pageCount": book["page_count"],
                "chapterCount": book["chapter_count"],
                "source": "engine_sync",
            },
        }
        if subcategory:
            create_data["subcategory"] = subcategory
        doc = client.create("books", create_data)

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


def fix_pipeline(args: argparse.Namespace):
    """Backfill pipeline fields for existing books based on their status."""
    print("\n🔧 Fixing pipeline fields for existing books...")
    client = PayloadClient(args.url)
    client.login(args.email, args.password)

    docs = client.find("books", limit=500)
    fixed = 0
    for doc in docs:
        pipeline = doc.get("pipeline") or {}
        # Skip if already has pipeline data
        has_data = any(pipeline.get(k) and pipeline[k] != "pending" for k in ["chunked", "stored", "vector", "fts", "toc"])
        if has_data:
            continue

        status = doc.get("status", "pending")
        if status == "indexed":
            stage_val = "done"
        elif status == "error":
            stage_val = "error"
        else:
            continue  # pending/processing — leave as pending

        client.update("books", doc["id"], {
            "pipeline": {
                "chunked": stage_val,
                "stored": stage_val,
                "vector": stage_val,
                "fts": stage_val,
                "toc": stage_val,
            },
        })
        fixed += 1
        print(f"  ✅ {doc.get('engineBookId', doc['id'])}: pipeline → all {stage_val}")

    print(f"\n  Fixed {fixed} books")


def fix_subcategory(args: argparse.Namespace):
    """Backfill subcategory for existing textbooks that don't have one."""
    print("\n🏷️  Fixing subcategories for existing textbooks...")
    client = PayloadClient(args.url)
    client.login(args.email, args.password)

    docs = client.find("books", limit=500)
    fixed = 0
    skipped = 0
    for doc in docs:
        engine_id = doc.get("engineBookId", "")
        if not engine_id:
            continue

        _, expected_sub = detect_category(engine_id)
        current_sub = doc.get("subcategory") or ""

        # Skip if already correct or no mapping exists
        if current_sub == expected_sub:
            skipped += 1
            continue
        if not expected_sub:
            skipped += 1
            continue

        client.update("books", doc["id"], {"subcategory": expected_sub})
        fixed += 1
        print(f"  ✅ {engine_id}: subcategory → {expected_sub}")

    print(f"\n  Fixed {fixed} books, skipped {skipped}")


def main():
    parser = argparse.ArgumentParser(description="Sync engine SQLite → Payload CMS")
    parser.add_argument("--book", type=str, default=None,
                        help="Sync only a specific book (engine book_id)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be synced without making changes")
    parser.add_argument("--fix-pipeline", action="store_true",
                        help="Backfill pipeline fields for existing books")
    parser.add_argument("--fix-subcategory", action="store_true",
                        help="Backfill subcategory for existing textbooks")
    parser.add_argument("--email", type=str, default=DEFAULT_EMAIL,
                        help="Payload admin email")
    parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD,
                        help="Payload admin password")
    parser.add_argument("--url", type=str, default=PAYLOAD_URL,
                        help="Payload server URL")
    args = parser.parse_args()

    if args.fix_pipeline:
        fix_pipeline(args)
    elif args.fix_subcategory:
        fix_subcategory(args)
    else:
        sync(args)


if __name__ == "__main__":
    main()
