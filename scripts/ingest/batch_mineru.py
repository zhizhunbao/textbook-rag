"""
Batch process all textbook PDFs with MinerU.
Outputs markdown + content_list.json (with bbox) for each book.

Features:
    - Checkpoint / resume: automatically skips completed books
    - Crash recovery: detects interrupted processing via lock files
    - Completeness validation: verifies output JSON is parseable and MD is non-trivial
    - Status log: writes batch_status.json for audit trail

Usage:
    python scripts/batch_mineru.py                  # Process all
    python scripts/batch_mineru.py --dry-run         # Preview only
    python scripts/batch_mineru.py --book bishop     # Process one book
    python scripts/batch_mineru.py --force           # Reprocess all (ignore cache)
    python scripts/batch_mineru.py --book bishop --force  # Reprocess one book
"""
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Config ──
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_PDFS_DIR = PROJECT_ROOT / "data" / "raw_pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "mineru_output"
VENV_MINERU = PROJECT_ROOT / ".venv" / "Scripts" / "mineru"
STATUS_FILE = OUTPUT_DIR / "batch_status.json"
LOCK_SUFFIX = ".processing"

# Categories to scan: category_name -> source directory
SOURCE_DIRS: dict[str, Path] = {
    "textbook":   RAW_PDFS_DIR / "textbooks",
    "ecdev":      RAW_PDFS_DIR / "ecdev",
    "real_estate": RAW_PDFS_DIR / "real_estate",
}

# Minimum output size thresholds for completeness validation
MIN_MD_SIZE_BYTES = 1024        # Markdown must be > 1 KB
MIN_JSON_ENTRIES = 1            # content_list.json must have >= 1 entry

# Books to process: populated by discover_books()
# Each entry: (pdf_path, short_name, category)
BOOKS: list[tuple[Path, str, str]] = []


# ── Discovery ──

def discover_books():
    """Find all PDFs in all category source directories.

    Textbook directory applies exclusion filters for slides/notes.
    ecdev and real_estate directories include everything (no filters).
    """
    for category, source_dir in SOURCE_DIRS.items():
        if not source_dir.exists():
            print(f"  [WARN] Source directory not found, skipping: {source_dir}")
            continue

        for pdf in sorted(source_dir.rglob("*.pdf")):
            rel = pdf.relative_to(source_dir)
            parts = str(rel).replace("\\", "/")

            # Textbook-only exclusion filters
            if category == "textbook":
                if "david_silver" in parts:
                    continue
                if "nlpwdl2025" in parts:
                    continue
                if "cs229-notes" in parts:
                    continue
                if "_slides" in parts.lower():
                    continue
                if "_sections" in parts:
                    continue
                if parts.startswith("math/_sources/mml_sections"):
                    continue
                if "jurafsky_slp3_jan2026" in parts:
                    continue
                if pdf.stat().st_size < 50_000:
                    continue
                if rel.stem[0:2].isdigit() and "-" in rel.stem:
                    continue
                if rel.stem in (
                    "error-analysis",
                    "Linear Algebra",
                    "Multivariate Calculus",
                    "Principal Component Analysis",
                ):
                    continue

            short_name = pdf.stem
            BOOKS.append((pdf, short_name, category))


# ── Checkpoint helpers ──

def _lock_path(short_name: str, category: str) -> Path:
    """Return the lock file path for a given book (per-category lock dir)."""
    lock_dir = OUTPUT_DIR / category
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f"{short_name}{LOCK_SUFFIX}"


def _acquire_lock(short_name: str, category: str) -> None:
    """Create a lock file indicating processing is in progress."""
    lock = _lock_path(short_name, category)
    lock.write_text(
        json.dumps({"started": datetime.now().isoformat(), "book": short_name, "category": category}),
        encoding="utf-8",
    )


def _release_lock(short_name: str, category: str) -> None:
    """Remove the lock file after processing completes (success or handled failure)."""
    lock = _lock_path(short_name, category)
    if lock.exists():
        lock.unlink()


