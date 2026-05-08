"""
Flatten MinerU output directories and rename internal files.

MinerU creates: <short_name>/<pdf_stem>/auto/<pdf_stem>_content_list.json
We want:        <short_name>/auto/<short_name>_content_list.json

This script:
  1. Finds all double-nested output dirs
  2. Moves <pdf_stem>/auto/* → auto/*
  3. Renames <pdf_stem>_* files → <short_name>_*
  4. Removes the now-empty <pdf_stem>/ directory

Usage:
    python scripts/ingest/flatten_mineru.py              # Process all
    python scripts/ingest/flatten_mineru.py --dry-run     # Preview only
    python scripts/ingest/flatten_mineru.py --category algonquin-programs
"""
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MINERU_DIR = PROJECT_ROOT / "data" / "mineru_output"

# Categories to process (same as batch_mineru.py)
CATEGORIES = [
    "textbooks", "ecdev", "real_estate",
    "federal-ircc",
    "prov-ontario", "prov-bc", "prov-alberta", "prov-manitoba",
    "prov-saskatchewan", "prov-nova-scotia", "prov-new-brunswick",
    "prov-nwt", "prov-quebec",
    "algonquin-programs",
]


def flatten_one(short_name_dir: Path, dry_run: bool = False) -> str | None:
    """Flatten one book's MinerU output.

    Returns a status string, or None if already flat.
    """
    short_name = short_name_dir.name

    # Find the inner subdirectory (MinerU uses pdf_stem)
    inner_dirs = [d for d in short_name_dir.iterdir()
                  if d.is_dir() and d.name != "auto"]

    if not inner_dirs:
        # Already flat (has auto/ directly) or empty
        if (short_name_dir / "auto").exists():
            return None  # already flat
        return "empty — no inner dir or auto/"

    if len(inner_dirs) > 1:
        return f"SKIP — multiple inner dirs: {[d.name for d in inner_dirs]}"

    inner_dir = inner_dirs[0]
    pdf_stem = inner_dir.name
    auto_src = inner_dir / "auto"

    if not auto_src.exists():
        return f"SKIP — no auto/ in {pdf_stem}/"

    auto_dst = short_name_dir / "auto"

    if dry_run:
        # Count files to rename
        files = list(auto_src.iterdir())
        rename_count = sum(1 for f in files if f.name.startswith(pdf_stem))
        return (f"WOULD flatten: {pdf_stem}/ -> ./ "
                f"({len(files)} files, {rename_count} to rename)")

    # Step 1: Move auto/ up one level
    if auto_dst.exists():
        shutil.rmtree(auto_dst)
    shutil.move(str(auto_src), str(auto_dst))

    # Step 2: Rename files from <pdf_stem>_* to <short_name>_*
    renamed = 0
    for f in auto_dst.iterdir():
        if f.name.startswith(pdf_stem):
            # Replace pdf_stem prefix with short_name
            new_name = short_name + f.name[len(pdf_stem):]
            new_path = f.parent / new_name
            f.rename(new_path)
            renamed += 1

    # Step 3: Remove the now-empty inner directory
    try:
        shutil.rmtree(inner_dir)
    except OSError:
        pass

    return f"OK — moved auto/, renamed {renamed} files"


def main():
    dry_run = "--dry-run" in sys.argv
    filter_category = None
    if "--category" in sys.argv:
        idx = sys.argv.index("--category")
        if idx + 1 < len(sys.argv):
            filter_category = sys.argv[idx + 1]

    print(f"\n{'='*60}")
    print(f"FLATTEN MinerU OUTPUT {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}\n")

    total = 0
    flattened = 0
    skipped = 0
    already_flat = 0

    for category in CATEGORIES:
        if filter_category and category != filter_category:
            continue
        cat_dir = MINERU_DIR / category
        if not cat_dir.exists():
            continue

        cat_count = 0
        for sub in sorted(cat_dir.iterdir()):
            if not sub.is_dir() or sub.name.endswith(".processing"):
                continue

            total += 1
            result = flatten_one(sub, dry_run=dry_run)
            if result is None:
                already_flat += 1
            elif result.startswith("OK") or result.startswith("WOULD"):
                print(f"  [{category}] {sub.name}: {result}")
                flattened += 1
                cat_count += 1
            else:
                print(f"  [{category}] {sub.name}: {result}")
                skipped += 1

        if cat_count > 0:
            print(f"  --- {category}: {cat_count} to flatten ---\n")

    print(f"\n{'='*60}")
    print(f"  Total dirs:    {total}")
    print(f"  Already flat:  {already_flat}")
    print(f"  Flattened:     {flattened}")
    print(f"  Skipped:       {skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
