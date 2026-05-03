"""
Shorten long filenames in crawled_web/<category> directories.

MinerU creates output like: <out>/<stem>/<stem>/auto/images/<hash>.jpg
On Windows, MAX_PATH = 260. With deeply nested paths, long stems cause failures.

Strategy:
  - Max stem length = 30 chars
  - If stem > 30, keep first 20 chars + "-" + 8-char hash (from original)
  - Rename the PDF file and update manifest.json

Usage:
    python scripts/ingest/shorten_web_filenames.py --category imm-pathways
    python scripts/ingest/shorten_web_filenames.py --category imm-pathways --dry-run
"""
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CRAWLED_WEB_DIR = PROJECT_ROOT / "data" / "crawled_web"

MAX_STEM = 30  # Maximum stem length (without .pdf)


def short_name(stem: str) -> str:
    """Return a shortened stem if it exceeds MAX_STEM, otherwise return as-is."""
    if len(stem) <= MAX_STEM:
        return stem
    # Use 8-char hash of original for uniqueness
    h = hashlib.md5(stem.encode()).hexdigest()[:8]
    prefix = stem[:20].rstrip("-")
    return f"{prefix}-{h}"


def main():
    dry_run = "--dry-run" in sys.argv
    category = None
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            category = sys.argv[idx + 1]

    if not category:
        print("Usage: python shorten_web_filenames.py --category <name> [--dry-run]")
        sys.exit(1)

    cat_dir = CRAWLED_WEB_DIR / category
    manifest_path = cat_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"[ERROR] manifest.json not found: {manifest_path}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    rename_count = 0
    renames = []  # (old_stem, new_stem)

    for page in manifest.get("pages", []):
        old_stem = page.get("filename", "")
        if not old_stem:
            continue

        new_stem = short_name(old_stem)
        if new_stem == old_stem:
            continue

        old_pdf = cat_dir / f"{old_stem}.pdf"
        new_pdf = cat_dir / f"{new_stem}.pdf"

        print(f"  {old_stem}.pdf")
        print(f"    -> {new_stem}.pdf  ({len(old_stem)} -> {len(new_stem)} chars)")

        if not dry_run:
            if old_pdf.exists():
                if new_pdf.exists():
                    print(f"    [WARN] Target already exists, skipping: {new_pdf.name}")
                    continue
                old_pdf.rename(new_pdf)
            else:
                print(f"    [WARN] Source PDF not found: {old_pdf.name}")
                # Still update manifest for consistency

            # Update manifest entry
            page["filename"] = new_stem
            if "file_size" in page and new_pdf.exists():
                page["file_size"] = new_pdf.stat().st_size

        rename_count += 1
        renames.append((old_stem, new_stem))

    if rename_count == 0:
        print(f"\n[OK] All filenames in '{category}' are already ≤ {MAX_STEM} chars. Nothing to do.")
        return

    print(f"\n{'[DRY-RUN] Would rename' if dry_run else 'Renamed'}: {rename_count} files")

    if not dry_run:
        # Write updated manifest
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[OK] Updated manifest.json")

    # Show rename mapping for reference
    print(f"\nRename mapping:")
    for old, new in renames:
        print(f"  {old} -> {new}")


if __name__ == "__main__":
    main()
