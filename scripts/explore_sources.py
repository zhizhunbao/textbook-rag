"""explore_sources — Crawl configured data-source websites for PDF endpoints.

Uses Playwright (headless Chromium) to render JavaScript-heavy pages,
discovers all accessible PDF links from each data source URL,
follows year-based sub-pages, scrolls for lazy-loaded content,
and generates a summary report saved to scripts/explore_sources_output.txt.

Usage:
    python scripts/explore_sources.py
    python scripts/explore_sources.py --source "ED Updates"
    python scripts/explore_sources.py --verify   # HEAD-check each PDF URL
    python scripts/explore_sources.py --headed    # Watch browser in action
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from collections import defaultdict

import httpx
from playwright.async_api import async_playwright, Page, BrowserContext


# ============================================================
# Data sources (mirrored from payload-v2/src/seed/data-sources.ts)
# ============================================================

SOURCES = [
    {
        "name": "City of Ottawa - ED Updates",
        "url": "https://ottawa.ca/en/planning-development-and-construction/housing-and-development-reports/local-economic-development-information/economic-development-update",
        "type": "url_pattern",
        "follow_year_links": True,
        # Only match economic_update PDF files (exclude election coloring pages, etc.)
        "pdf_pattern": r"economic.update.*\.pdf",
        "crawl_subpages": [
            "https://ottawa.ca/en/planning-development-and-construction/housing-and-development-reports/economic-development-update/2024",
            "https://ottawa.ca/en/planning-development-and-construction/housing-and-development-reports/economic-development-update/2023",
        ],
    },
    {
        "name": "Ottawa Real Estate Board (OREB)",
        "url": "https://www.oreb.ca/newsroom/news-releases/",
        "type": "pdf_crawl",
        "pdf_pattern": r"\.pdf",
        # PDFs are inside individual news articles (wp-content/uploads/)
        # Deep crawl: follow article links from listing pages
        "deep_crawl": {
            "article_pattern": r"oreb\.ca/newsroom/[a-z0-9-]+/$",
            "pagination_pattern": r"news-releases/page/\d+",
            "max_pages": 5,   # paginate through first 5 listing pages
            "max_articles": 20,  # visit up to 20 articles
        },
        "crawl_subpages": [
            "https://www.oreb.ca/newsroom/news-releases/page/2/",
            "https://www.oreb.ca/newsroom/news-releases/page/3/",
        ],
    },
    {
        "name": "CMHC - Housing Market Reports",
        "url": "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/market-reports/housing-market",
        "type": "pdf_crawl",
        "pdf_pattern": r"\.pdf",
        # Crawl deeper into CMHC's research ecosystem
        "crawl_subpages": [
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-research/research-reports",
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/market-reports/mortgage-market",
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/housing-market-data",
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-data/data-tables/rental-market",
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/news-releases-reports-calendar",
        ],
    },
    {
        "name": "Invest Ottawa",
        "url": "https://www.investottawa.ca/",
        "type": "pdf_crawl",
        "pdf_pattern": r"\.pdf",
        "timeout": 45_000,
        "wait_for": "domcontentloaded",
        "alt_urls": [
            "https://www.investottawa.ca/ottawa-profile/",
            "https://www.investottawa.ca/knowledge-base/",
        ],
    },
    {
        "name": "Colliers Ottawa",
        "url": "https://www.colliers.com/en-ca/research",
        "type": "pdf_crawl",
        "pdf_pattern": r"\.pdf",
        "timeout": 45_000,
        "wait_for": "domcontentloaded",
        "alt_urls": [
            "https://www.colliers.com/en-ca/research/canada",
        ],
    },
]

OUTPUT_FILE = Path(__file__).parent / "explore_sources_output.txt"


# ============================================================
# Crawl helpers (Playwright-based)
# ============================================================

def normalize_url(url: str) -> str:
    """Strip fragment and trailing slash for deduplication."""
    parsed = urlparse(url)
    # Remove fragment, normalize trailing slash
    clean = urlunparse(parsed._replace(fragment=""))
    return clean.rstrip("/")


async def scroll_to_bottom(page: Page, pause: int = 500, max_scrolls: int = 10) -> None:
    """Scroll to bottom in increments to trigger lazy-loaded content."""
    for _ in range(max_scrolls):
        prev_height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(pause)
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == prev_height:
            break


async def extract_all_links_pw(page: Page) -> list[str]:
    """Extract all href values from anchor tags via Playwright."""
    return await page.evaluate("""
        () => {
            const links = new Set();
            // Standard <a> tags
            document.querySelectorAll('a[href]').forEach(a => {
                if (a.href && a.href.startsWith('http')) links.add(a.href);
            });
            // data-href attributes (some sites use these)
            document.querySelectorAll('[data-href]').forEach(el => {
                const h = el.getAttribute('data-href');
                if (h && h.startsWith('http')) links.add(h);
            });
            // onclick handlers containing URLs (basic extraction)
            document.querySelectorAll('[onclick]').forEach(el => {
                const m = el.getAttribute('onclick').match(/https?:\\/\\/[^'"\\s)]+\\.pdf/gi);
                if (m) m.forEach(u => links.add(u));
            });
            return Array.from(links);
        }
    """)


async def extract_pdf_links_pw(page: Page) -> list[str]:
    """Extract all PDF links from the rendered page DOM via multiple strategies."""
    all_links = await extract_all_links_pw(page)
    pdf_links = set()

    for link in all_links:
        if re.search(r'\.pdf', link, re.IGNORECASE):
            pdf_links.add(normalize_url(link))

    # Also check iframes for embedded PDF viewers
    iframes = await page.evaluate("""
        () => Array.from(document.querySelectorAll('iframe[src]'))
                    .map(f => f.src)
                    .filter(s => /\\.pdf/i.test(s))
    """)
    for src in iframes:
        pdf_links.add(normalize_url(src))

    # Check for wp-content/uploads links and scan raw HTML for PDF URLs
    wp_links = await page.evaluate("""
        () => {
            const links = new Set();
            document.querySelectorAll('[href*="wp-content/uploads"], [src*="wp-content/uploads"]').forEach(el => {
                const url = el.href || el.src;
                if (url && /\\.pdf/i.test(url)) links.add(url);
            });
            const html = document.documentElement.innerHTML;
            const matches = html.match(/https?:\\/\\/[^"'\\s<>]+\\.pdf/gi);
            if (matches) matches.forEach(m => links.add(m));
            return Array.from(links);
        }
    """)
    for link in wp_links:
        pdf_links.add(normalize_url(link))

    return list(pdf_links)


async def extract_article_links(page: Page, pattern: str) -> list[str]:
    """Extract article links from a listing page matching the given regex pattern."""
    all_links = await extract_all_links_pw(page)
    regex = re.compile(pattern, re.IGNORECASE)
    seen = set()
    articles = []
    for link in all_links:
        norm = normalize_url(link)
        if norm not in seen and regex.search(norm):
            seen.add(norm)
            articles.append(link)
    return articles


def find_year_subpages(links: list[str], base_url: str) -> list[str]:
    """Find links to year-based sub-pages (e.g. /2023, /2022)."""
    parsed_base = urlparse(base_url)
    year_links = []
    seen = set()
    for link in links:
        parsed = urlparse(link)
        if parsed.netloc == parsed_base.netloc:
            if re.search(r'/(20\d{2})\b', parsed.path):
                norm = normalize_url(link)
                if norm not in seen:
                    seen.add(norm)
                    year_links.append(link)
    return year_links


async def crawl_page_pw(
    page: Page,
    url: str,
    timeout: int = 30_000,
    wait_for: str = "networkidle",
    scroll: bool = True,
) -> bool:
    """Navigate to a URL with Playwright. Returns True on success."""
    try:
        resp = await page.goto(url, timeout=timeout, wait_until=wait_for)
        if resp and resp.status >= 400:
            print(f"    ! HTTP {resp.status} for {url}")
            return False
        # Wait for dynamic content
        await page.wait_for_timeout(1500)
        # Scroll to trigger lazy loading
        if scroll:
            await scroll_to_bottom(page)
        return True
    except Exception as e:
        err_msg = str(e).split("\n")[0]  # first line only
        print(f"    ! Failed: {err_msg}")
        return False


async def verify_pdf(
    client: httpx.AsyncClient, url: str
) -> tuple[str, bool, int]:
    """HEAD-check a PDF URL. Returns (url, accessible, status_code)."""
    try:
        resp = await client.head(url, timeout=15.0, follow_redirects=True)
        return (url, resp.status_code < 400, resp.status_code)
    except Exception:
        return (url, False, 0)


# ============================================================
# Main exploration logic
# ============================================================

async def explore_source(
    context: BrowserContext,
    source: dict,
    verify: bool = False,
) -> dict:
    """Explore a single data source and return discovery results."""
    name = source["name"]
    url = source["url"]
    pdf_pattern = source.get("pdf_pattern", r"\.pdf")
    follow_years = source.get("follow_year_links", False)
    alt_urls = source.get("alt_urls", [])
    crawl_subpages = source.get("crawl_subpages", [])
    src_timeout = source.get("timeout", 30_000)
    src_wait = source.get("wait_for", "networkidle")

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"   URL: {url}")
    print(f"{'='*60}")

    all_pdfs: list[str] = []
    pages_visited: set[str] = set()

    page = await context.new_page()

    try:
        # -- 1. Fetch main page --
        success = await crawl_page_pw(page, url, timeout=src_timeout, wait_for=src_wait)
        if not success:
            for alt in alt_urls:
                print(f"   -> Trying alt URL: {alt}")
                success = await crawl_page_pw(page, alt, timeout=src_timeout, wait_for=src_wait)
                if success:
                    url = alt
                    break

        if not success:
            return {
                "name": name,
                "url": url,
                "error": "Failed to fetch main page (and all alt URLs)",
                "pdfs": [],
            }

        pages_visited.add(normalize_url(url))
        pdfs = await extract_pdf_links_pw(page)
        all_pdfs.extend(pdfs)
        print(f"   Main page: {len(pdfs)} PDF links found")

        # -- 2. Follow year sub-pages if configured --
        if follow_years:
            all_links = await extract_all_links_pw(page)
            year_links = find_year_subpages(all_links, url)
            print(f"   Year sub-pages found: {len(year_links)}")
            for year_url in year_links[:10]:
                norm = normalize_url(year_url)
                if norm in pages_visited:
                    continue
                print(f"   -> Year page: {year_url.split('#')[0]}")
                ok = await crawl_page_pw(page, year_url, timeout=src_timeout, wait_for=src_wait)
                if ok:
                    pages_visited.add(norm)
                    year_pdfs = await extract_pdf_links_pw(page)
                    new_pdfs = [p for p in year_pdfs if p not in set(all_pdfs)]
                    all_pdfs.extend(new_pdfs)
                    print(f"      Found {len(new_pdfs)} new PDFs")

        # -- 3. Deep crawl: follow article links from listing pages --
        deep_cfg = source.get("deep_crawl")
        if deep_cfg:
            article_pattern = deep_cfg["article_pattern"]
            max_articles = deep_cfg.get("max_articles", 15)
            article_urls: list[str] = []

            # Collect article links from main page
            articles_on_page = await extract_article_links(page, article_pattern)
            article_urls.extend(articles_on_page)

            # Also collect from sub-pages (pagination)
            for sub_url in crawl_subpages:
                norm = normalize_url(sub_url)
                if norm in pages_visited:
                    continue
                print(f"   -> Listing page: {sub_url}")
                ok = await crawl_page_pw(page, sub_url, timeout=src_timeout, wait_for=src_wait)
                if ok:
                    pages_visited.add(norm)
                    more_articles = await extract_article_links(page, article_pattern)
                    article_urls.extend(more_articles)
                    # Also check for direct PDFs on listing page
                    listing_pdfs = await extract_pdf_links_pw(page)
                    new_listing = [p for p in listing_pdfs if p not in set(all_pdfs)]
                    all_pdfs.extend(new_listing)

            # Deduplicate article URLs
            unique_articles = list(dict.fromkeys(
                normalize_url(u) for u in article_urls
            ))
            print(f"   Found {len(unique_articles)} article links (visiting up to {max_articles})")

            for art_url in unique_articles[:max_articles]:
                if art_url in pages_visited:
                    continue
                art_name = art_url.rstrip('/').rsplit('/', 1)[-1][:50]
                print(f"   -> Article: {art_name}")
                ok = await crawl_page_pw(page, art_url, timeout=src_timeout, wait_for=src_wait)
                if ok:
                    pages_visited.add(art_url)
                    art_pdfs = await extract_pdf_links_pw(page)
                    new_pdfs = [p for p in art_pdfs if p not in set(all_pdfs)]
                    all_pdfs.extend(new_pdfs)
                    if new_pdfs:
                        print(f"      Found {len(new_pdfs)} PDFs!")
        else:
            # -- 3b. Crawl explicit sub-pages (non-deep mode) --
            for sub_url in crawl_subpages:
                norm = normalize_url(sub_url)
                if norm in pages_visited:
                    continue
                print(f"   -> Sub-page: {sub_url}")
                ok = await crawl_page_pw(page, sub_url, timeout=src_timeout, wait_for=src_wait)
                if ok:
                    pages_visited.add(norm)
                    sub_pdfs = await extract_pdf_links_pw(page)
                    new_pdfs = [p for p in sub_pdfs if p not in set(all_pdfs)]
                    all_pdfs.extend(new_pdfs)
                    if new_pdfs:
                        print(f"      Found {len(new_pdfs)} new PDFs")
                    else:
                        print(f"      No new PDFs")

        # -- 4. Check alt URLs for additional discovery --
        for alt in alt_urls:
            norm = normalize_url(alt)
            if norm in pages_visited:
                continue
            print(f"   -> Alt page: {alt}")
            ok = await crawl_page_pw(page, alt, timeout=src_timeout, wait_for=src_wait)
            if ok:
                pages_visited.add(norm)
                alt_pdfs = await extract_pdf_links_pw(page)
                new_pdfs = [p for p in alt_pdfs if p not in set(all_pdfs)]
                all_pdfs.extend(new_pdfs)
                if new_pdfs:
                    print(f"      Found {len(new_pdfs)} new PDFs")

        # -- 5. Deduplicate and filter --
        unique_pdfs = list(dict.fromkeys(all_pdfs))
        if pdf_pattern:
            regex = re.compile(pdf_pattern, re.IGNORECASE)
            filtered = [p for p in unique_pdfs if regex.search(p)]
        else:
            filtered = unique_pdfs

        # -- 6. Optionally verify PDF accessibility --
        verified = {}
        if verify and filtered:
            print(f"\n   Verifying {len(filtered)} PDFs...")
            async with httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0"},
                follow_redirects=True,
            ) as client:
                tasks = [verify_pdf(client, u) for u in filtered]
                results = await asyncio.gather(*tasks)
                for pdf_url, ok, status in results:
                    verified[pdf_url] = (ok, status)
                    symbol = "OK" if ok else "FAIL"
                    print(f"   [{symbol} {status}] {pdf_url.split('/')[-1]}")

    finally:
        await page.close()

    return {
        "name": name,
        "url": url,
        "pages_visited": list(pages_visited),
        "total_links": len(unique_pdfs),
        "filtered_count": len(filtered),
        "pdfs": filtered,
        "all_pdfs": unique_pdfs,
        "verified": verified,
    }


def format_report(results: list[dict]) -> str:
    """Generate a formatted summary report string."""
    lines: list[str] = []
    lines.append(f"\n{'='*60}")
    lines.append(" EXPLORATION REPORT")
    lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"{'='*60}")

    total_pdfs = 0
    for r in results:
        name = r["name"]
        if "error" in r:
            lines.append(f"\n[FAIL] {name}: {r['error']}")
            continue

        count = r["filtered_count"]
        total_pdfs += count
        all_count = r["total_links"]
        pages = len(r.get("pages_visited", []))

        lines.append(f"\n[SOURCE] {name}")
        lines.append(f"   Pages crawled: {pages}")
        lines.append(f"   Total PDF links (all): {all_count}")
        lines.append(f"   Matching pattern: {count}")

        if r.get("verified"):
            accessible = sum(1 for ok, _ in r["verified"].values() if ok)
            lines.append(f"   Verified accessible: {accessible}/{count}")

        # Group PDFs by domain
        by_domain: dict[str, list[str]] = defaultdict(list)
        for pdf in r["pdfs"]:
            domain = urlparse(pdf).netloc
            by_domain[domain].append(pdf)

        for domain, pdfs in sorted(by_domain.items()):
            lines.append(f"\n   [{domain}] ({len(pdfs)} PDFs):")
            for pdf in sorted(pdfs)[:30]:
                fname = pdf.rsplit("/", 1)[-1]
                lines.append(f"      - {fname}")
                lines.append(f"        {pdf}")
            if len(pdfs) > 30:
                lines.append(f"      ... and {len(pdfs) - 30} more")

    lines.append(f"\n{'_'*60}")
    lines.append(f"Total PDFs discovered: {total_pdfs}")
    lines.append(f"{'_'*60}")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Explore data source websites for PDF endpoints (Playwright)"
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help='Filter by source name (partial match), e.g. "ED Updates"'
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="HEAD-check each discovered PDF URL"
    )
    parser.add_argument(
        "--headed", action="store_true",
        help="Run browser in headed mode (visible window)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: scripts/explore_sources_output.txt)"
    )
    args = parser.parse_args()

    sources = SOURCES
    if args.source:
        sources = [
            s for s in SOURCES
            if args.source.lower() in s["name"].lower()
        ]
        if not sources:
            print(f"No source matching '{args.source}'. Available:")
            for s in SOURCES:
                print(f"  - {s['name']}")
            sys.exit(1)

    print("PDF Source Explorer (Playwright)")
    print(f"   Scanning {len(sources)} source(s)...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            # Accept cookies / dismiss dialogs
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        results = []
        for source in sources:
            result = await explore_source(context, source, verify=args.verify)
            results.append(result)

        await context.close()
        await browser.close()

    # Print and save report
    report = format_report(results)
    print(report)

    out_path = Path(args.output) if args.output else OUTPUT_FILE
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved to: {out_path}")

    # Also save raw JSON for programmatic consumption
    json_path = out_path.with_suffix(".json")
    json_data = []
    for r in results:
        entry = {k: v for k, v in r.items() if k != "verified"}
        if r.get("verified"):
            entry["verified"] = {
                url: {"accessible": ok, "status": status}
                for url, (ok, status) in r["verified"].items()
            }
        json_data.append(entry)
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON data saved to: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
