"""Rename long-named PDFs and MinerU outputs, update manifest.

Fixes Windows MAX_PATH issues by truncating filenames > 50 chars.
"""
import hashlib
import json
import shutil
from pathlib import Path

MAX_FILENAME_LEN = 50
PROJECT_ROOT = Path(__file__).parent.parent
PDF_DIR = PROJECT_ROOT / "data" / "crawled_web" / "imm-pathways"
MINERU_DIR = PROJECT_ROOT / "data" / "mineru_output" / "imm-pathways"
MANIFEST = PDF_DIR / "manifest.json"


def truncate_name(name: str) -> str:
    """Apply same truncation logic as web_crawler._url_to_filename."""
    if len(name) <= MAX_FILENAME_LEN:
        return name
    hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
    prefix_len = MAX_FILENAME_LEN - 9
    return f"{name[:prefix_len]}-{hash_suffix}"


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    renames = []

    for page in manifest["pages"]:
        old_name = page["filename"]
        new_name = truncate_name(old_name)
        if old_name == new_name:
            continue

        renames.append((old_name, new_name))
        page["filename"] = new_name

        # Rename PDF
        old_pdf = PDF_DIR / f"{old_name}.pdf"
        new_pdf = PDF_DIR / f"{new_name}.pdf"
        if old_pdf.exists():
            old_pdf.rename(new_pdf)
            print(f"  PDF:   {old_name}.pdf -> {new_name}.pdf")

        # Rename MinerU output dir
        old_mineru = MINERU_DIR / old_name
        new_mineru = MINERU_DIR / new_name
        if old_mineru.exists():
            # MinerU has nested dir: name/name/auto/...
            # Need to rename both outer and inner dir
            old_inner = old_mineru / old_name
            if old_inner.exists():
                new_inner = old_mineru / new_name
                old_inner.rename(new_inner)
                # Rename files inside auto/
                auto_dir = new_inner / "auto"
                if auto_dir.exists():
                    for f in auto_dir.iterdir():
                        if f.name.startswith(old_name):
                            new_fname = f.name.replace(old_name, new_name, 1)
                            f.rename(auto_dir / new_fname)
                            print(f"  FILE:  {f.name} -> {new_fname}")
            old_mineru.rename(new_mineru)
            print(f"  MINER: {old_name}/ -> {new_name}/")

    if not renames:
        print("No files need renaming!")
        return

    # Update manifest
    manifest["total_urls"] = len(manifest["pages"])
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"Renamed {len(renames)} entries:")
    for old, new in renames:
        print(f"  {old}")
        print(f"    -> {new}")
    print(f"Manifest updated: {MANIFEST}")


if __name__ == "__main__":
    main()
