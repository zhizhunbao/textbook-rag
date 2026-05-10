"""Inject missing CIMM committee pages into federal-ircc manifest.

These pages live deep in the /corporate/transparency/committees/ subtree
and are not reached by BFS_DEPTH=3 from the existing seed URLs.

Usage:
    uv run python scripts/crawl/inject_cimm_pages.py            # inject + report
    uv run python scripts/crawl/inject_cimm_pages.py --dry-run   # preview only
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "crawled_web" / "federal-ircc" / "manifest.json"

# ── CIMM Nov 18, 2025: Sustainable Immigration / Health / Credential Recognition ──
CIMM_NOV_2025_BASE = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-nov-18-2025"
CIMM_NOV_2025_PAGES = [
    "",                                          # TOC page
    "/opening-statement",
    "/parliamentary-context",
    "/summary-data-sheet",
    "/master-data-sheet",
    "/quebec-key-facts",
    "/health-human-resources",
    "/talent-attraction",
    "/foreign-credential-recognition",
    "/work-permits-for-visa-trainee-physicians",
    "/support-for-asylum-seekers",
    "/levels",                                    # ← the key page!
    "/francophone-immigration",
    "/security-screening",
    "/fraud",
    "/management-of-expired-and-cancelled-visas",
    "/processing-times-and-service-delivery",
    "/modernizing-canadas-immigration-system",
    "/1-q-168-response-and-annexe",
    "/2-q-235-response-and-annex",
    "/3-q-257-response-and-annex",
]

# ── CIMM Nov 25, 2024: Immigration Levels Plan 2025-2027 ──
CIMM_NOV_2024_BASE = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-nov-25-2024"

# ── Other recent CIMM sessions (2024+) — TOC pages only for now ──
OTHER_CIMM_TOCS = [
    f"{CIMM_NOV_2024_BASE}",
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-may-27-2024",
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-mar-20-2024",
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-feb-28-2024",
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees/cimm-feb-7-2024",
]

# Also add the committees index itself
COMMITTEES_INDEX = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency/committees"


def build_urls() -> list[str]:
    """Build the full list of CIMM URLs to inject."""
    urls = []
    # Nov 2025 full sub-pages
    for suffix in CIMM_NOV_2025_PAGES:
        url = f"{CIMM_NOV_2025_BASE}{suffix}.html"
        urls.append(url)
    # Other CIMM TOCs
    for url in OTHER_CIMM_TOCS:
        urls.append(url + ".html" if not url.endswith(".html") else url)
    # Committees index
    urls.append(COMMITTEES_INDEX + ".html")
    return urls


def main():
    dry_run = "--dry-run" in sys.argv

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing_urls = {p["url"].rstrip("/") for p in manifest["pages"]}

    new_pages = []
    for url in build_urls():
        norm = url.rstrip("/")
        if norm in existing_urls:
            continue
        path = urlparse(norm).path
        filename = path.lstrip("/").rstrip("/").replace(".html", "")
        new_pages.append({"url": norm, "filename": filename})

    print(f"Total CIMM URLs:    {len(build_urls())}")
    print(f"Already in manifest: {len(build_urls()) - len(new_pages)}")
    print(f"New to add:          {len(new_pages)}")

    if not new_pages:
        print("\n[OK] All CIMM pages already in manifest.")
        return

    if dry_run:
        print("\n[DRY RUN] Would add:")
        for p in new_pages:
            print(f"  {p['url']}")
        return

    # Prepend new pages for priority crawling
    manifest["pages"] = new_pages + manifest["pages"]
    manifest["total_urls"] = len(manifest["pages"])
    manifest["cimm_injected_at"] = datetime.now().isoformat()

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[OK] Prepended {len(new_pages)} CIMM pages (total: {manifest['total_urls']})")
    print("\nNow run:")
    print("  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/federal-ircc/manifest.json")


if __name__ == "__main__":
    main()