def _is_locked(short_name: str, category: str) -> bool:
    """Check if a book has an active lock (was interrupted mid-processing)."""
    return _lock_path(short_name, category).exists()


def _validate_output(short_name: str, category: str) -> tuple[bool, str]:
    """
    Validate that the output for a book is complete and usable.
    Returns (is_valid, reason_if_invalid).
    """
    out_dir = OUTPUT_DIR / category / short_name
    if not out_dir.exists():
        return False, "output directory missing"

    # Check markdown files exist and have meaningful size
    md_files = list(out_dir.rglob("*.md"))
    if not md_files:
        return False, "no .md files found"

    total_md_size = sum(f.stat().st_size for f in md_files)
    if total_md_size < MIN_MD_SIZE_BYTES:
        return False, f"markdown too small ({total_md_size} bytes < {MIN_MD_SIZE_BYTES})"

    # Check content_list.json exists and is valid JSON
    json_files = list(out_dir.rglob("*_content_list.json"))
    if not json_files:
        return False, "no _content_list.json found"

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            if not isinstance(data, list) or len(data) < MIN_JSON_ENTRIES:
                return False, f"{jf.name}: empty or invalid content list"
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return False, f"{jf.name}: JSON parse error — {e}"

    return True, "ok"


def _clean_incomplete(short_name: str, category: str) -> None:
    """Remove incomplete output directory so the book can be retried cleanly."""
    out_dir = OUTPUT_DIR / category / short_name
    if out_dir.exists():
        print(f"  🧹 Cleaning incomplete output: {out_dir}")
        shutil.rmtree(out_dir, ignore_errors=True)
    _release_lock(short_name, category)


def is_processed(short_name: str, force: bool = False, category: str = "textbook") -> tuple[bool, str]:
    """
    Check if a book has been successfully processed.
    Returns (is_done, status_message).
    """
    if force:
        return False, "forced reprocess"

    # Detect interrupted processing (lock file exists)
    if _is_locked(short_name, category):
        _clean_incomplete(short_name, category)
        return False, "interrupted — will retry"

    # Validate output completeness
    is_valid, reason = _validate_output(short_name, category)
    if is_valid:
        return True, "complete"
    else:
        # Output exists but is invalid — clean it up
        out_dir = OUTPUT_DIR / category / short_name
        if out_dir.exists():
            _clean_incomplete(short_name, category)
            return False, f"invalid output ({reason}) — cleaned, will retry"
        return False, "not started"


# ── Status log ──

