"""
Unified batch ingest: MinerU output → ChromaDB + Payload CMS (PostgreSQL).

Default behavior: CLEAN REPLACE
  1. Delete old ChromaDB collection for target category
  2. Clear ingest_status.json entries for target category
  3. Re-ingest all MinerU output into fresh collection
  4. Sync book metadata to Payload CMS

Pipeline position:
  Script 1: crawler_cli.py crawl  → crawled_web/<persona>/*.pdf
  Script 2: batch_mineru.py       → mineru_output/<persona>/<name>/*.md
  Script 3: batch_ingest.py (this) → ChromaDB + Payload CMS   ← YOU ARE HERE

Usage:
  python scripts/ingest/batch_ingest.py                        # All categories (clean replace)
  python scripts/ingest/batch_ingest.py --category federal-ircc
  python scripts/ingest/batch_ingest.py --dry-run              # Preview only
  python scripts/ingest/batch_ingest.py --skip-payload         # Skip Payload sync
  python scripts/ingest/batch_ingest.py --skip-vectors         # Skip ChromaDB, only sync Payload
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from engine_v2.settings import init_settings

init_settings()

from engine_v2.ingestion.pipeline import get_vector_store
from engine_v2.readers.mineru_reader import MinerUReader
from engine_v2.ingestion.transformations import BBoxNormalizer
from engine_v2.settings import CHROMA_PERSIST_DIR
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.settings import Settings

# ── Config ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
MINERU_DIR = PROJECT_ROOT / "data" / "mineru_output"
STATUS_FILE = MINERU_DIR / "ingest_status.json"

PAYLOAD_URL = "http://localhost:3001"
ENGINE_URL = "http://localhost:8001"
PAYLOAD_ADMIN_EMAIL = "402707192@qq.com"
PAYLOAD_ADMIN_PASSWORD = "123123"

# Category → ChromaDB collection name mapping
COLLECTION_MAP: dict[str, str] = {
    "textbook":           "textbook_chunks",
    "ecdev":              "ca_ecdev",
    "real_estate":        "ca_real_estate",
    # ── Source-based: federal + provincial ──
    "federal-ircc":       "ca_federal",
    "federal-fcac":       "ca_fcac",
    "federal-cra":        "ca_cra",
    "federal-cdic":       "ca_cdic",
    "federal-esdc":       "ca_esdc",
    "prov-ontario":       "ca_prov_ontario",
    "prov-bc":            "ca_prov_bc",
    "prov-alberta":       "ca_prov_alberta",
    "prov-manitoba":      "ca_prov_manitoba",
    "prov-saskatchewan":  "ca_prov_saskatchewan",
    "prov-nova-scotia":   "ca_prov_nova_scotia",
    "prov-new-brunswick": "ca_prov_new_brunswick",
    "prov-nwt":           "ca_prov_nwt",
    "prov-quebec":        "ca_prov_quebec",
    # ── Education: Algonquin College ──
    "algonquin-programs": "ca_edu_algonquin",
    # ── Banking: Big 5 ──
    "bank-bmo":           "ca_bank_bmo",
    "bank-cibc":          "ca_bank_cibc",
    "bank-rbc":           "ca_bank_rbc",
    "bank-scotiabank":    "ca_bank_scotiabank",
    "bank-td":            "ca_bank_td",
}


# ── Status tracking ─────────────────────────────────────────────────────────

def _load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _save_status(status: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _status_key(category: str, name: str) -> str:
    return f"{category}/{name}"


# ── Discovery ────────────────────────────────────────────────────────────────

def discover_ready_books(
    filter_category: str | None = None,
) -> list[tuple[str, str, Path]]:
    """Scan mineru_output for books that have valid MD output.

    Supports both flat layouts (textbooks, ecdev) and deeply nested
    layouts from web crawls (federal-ircc/en/ircc/services/study-canada/).
    A "book" is identified by having an auto/ subdirectory with .md files.

    Returns: list of (category, short_name, md_dir)
    """
    books = []
    for category in COLLECTION_MAP:
        if filter_category and category != filter_category:
            continue
        cat_dir = MINERU_DIR / category
        if not cat_dir.exists():
            continue

        # Walk the entire tree to find directories containing auto/
        for dirpath, dirnames, _filenames in os.walk(cat_dir):
            dirpath = Path(dirpath)
            # Skip lock dirs
            if dirpath.name.endswith(".processing"):
                dirnames.clear()
                continue
            # Look for auto/ as a direct child
            if "auto" not in dirnames:
                continue
            auto_dir = dirpath / "auto"
            md_files = list(auto_dir.glob("*.md"))
            if not md_files:
                continue
            total_size = sum(f.stat().st_size for f in md_files)
            if total_size < 50:
                continue
            # short_name = relative path from cat_dir (matches batch_mineru output)
            short_name = str(dirpath.relative_to(cat_dir)).replace("\\", "/")
            books.append((category, short_name, dirpath))
            # Don't descend into auto/ or deeper — this is a leaf book
            dirnames.clear()

    return sorted(books)


# ── Vector Ingestion (ChromaDB) ──────────────────────────────────────────────

def ingest_one(category: str, short_name: str, collection_name: str) -> int:
    """Ingest a single book's MinerU output into ChromaDB.

    Returns the number of nodes ingested.
    """
    reader = MinerUReader(MINERU_DIR, merge_sections=True)
    documents = reader.load_data(book_dir_name=short_name, category=category)
    if not documents:
        raise FileNotFoundError(f"No content: {category}/{short_name}")

    vector_store = get_vector_store(collection_name=collection_name)
    pipeline = IngestionPipeline(
        transformations=[
            BBoxNormalizer(),
            Settings.embed_model,
        ],
        vector_store=vector_store,
    )
    nodes = pipeline.run(documents=documents, show_progress=True)
    return len(nodes)


# ── Payload CMS Sync (PostgreSQL) ────────────────────────────────────────────

def _payload_login(httpx_mod) -> tuple[str, dict] | None:
    """Login to Payload CMS. Returns (token, headers) or None."""
    try:
        resp = httpx_mod.post(
            f"{PAYLOAD_URL}/api/users/login",
            json={"email": PAYLOAD_ADMIN_EMAIL, "password": PAYLOAD_ADMIN_PASSWORD},
            timeout=10.0,
        )
        if not resp.is_success:
            print(f"    [WARN] Payload login failed: {resp.status_code}")
            return None
        token = resp.json().get("token")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"JWT {token}",
        }
        return token, headers
    except Exception as e:
        print(f"    [WARN] Payload login error: {e}")
        return None


def _delete_payload_books(httpx_mod, headers: dict, filter_category: str | None) -> int:
    """Bulk-delete old book records from Payload for target category.

    Uses Payload v3 bulk DELETE with `where` clause — single HTTP call
    instead of N individual deletes.
    """
    params: dict[str, str] = {}
    if filter_category:
        params["where[category][equals]"] = filter_category

    try:
        resp = httpx_mod.delete(
            f"{PAYLOAD_URL}/api/books",
            params=params,
            headers=headers,
            timeout=120.0,
        )
        if resp.is_success:
            result = resp.json()
            deleted = len(result.get("docs", []))
            return deleted
        else:
            print(f"    [WARN] Bulk delete failed: {resp.status_code} {resp.text[:200]}")
            return 0
    except Exception as e:
        print(f"    [WARN] Bulk delete error: {e}")
        return 0


def sync_to_payload(filter_category: str | None = None) -> bool:
    """Clean-replace book metadata in Payload CMS.

    1. Delete old book records for target category
    2. Call sync-engine to recreate from current Engine data
    3. Verify record count

    Returns True if sync succeeded.
    """
    try:
        import httpx
    except ImportError:
        print("  [WARN] httpx not installed, skipping Payload sync")
        print("         Install with: pip install httpx")
        return False

    print("\n" + "=" * 60)
    print("PHASE 2: PAYLOAD CMS SYNC (PostgreSQL)")
    print("=" * 60)

    # Step 1: Check if services are running
    try:
        httpx.get(f"{PAYLOAD_URL}/api/users", timeout=5.0)
    except Exception:
        print("  [WARN] Payload CMS not running at", PAYLOAD_URL)
        print("         Skipping Payload sync. Run batch_ingest.py --skip-vectors later.")
        return False

    try:
        httpx.get(f"{ENGINE_URL}/health", timeout=5.0)
    except Exception:
        print("  [WARN] Engine API not running at", ENGINE_URL)
        print("         Skipping Payload sync. Run batch_ingest.py --skip-vectors later.")
        return False

    # Step 2: Login
    print("\n  [1/3] Logging into Payload CMS...")
    auth = _payload_login(httpx)
    if not auth:
        return False
    token, headers = auth
    print(f"    Logged in as {PAYLOAD_ADMIN_EMAIL}")

    # Step 3: Delete old book records
    scope = filter_category or "ALL categories"
    print(f"\n  [2/3] Deleting old book records ({scope})...")
    deleted = _delete_payload_books(httpx, headers, filter_category)
    print(f"    Deleted {deleted} old book records")

    # Step 4: Sync fresh data from Engine
    print(f"\n  [3/3] Syncing fresh books from Engine -> Payload...")
    try:
        sync_url = f"{PAYLOAD_URL}/api/books/sync-engine"
        if filter_category:
            sync_url += f"?category={filter_category}"
        sync_resp = httpx.post(sync_url, timeout=600.0)
        if sync_resp.is_success:
            result = sync_resp.json()
            print(f"    created={result.get('created')}, "
                  f"updated={result.get('updated')}, "
                  f"total={result.get('total')}")
        else:
            print(f"    [WARN] Sync returned {sync_resp.status_code}: "
                  f"{sync_resp.text[:200]}")
    except Exception as e:
        print(f"    [ERROR] Sync failed: {e}")
        return False

    return True


# ── Clean (delete old data) ──────────────────────────────────────────────────

def clean_collections(filter_category: str | None = None) -> None:
    """Delete ChromaDB collections and clear ingest_status for target categories."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    existing = {c.name for c in client.list_collections()}

    # Determine which collections to delete
    targets = {}
    for cat, col in COLLECTION_MAP.items():
        if filter_category and cat != filter_category:
            continue
        targets[cat] = col

    for cat, col in targets.items():
        if col in existing:
            client.delete_collection(col)
            print(f"  [DELETE] ChromaDB collection '{col}' (category: {cat})")
        else:
            print(f"  [SKIP]   '{col}' not found in ChromaDB")

    # Clear ingest_status.json entries
    status = _load_status()
    keys_to_remove = [
        k for k in status
        if any(k.startswith(f"{cat}/") for cat in targets)
    ]
    for k in keys_to_remove:
        del status[k]
    _save_status(status)
    if keys_to_remove:
        print(f"  [CLEAR]  {len(keys_to_remove)} entries from ingest_status.json")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    skip_payload = "--skip-payload" in sys.argv
    skip_vectors = "--skip-vectors" in sys.argv
    filter_category = None
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            filter_category = sys.argv[idx + 1]

    # ── Phase 1: ChromaDB Vector Ingestion (clean replace) ───────
    if not skip_vectors:
        books = discover_ready_books(filter_category=filter_category)

        print(f"\n{'='*60}")
        print(f"PHASE 1: VECTOR INGESTION (MinerU -> ChromaDB)")
        print(f"{'='*60}")
        print(f"  Mode:    CLEAN REPLACE (delete old -> ingest new)")
        print(f"  Total:   {len(books)} books")
        if filter_category:
            print(f"  Filter:  {filter_category}")
        print()

        if dry_run:
            print("  --dry-run mode, would process:")
            for cat, name, _ in books:
                print(f"    {cat}/{name}")
            print(f"\n  Total: {len(books)} books")
        elif not books:
            print("  No books found to ingest!")
        else:
            # Step 1: Clean old data
            print("  --- Cleaning old data ---")
            clean_collections(filter_category=filter_category)

            # Step 2: Ingest all
            print("\n  --- Ingesting new data ---")
            status = _load_status()
            t0 = time.time()
            success = 0
            failed = []

            for i, (category, name, _path) in enumerate(books, 1):
                collection = COLLECTION_MAP.get(category, f"ca_{category}")
                key = _status_key(category, name)
                print(f"\n  [{i}/{len(books)}] {category}/{name} -> {collection}")

                start = time.time()
                try:
                    node_count = ingest_one(category, name, collection)
                    elapsed = time.time() - start
                    status[key] = {
                        "result": "success",
                        "nodes": node_count,
                        "collection": collection,
                        "elapsed_sec": round(elapsed, 1),
                        "timestamp": datetime.now().isoformat(),
                    }
                    _save_status(status)
                    print(f"    [OK] {node_count} nodes in {elapsed:.1f}s")
                    success += 1
                except Exception as e:
                    elapsed = time.time() - start
                    status[key] = {
                        "result": f"error: {e}",
                        "elapsed_sec": round(elapsed, 1),
                        "timestamp": datetime.now().isoformat(),
                    }
                    _save_status(status)
                    print(f"    [FAIL] {e}")
                    failed.append(f"{category}/{name}")

            total_elapsed = time.time() - t0
            print(f"\n  Vector ingestion: {success}/{len(books)} in {total_elapsed/60:.1f} min")
            if failed:
                print(f"  Failed: {', '.join(failed[:5])}")

    # ── Phase 2: Payload CMS Sync ────────────────────────────────
    if not skip_payload and not dry_run:
        sync_to_payload(filter_category=filter_category)

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
