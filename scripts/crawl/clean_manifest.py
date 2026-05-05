"""
Clean manifest.json: remove dead URLs (soft-404) and already-saved 404 PDFs.

1. Check saved PDFs — delete any with "Page not found" in filename/small size
2. HTTP HEAD-check remaining unsaved URLs — remove soft-404s from manifest
3. Save cleaned manifest.json

Usage:
    cd textbook-rag
    python scripts/crawl/clean_manifest.py
    python scripts/crawl/clean_manifest.py --dry-run   # preview only
"""
import json
import sys
import time
from pathlib import Path

import httpx

MANIFEST_PATH = Path("data/crawled_web/algonquin-programs/manifest.json")
PDF_DIR = Path("data/crawled_web/algonquin-programs")

# PDFs smaller than this are likely soft-404 pages
SUSPECT_SIZE_KB = 400

# Timeout for HTTP checks
HTTP_TIMEOUT = 10


def clean_saved_pdfs(dry_run: bool = False) -> set[str]:
    """Check saved PDFs — currently disabled (size-based heuristic too risky)."""
    # Size-based detection removed: listing pages like programs.pdf are
    # legitimately small. We rely on HTTP content checks only (Step 2).
    return set()


def check_urls_alive(pages: list[dict], dry_run: bool = False) -> list[dict]:
    """HTTP HEAD check each unsaved URL, keep only live ones."""
    alive = []
    dead = 0

    with httpx.Client(
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    ) as client:
        for i, page in enumerate(pages, 1):
            url = page["url"]
            filename = page["filename"]

            # Check if PDF already exists (and wasn't deleted)
            pdf_candidates = list(PDF_DIR.rglob(f"{Path(filename).name}.pdf"))
            if pdf_candidates:
                if i % 50 == 0 or i <= 5:
                    print(f"  [{i}/{len(pages)}] SKIP (PDF exists): {Path(filename).name}")
                alive.append(page)
                continue

            # HTTP check for unsaved URLs
            try:
                resp = client.get(url, timeout=HTTP_TIMEOUT)
                title = ""
                body_text_len = 0
                if resp.status_code == 200:
                    # Check for soft-404 in page title
                    import re
                    title_match = re.search(r"<title>(.*?)</title>", resp.text[:5000], re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()

                    # Check for empty/blank pages: extract main content text length
                    # Remove all HTML tags and count meaningful text
                    main_match = re.search(
                        r'<main[^>]*>(.*?)</main>',
                        resp.text, re.DOTALL | re.IGNORECASE,
                    )
                    content_html = main_match.group(1) if main_match else resp.text
                    body_text = re.sub(r'<[^>]+>', '', content_html)
                    body_text = re.sub(r'\s+', ' ', body_text).strip()
                    body_text_len = len(body_text)

                is_dead = False
                reason = ""

                if resp.status_code == 404:
                    is_dead, reason = True, "HTTP 404"
                elif "not found" in title.lower():
                    is_dead, reason = True, f"title='{title[:60]}'"
                elif body_text_len < 200 and "/program/" in url:
                    # Blank program page — has header/nav but no actual content
                    is_dead, reason = True, f"empty page (body={body_text_len} chars)"

                if is_dead:
                    print(f"  [{i}/{len(pages)}] DEAD: {url}")
                    print(f"           {reason}")
                    dead += 1
                    continue
                else:
                    alive.append(page)
                    if i % 20 == 0:
                        print(f"  [{i}/{len(pages)}] checked... ({dead} dead so far)")
            except Exception as e:
                print(f"  [{i}/{len(pages)}] ERROR: {url} — {e}")
                alive.append(page)  # Keep on error (benefit of doubt)

            time.sleep(1.0)  # Be polite — avoid rate limiting

    return alive


def main():
    dry_run = "--dry-run" in sys.argv

    if not MANIFEST_PATH.exists():
        print("[ERROR] manifest.json not found")
        return

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pages = manifest.get("pages", [])
    print(f"Original manifest: {len(pages)} URLs\n")

    # Step 1: Clean saved PDFs that are 404s
    print("=== Step 1: Cleaning saved 404 PDFs ===")
    removed = clean_saved_pdfs(dry_run)
    print(f"  Removed {len(removed)} suspect PDFs\n")

    # Step 2: HTTP check unsaved URLs
    print("=== Step 2: HTTP checking unsaved URLs ===")
    alive_pages = check_urls_alive(pages, dry_run)
    dead_count = len(pages) - len(alive_pages)
    print(f"\n  Alive: {len(alive_pages)}, Dead: {dead_count}\n")

    # Step 3: Save cleaned manifest
    if not dry_run and dead_count > 0:
        # Backup original
        backup = MANIFEST_PATH.with_suffix(".json.bak")
        backup.write_text(MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  Backup saved: {backup}")

        manifest["pages"] = alive_pages
        manifest["total_urls"] = len(alive_pages)
        manifest["cleaned"] = True
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  Cleaned manifest saved: {len(alive_pages)} URLs")
    elif dry_run:
        print("  --dry-run mode, no changes made")
    else:
        print("  No dead URLs found, manifest unchanged")


if __name__ == "__main__":
    main()