def _load_status() -> dict:
    """Load the batch status log from disk."""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _save_status(status: dict) -> None:
    """Persist the batch status log to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _update_status(short_name: str, result: str, elapsed: float = 0) -> None:
    """Update the status log for a single book."""
    status = _load_status()
    status[short_name] = {
        "result": result,
        "elapsed_sec": round(elapsed, 1),
        "timestamp": datetime.now().isoformat(),
    }
    _save_status(status)


# ── Processing ──

def process_book(pdf_path: Path, short_name: str, category: str = "textbook", backend: str = "pipeline") -> bool:
    """Process a single PDF with MinerU, with lock file protection."""
    out_dir = OUTPUT_DIR / category / short_name

    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"Processing: {short_name} [{category}] ({size_mb:.1f} MB)")
    print(f"  Input:  {pdf_path}")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}")

    # Acquire lock before starting
    _acquire_lock(short_name, category)

    cmd = [
        str(VENV_MINERU),
        "-p", str(pdf_path),
        "-o", str(out_dir),
        "-b", backend,
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,  # Show output in real-time
            text=True,
            timeout=3600,  # 60 min max per book
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            # Validate output after successful run
            is_valid, reason = _validate_output(short_name, category)
            if is_valid:
                _release_lock(short_name, category)
                _update_status(short_name, "success", elapsed)
                print(f"✓ {short_name} done in {elapsed:.0f}s ({elapsed/60:.1f} min)")
                return True
            else:
                _update_status(short_name, f"invalid: {reason}", elapsed)
                print(f"✗ {short_name} completed but output invalid: {reason}")
                _clean_incomplete(short_name, category)
                return False
        else:
            _update_status(short_name, f"failed (exit {result.returncode})", time.time() - start)
            print(f"✗ {short_name} FAILED (exit code {result.returncode})")
            _clean_incomplete(short_name, category)
            return False

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        _update_status(short_name, "timeout", elapsed)
        print(f"✗ {short_name} TIMEOUT (>60 min)")
        _clean_incomplete(short_name, category)
        return False
    except KeyboardInterrupt:
        elapsed = time.time() - start
        _update_status(short_name, "interrupted", elapsed)
        print(f"\n⚠ {short_name} interrupted by user after {elapsed:.0f}s")
        # Lock file stays — will be detected on next run
        raise
    except Exception as e:
        elapsed = time.time() - start
        _update_status(short_name, f"error: {e}", elapsed)
        print(f"✗ {short_name} ERROR: {e}")
        _clean_incomplete(short_name, category)
        return False


def main():
    discover_books()

    # Parse args
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    filter_book = None
    filter_category = None
    if "--book" in sys.argv:
        idx = sys.argv.index("--book")
        if idx + 1 < len(sys.argv):
            filter_book = sys.argv[idx + 1].lower()
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            filter_category = sys.argv[idx + 1].lower()

    # Filter books if requested
    books = BOOKS
    if filter_book:
        books = [(p, n, c) for p, n, c in books if filter_book in n.lower()]
    if filter_category:
        books = [(p, n, c) for p, n, c in books if c == filter_category]

    # Show plan
    print(f"\n{'='*60}")
    print(f"MinerU Batch Processing {'(FORCE MODE)' if force else ''}")
    print(f"{'='*60}")
    # Per-category summary
    for cat in SOURCE_DIRS:
        cat_total = sum(1 for _, _, c in BOOKS if c == cat)
        cat_scope = sum(1 for _, _, c in books if c == cat)
        print(f"  [{cat}] {cat_total} total, {cat_scope} in scope")
    print(f"Total books found: {len(BOOKS)}")
    print(f"Books to process:  {len(books)}")
    print()

    skip_count = 0
    todo = []
    for pdf_path, short_name, category in books:
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        done, reason = is_processed(short_name, force=force, category=category)
        if done:
            print(f"  [SKIP] {short_name} [{category}] ({size_mb:.1f} MB) — {reason}")
            skip_count += 1
        else:
            print(f"  [TODO] {short_name} [{category}] ({size_mb:.1f} MB) — {reason}")
            todo.append((pdf_path, short_name, category))

    print(f"\nSkipped: {skip_count}, To process: {len(todo)}")

    if dry_run:
        print("\n--dry-run mode, exiting.")
        return

    if not todo:
        print("\nAll books already processed!")
        return

    # Process
    total_start = time.time()
    success = 0
    failed = []

    try:
        for i, (pdf_path, short_name, category) in enumerate(todo, 1):
            print(f"\n[{i}/{len(todo)}] ", end="")
            if process_book(pdf_path, short_name, category=category):
                success += 1
            else:
                failed.append(short_name)
    except KeyboardInterrupt:
        print("\n\n⚠ Batch interrupted by user. Progress has been saved.")
        print("  Run again to resume from where you left off.")

    # Summary
    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total time: {total_elapsed/60:.1f} min")
    print(f"  Success:    {success}/{len(todo)}")
    if failed:
        print(f"  Failed:     {', '.join(failed)}")
    remaining = len(todo) - success - len(failed)
    if remaining > 0:
        print(f"  Remaining:  {remaining} (run again to resume)")
    print(f"  Status log: {STATUS_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
