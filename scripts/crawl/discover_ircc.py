"""Discover all IRCC URLs into federal-ircc manifest.

Two phases:
  Phase 1 (BFS):  Crawl service pages via crawl4ai BFS to discover linked pages.
  Phase 2 (News): Paginate GC Advanced News Search via Playwright to discover
                   news articles (newsreleases, backgrounders, statements, etc.).

Usage:
    uv run python scripts/crawl/_discover_all_ircc.py
    uv run python scripts/crawl/_discover_all_ircc.py --skip-bfs         # news only
    uv run python scripts/crawl/_discover_all_ircc.py --skip-news        # BFS only
    uv run python scripts/crawl/_discover_all_ircc.py --news-year-min 2025
    uv run python scripts/crawl/_discover_all_ircc.py --dry-run
"""
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Config ──
PERSONA = "federal-ircc"
MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "crawled_web" / PERSONA / "manifest.json"

# Phase 1: BFS seeds (service + corporate pages)
BFS_SEEDS = [
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/visit-canada.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-citizenship.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/permanent-residents.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/canadian-passports.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/settle-canada.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/refugees.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/application.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/protect-fraud.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate.html",
    "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/transparency.html",
]
BFS_DEPTH = 3
BFS_MAX_PAGES = 200

# Phase 1.5: Supplemental URLs — gc-subway section nav pages that BFS misses
# because they live inside <nav> tags which are excluded by excluded_tags=["nav"]
# to avoid the massive government-wide site menu.
_BASE = "https://www.canada.ca/en/immigration-refugees-citizenship"
SUPPLEMENTAL_URLS = [
    # ── Express Entry gc-subway ──
    f"{_BASE}/services/immigrate-canada/express-entry/who-can-apply.html",
    f"{_BASE}/services/immigrate-canada/express-entry/check-score.html",
    f"{_BASE}/services/immigrate-canada/express-entry/documents.html",
    f"{_BASE}/services/immigrate-canada/express-entry/create-profile.html",
    f"{_BASE}/services/immigrate-canada/express-entry/rounds-invitations.html",
    f"{_BASE}/services/immigrate-canada/express-entry/rounds-invitations/category-based-selection.html",
    f"{_BASE}/services/immigrate-canada/express-entry/apply-permanent-residence.html",
    f"{_BASE}/services/immigrate-canada/express-entry/after-apply.html",
    f"{_BASE}/services/immigrate-canada/express-entry/application-approved.html",
    # ── Express Entry sub-pages (eligibility) ──
    f"{_BASE}/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html",
    f"{_BASE}/services/immigrate-canada/express-entry/eligibility/canadian-experience-class.html",
    f"{_BASE}/services/immigrate-canada/express-entry/eligibility/skilled-trades.html",
    f"{_BASE}/services/immigrate-canada/express-entry/check-score/crs-criteria.html",
    # ── Visit Canada gc-subway ──
    f"{_BASE}/services/visit-canada/eta.html",
    f"{_BASE}/services/visit-canada/apply-visitor-visa.html",
    f"{_BASE}/services/visit-canada/business.html",
    # ── Work Canada gc-subway ──
    f"{_BASE}/services/work-canada/permit.html",
    f"{_BASE}/services/work-canada/hire-temporary-foreign.html",
    f"{_BASE}/services/work-canada/iec.html",
    # ── Study Canada gc-subway ──
    f"{_BASE}/services/study-canada/study-permit.html",
    f"{_BASE}/services/study-canada/work.html",
    # ── Citizenship gc-subway ──
    f"{_BASE}/services/canadian-citizenship/become-canadian-citizen.html",
    f"{_BASE}/services/canadian-citizenship/proof-citizenship.html",
    # ── Provincial Nominees ──
    f"{_BASE}/services/immigrate-canada/provincial-nominees.html",
    f"{_BASE}/services/immigrate-canada/provincial-nominees/express-entry.html",
    f"{_BASE}/services/immigrate-canada/provincial-nominees/non-express-entry.html",
    # ── Family Sponsorship ──
    f"{_BASE}/services/immigrate-canada/family-sponsorship.html",
    f"{_BASE}/services/immigrate-canada/family-sponsorship/spouse-partner-children.html",
    f"{_BASE}/services/immigrate-canada/family-sponsorship/parents-grandparents.html",
    # ── PGWP / Study ──
    f"{_BASE}/services/study-canada/work/after-graduation.html",
    f"{_BASE}/services/study-canada/work/after-graduation/eligibility.html",
    # ── Ministerial Instructions / Rounds archive ──
    f"{_BASE}/corporate/mandate/policies-operational-instructions-agreements/ministerial-instructions/express-entry-rounds.html",
    # ── EE Rounds raw JSON data (dynamically loaded by rounds-invitations page) ──
    # These contain ALL historical round data: scores, dates, invitation counts
    "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json",
    "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_4_en.json",
]

