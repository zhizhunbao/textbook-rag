"""
Download Ottawa Economic Development Update quarterly PDFs.

Coverage: Q1 2022 – Q4 2024  (Q2 2022 included; 2025 not yet published as PDF)

Usage:
    uv run python scripts/download_ecdev_pdfs.py           # download all missing
    uv run python scripts/download_ecdev_pdfs.py --dry-run # preview only
    uv run python scripts/download_ecdev_pdfs.py --force   # re-download all
"""
import argparse
import sys
from pathlib import Path

import httpx

# ── Config ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw_pdfs" / "ecdev"

# All confirmed PDF direct-links from ottawa.ca / documents.ottawa.ca
PDFS = [
    # 2022
    ("q1_2022", "https://documents.ottawa.ca/sites/documents/files/economic_update_q1_2022_en.pdf"),
    ("q2_2022", "https://documents.ottawa.ca/sites/documents/files/economic_update_q2_2022_en.pdf"),
    ("q3_2022", "https://documents.ottawa.ca/sites/documents/files/economic_update_q3_2022_en.pdf"),
    ("q4_2022", "https://documents.ottawa.ca/sites/documents/files/economic_update_q4_2022_en.pdf"),
    # 2023
    ("q1_2023", "https://documents.ottawa.ca/sites/documents/files/economic_update_q1_2023_en.pdf"),
    ("q2_2023", "https://documents.ottawa.ca/sites/documents/files/economic_update_q2_2023_en.pdf"),
    ("q3_2023", "https://documents.ottawa.ca/sites/documents/files/economic_update_q3_en_0.pdf"),
    ("q4_2023", "https://documents.ottawa.ca/sites/documents/files/economic_update_q4_en.pdf"),
    # 2024
    ("q1_2024", "https://documents.ottawa.ca/sites/documents/files/economic_update_q1_2024_en.pdf"),
    ("q2_2024", "https://documents.ottawa.ca/sites/default/files/economic_update_q2_2024_en.pdf"),
    ("q3_2024", "https://documents.ottawa.ca/sites/default/files/economic_update_q3_2024_en.pdf"),
    ("q4_2024", "https://documents.ottawa.ca/sites/default/files/economic_update_q4_2024_en.pdf"),
]


def download_pdf(label: str, url: str, dest: Path, force: bool = False) -> bool:
    """Download a single PDF. Returns True if downloaded (or already exists)."""
    filename = f"ed_update_{label}.pdf"
    dest_file = dest / filename

    if dest_file.exists() and not force:
        size_kb = dest_file.stat().st_size // 1024
        print(f"  [SKIP] {filename} — already exists ({size_kb} KB)")
        return True

    print(f"  [DOWN] {filename}")
    print(f"         {url}")

    try:
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            response = client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and len(response.content) < 10_000:
            print(f"  [WARN] Unexpected content-type: {content_type} — skipping")
            return False

        dest_file.write_bytes(response.content)
        size_kb = len(response.content) // 1024
        print(f"  [OK]   {filename} saved ({size_kb} KB)")
        return True

    except httpx.HTTPStatusError as e:
        print(f"  [FAIL] HTTP {e.response.status_code} — {url}")
        return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Ottawa EcDev PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without downloading")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Ottawa Economic Development Update — PDF Downloader")
    print(f"{'='*60}")
    print(f"Output dir : {OUTPUT_DIR}")
    print(f"Total PDFs : {len(PDFS)}")
    print(f"{'='*60}\n")

    if args.dry_run:
        for label, url in PDFS:
            filename = f"ed_update_{label}.pdf"
            dest_file = OUTPUT_DIR / filename
            status = "EXISTS" if dest_file.exists() else "MISSING"
            print(f"  [{status}] {filename}")
            print(f"         {url}")
        print("\n--dry-run: no files downloaded.")
        return

    success, failed = 0, []
    for label, url in PDFS:
        ok = download_pdf(label, url, OUTPUT_DIR, force=args.force)
        if ok:
            success += 1
        else:
            failed.append(f"ed_update_{label}.pdf")

    print(f"\n{'='*60}")
    print(f"Done: {success}/{len(PDFS)} PDFs available in {OUTPUT_DIR}")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        print("You may need to download these manually from:")
        print("  https://ottawa.ca/en/business/economic-development-update")
    print(f"{'='*60}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
