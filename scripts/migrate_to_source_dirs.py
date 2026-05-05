"""
Migrate directory structure from persona-based to source-based naming.

Run AFTER the crawler finishes:
  python scripts/migrate_to_source_dirs.py --dry-run    # Preview
  python scripts/migrate_to_source_dirs.py              # Execute

Changes:
  data/crawled_web/edu-school-planning/  →  data/crawled_web/federal-ircc/
  data/mineru_output/edu-school-planning/ →  data/mineru_output/federal-ircc/
  (imm-pathways already deleted)
"""
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DRY_RUN = "--dry-run" in sys.argv

RENAMES = [
    # (old_path, new_path)
    (
        PROJECT_ROOT / "data" / "crawled_web" / "edu-school-planning",
        PROJECT_ROOT / "data" / "crawled_web" / "federal-ircc",
    ),
    (
        PROJECT_ROOT / "data" / "mineru_output" / "edu-school-planning",
        PROJECT_ROOT / "data" / "mineru_output" / "federal-ircc",
    ),
]


def main():
    print("=" * 60)
    print(f"Directory Migration {'(DRY RUN)' if DRY_RUN else ''}")
    print("=" * 60)

    for old, new in RENAMES:
        if not old.exists():
            print(f"  [SKIP] {old.relative_to(PROJECT_ROOT)} — does not exist")
            continue
        if new.exists():
            print(f"  [SKIP] {new.relative_to(PROJECT_ROOT)} — target already exists!")
            continue

        print(f"  [RENAME] {old.relative_to(PROJECT_ROOT)}")
        print(f"        -> {new.relative_to(PROJECT_ROOT)}")

        if not DRY_RUN:
            old.rename(new)
            print(f"        Done!")

    print()
    if DRY_RUN:
        print("  --dry-run mode. No changes made.")
    else:
        print("  Migration complete.")
        print("  Next: update manifest.json persona field if needed.")


if __name__ == "__main__":
    main()