# Phase 2: News search pagination
NEWS_SEARCH_URL = "https://www.canada.ca/en/news/advanced-news-search/news-results.html"
NEWS_DEPT = "departmentofcitizenshipandimmigration"
NEWS_TYPES = ["newsreleases", "backgrounders", "statements", "mediaadvisories", "speeches"]
NEWS_PER_PAGE = 10
NEWS_YEAR_MIN = 2024


# ── Phase 1: BFS ──

async def run_bfs_discovery():
    """Discover IRCC service pages via crawl4ai BFS."""
    from engine_v2.crawling.web_crawler_v2 import discover_urls

    print(f"\n{'='*60}")
    print(f"PHASE 1: BFS Discovery ({len(BFS_SEEDS)} seeds)")
    print(f"{'='*60}")

    for i, url in enumerate(BFS_SEEDS):
        name = url.rstrip("/").split("/")[-1].replace(".html", "")
        print(f"\n[{i+1}/{len(BFS_SEEDS)}] {name}")
        try:
            manifest = await discover_urls(
                url, persona_slug=PERSONA,
                max_depth=BFS_DEPTH, max_pages=BFS_MAX_PAGES,
            )
            print(f"  -> Manifest: {manifest}")
        except Exception as e:
            print(f"  ERROR: {e}")


# ── Phase 2: News ──

async def discover_news_urls(year_min: int = NEWS_YEAR_MIN) -> list[dict]:
    """Paginate through GC Advanced News Search to collect IRCC news URLs."""
    from playwright.async_api import async_playwright

    all_urls: list[dict] = []
    seen: set[str] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for news_type in NEWS_TYPES:
            start_date = f"{year_min}-01-01"
            idx = 0
            empty_pages = 0

            print(f"\n--- {news_type} ---")

            while empty_pages < 2:
                url = (f"{NEWS_SEARCH_URL}?typ={news_type}"
                       f"&dprtmnt={NEWS_DEPT}&start={start_date}&end=&idx={idx}")
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(1500)
                except Exception as e:
                    print(f"  [ERROR] idx={idx}: {e}")
                    break

                links = await page.eval_on_selector_all(
                    'a[href*="/immigration-refugees-citizenship/news/"]',
                    """elements => elements.map(el => ({
                        url: el.href,
                        text: el.textContent.trim().substring(0, 150)
                    }))"""
                )

                new_count = 0
                for link in links:
                    url_clean = link["url"].split("?")[0].split("#")[0]
                    if url_clean.endswith("/news.html") or url_clean.endswith("/archives.html"):
                        continue
                    if url_clean not in seen:
                        seen.add(url_clean)
                        all_urls.append({"url": url_clean, "text": link["text"]})
                        new_count += 1

                page_num = idx // NEWS_PER_PAGE + 1
                print(f"  Page {page_num} (idx={idx}): +{new_count} new (total: {len(all_urls)})")

                if new_count == 0:
                    empty_pages += 1
                else:
                    empty_pages = 0

                idx += NEWS_PER_PAGE

        await browser.close()

    print(f"\nTotal unique news URLs: {len(all_urls)}")
    return all_urls


