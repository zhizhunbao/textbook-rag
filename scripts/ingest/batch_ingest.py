"""
Batch ingest: scan mineru_output for new Markdown, push delta to ChromaDB.

Auto-detects what's already in the vector store and only ingests new content.
Designed to run after batch_mineru.py completes.

Pipeline position:
  Script 1: crawler_cli.py crawl  → crawled_web/<persona>/*.pdf
  Script 2: batch_mineru.py       → mineru_output/<persona>/<name>/*.md
  Script 3: batch_ingest.py (this) → chroma_persist/ (vector DB)   ← YOU ARE HERE

Usage:
  uv run python scripts/ingest/batch_ingest.py                     # All categories
  uv run python scripts/ingest/batch_ingest.py --category imm-pathways
  uv run python scripts/ingest/batch_ingest.py --dry-run            # Preview only
  uv run python scripts/ingest/batch_ingest.py --force              # Re-ingest all
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from engine_v2.settings import init_settings

init_settings()

from engine_v2.ingestion.pipeline import get_vector_store
from engine_v2.readers.mineru_reader import MinerUReader
from engine_v2.ingestion.transformations import BBoxNormalizer
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.settings import Settings

# ── Config ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
MINERU_DIR = PROJECT_ROOT / "data" / "mineru_output"
STATUS_FILE = MINERU_DIR / "ingest_status.json"

# Category → ChromaDB collection name mapping
# Organized by data source (not persona)
COLLECTION_MAP: dict[str, str] = {
    "textbook":           "textbook_chunks",
    "ecdev":              "ca_ecdev",
    "real_estate":        "ca_real_estate",
    # ── Source-based: federal + provincial ──
    "federal-ircc":       "ca_federal",
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

    Returns: list of (category, short_name, md_dir)
    """
    books = []
    for category in COLLECTION_MAP:
        if filter_category and category != filter_category:
            continue
        cat_dir = MINERU_DIR / category
        if not cat_dir.exists():
            continue
        for sub in sorted(cat_dir.iterdir()):
            if not sub.is_dir():
                continue
            # Skip lock files from batch_mineru
            if sub.name.endswith(".processing"):
                continue
            # Check for valid MD output
            md_files = list(sub.rglob("*.md"))
            if md_files:
                total_size = sum(f.stat().st_size for f in md_files)
                if total_size >= 50:
                    books.append((category, sub.name, sub))
    return books


# ── Ingestion ────────────────────────────────────────────────────────────────

def ingest_one(category: str, short_name: str, collection_name: str) -> int:
    """Ingest a single book's MinerU output into ChromaDB.

    Returns the number of nodes ingested.
    """
    reader = MinerUReader(MINERU_DIR)
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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    filter_category = None
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            filter_category = sys.argv[idx + 1]

    # Discover all ready books
    books = discover_ready_books(filter_category=filter_category)
    status = _load_status()

    print(f"\n{'='*60}")
    print(f"BATCH INGEST — mineru_output → ChromaDB")
    print(f"{'='*60}")
    print(f"  Total ready: {len(books)}")
    if filter_category:
        print(f"  Filter:      {filter_category}")
    print()

    # Classify: done vs todo
    todo = []
    for category, name, path in books:
        key = _status_key(category, name)
        if not force and key in status and status[key].get("result") == "success":
            md_dir_mtime = max(f.stat().st_mtime for f in path.rglob("*.md"))
            ingested_at = status[key].get("timestamp", "")
            # Check if MD files were modified after last ingest
            if ingested_at:
                try:
                    last_ingest = datetime.fromisoformat(ingested_at).timestamp()
                    if md_dir_mtime <= last_ingest:
                        print(f"  [SKIP] {category}/{name} — already ingested")
                        continue
                    else:
                        print(f"  [UPDATE] {category}/{name} — MD changed since last ingest")
                except ValueError:
                    pass
            else:
                print(f"  [SKIP] {category}/{name} — already ingested")
                continue
        else:
            reason = "forced" if force else "new"
            print(f"  [TODO] {category}/{name} — {reason}")
        todo.append((category, name))

    print(f"\n  To ingest: {len(todo)}")

    if dry_run:
        print("\n--dry-run mode, exiting.")
        return

    if not todo:
        print("\nAll books already ingested!")
        return

    # Process
    t0 = time.time()
    success = 0
    failed = []

    for i, (category, name) in enumerate(todo, 1):
        collection = COLLECTION_MAP.get(category, f"ca_{category}")
        key = _status_key(category, name)
        print(f"\n[{i}/{len(todo)}] {category}/{name} → {collection}")

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
            print(f"  [OK] {node_count} nodes in {elapsed:.1f}s")
            success += 1
        except Exception as e:
            elapsed = time.time() - start
            status[key] = {
                "result": f"error: {e}",
                "elapsed_sec": round(elapsed, 1),
                "timestamp": datetime.now().isoformat(),
            }
            _save_status(status)
            print(f"  [FAIL] {e}")
            failed.append(f"{category}/{name}")

    total_elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"INGEST COMPLETE")
    print(f"  Time:    {total_elapsed/60:.1f} min")
    print(f"  Success: {success}/{len(todo)}")
    if failed:
        print(f"  Failed:  {', '.join(failed)}")
    print(f"  Status:  {STATUS_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