def merge_news_into_manifest(news_urls: list[dict], dry_run: bool = False) -> int:
    """Merge news URLs into manifest, prepending for priority crawling."""
    if not MANIFEST_PATH.exists():
        print(f"[ERROR] Manifest not found: {MANIFEST_PATH}")
        return 0

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing_urls = {p["url"] for p in manifest["pages"]}

    new_pages = []
    for item in news_urls:
        if item["url"] not in existing_urls:
            path = urlparse(item["url"]).path
            filename = path.lstrip("/").rstrip("/").replace(".html", "")
            new_pages.append({"url": item["url"], "filename": filename})

    print(f"\n{'='*60}")
    print(f"News URLs discovered: {len(news_urls)}")
    print(f"Already in manifest:  {len(news_urls) - len(new_pages)}")
    print(f"New to add:           {len(new_pages)}")
    print(f"{'='*60}")

    if new_pages and not dry_run:
        manifest["pages"] = new_pages + manifest["pages"]
        manifest["total_urls"] = len(manifest["pages"])
        manifest["news_updated_at"] = datetime.now().isoformat()
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[OK] Prepended {len(new_pages)} news URLs (total: {manifest['total_urls']})")
    elif dry_run:
        print("[DRY RUN] Would add:")
        for p in new_pages[:20]:
            print(f"  {p['url']}")
        if len(new_pages) > 20:
            print(f"  ... and {len(new_pages) - 20} more")

    return len(new_pages)


# ── Phase 1.5: Supplemental merge ──

def merge_supplemental_into_manifest(dry_run: bool = False) -> int:
    """Merge SUPPLEMENTAL_URLS into manifest (gc-subway nav pages BFS can't reach)."""
    if not MANIFEST_PATH.exists():
        print(f"[ERROR] Manifest not found: {MANIFEST_PATH}")
        return 0

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing_urls = {p["url"].rstrip("/") for p in manifest["pages"]}

    new_pages = []
    for url in SUPPLEMENTAL_URLS:
        url_clean = url.rstrip("/")
        if url_clean not in existing_urls:
            path = urlparse(url_clean).path
            filename = path.lstrip("/").rstrip("/").replace(".html", "")
            new_pages.append({"url": url_clean, "filename": filename})

    print(f"\n{'='*60}")
    print(f"PHASE 1.5: Supplemental URLs (gc-subway nav pages)")
    print(f"  Total supplemental: {len(SUPPLEMENTAL_URLS)}")
    print(f"  Already in manifest: {len(SUPPLEMENTAL_URLS) - len(new_pages)}")
    print(f"  New to add:          {len(new_pages)}")
    print(f"{'='*60}")

    if new_pages and not dry_run:
        manifest["pages"] = manifest["pages"] + new_pages
        manifest["total_urls"] = len(manifest["pages"])
        manifest["supplemental_updated_at"] = datetime.now().isoformat()
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[OK] Appended {len(new_pages)} supplemental URLs (total: {manifest['total_urls']})")
    elif dry_run:
        print("[DRY RUN] Would add:")
        for p in new_pages:
            print(f"  {p['url']}")

    return len(new_pages)


# ── Main ──

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover all IRCC URLs (BFS + News + Supplemental)")
    parser.add_argument("--skip-bfs", action="store_true", help="Skip BFS phase")
    parser.add_argument("--skip-news", action="store_true", help="Skip news phase")
    parser.add_argument("--skip-supplemental", action="store_true", help="Skip supplemental phase")
    parser.add_argument("--supplemental-only", action="store_true", help="Only run supplemental merge")
    parser.add_argument("--news-year-min", type=int, default=NEWS_YEAR_MIN, help="News start year")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    # Phase 1: BFS
    if not args.supplemental_only:
        if not args.skip_bfs:
            await run_bfs_discovery()
        else:
            print("[SKIP] BFS discovery")

    # Phase 1.5: Supplemental (gc-subway nav pages)
    if not args.skip_supplemental:
        merge_supplemental_into_manifest(dry_run=args.dry_run)
    else:
        print("[SKIP] Supplemental merge")

    # Phase 2: News
    if not args.supplemental_only:
        if not args.skip_news:
            print(f"\n{'='*60}")
            print(f"PHASE 2: News Discovery (>= {args.news_year_min})")
            print(f"{'='*60}")
            news = await discover_news_urls(year_min=args.news_year_min)
            merge_news_into_manifest(news, dry_run=args.dry_run)
        else:
            print("[SKIP] News discovery")

    print("\n=== Discovery complete! Now run: ===")
    print("uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/federal-ircc/manifest.json")


if __name__ == "__main__":
    asyncio.run(main())
