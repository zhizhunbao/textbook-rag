"""sources — Web data-source discovery endpoint.

Crawls a given URL, extracts PDF links, and returns discovered documents.
Used by the frontend Sources tab for one-click PDF discovery & import.

Supports two discovery strategies:
  - pdf_crawl: HTTP GET the page, parse <a href="*.pdf"> links
  - url_pattern: Generate PDF URLs from a known pattern (e.g. ED Updates)
"""
# reload-trigger

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sources"])


# ── Request / Response schemas ───────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    """Parameters for PDF discovery from a web source."""
    url: str = Field(..., description="Base URL to crawl for PDF links")
    pdf_pattern: Optional[str] = Field(
        None, description="Regex pattern to filter PDF filenames (optional)"
    )
    type: str = Field(
        "pdf_crawl", description="Discovery type: pdf_crawl | url_pattern"
    )
    known_book_ids: list[str] = Field(
        default_factory=list,
        description="Engine book_id strings already in the system (for dedup)"
    )


class DiscoveredPdf(BaseModel):
    """A single discovered PDF document."""
    url: str
    filename: str
    title: str
    already_imported: bool = False
    unavailable: bool = False  # True if HEAD check returned 404


class DiscoverResponse(BaseModel):
    """Result of a discovery crawl."""
    success: bool
    source_url: str
    total_found: int = 0
    new_count: int = 0
    existing_count: int = 0
    pdfs: list[DiscoveredPdf] = []
    error: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_pdf_links(html: str, base_url: str) -> list[str]:
    """Extract all href values ending in .pdf from HTML content."""
    # Match <a> tags with href containing .pdf
    pattern = r'href=["\']([^"\']*\.pdf)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    # Resolve relative URLs
    return list({urljoin(base_url, m) for m in matches})


def _filename_from_url(url: str) -> str:
    """Extract filename from a PDF URL."""
    path = urlparse(url).path
    return path.rsplit("/", 1)[-1] if "/" in path else path


def _title_from_filename(filename: str) -> str:
    """Generate a human-readable title from a PDF filename."""
    name = filename.rsplit(".", 1)[0]  # remove .pdf
    # Replace underscores/hyphens with spaces, title-case
    name = re.sub(r"[_-]+", " ", name)
    return name.strip().title()


def _is_already_imported(
    filename: str, url: str, known_ids: list[str]
) -> bool:
    """Check if a PDF is already imported based on known engine book IDs.

    Handles naming mismatches like:
      engineBookId='ed_update_q1_2022' vs filename='economic_update_q1_2022_en.pdf'
    Also matches when the full URL was stored as engineBookId (URL-imported books).
    """
    name_lower = filename.rsplit(".", 1)[0].lower()
    url_lower = url.lower()

    # Extract quarter+year token like "q1_2022" from the filename
    qy_match = re.search(r"q[1-4][_\s]?\d{4}", name_lower)
    qy_token = qy_match.group(0).replace(" ", "_") if qy_match else None

    for kid in known_ids:
        kid_lower = kid.lower()
        # Direct match: engineBookId equals filename stem
        if kid_lower == name_lower or kid_lower in name_lower or name_lower in kid_lower:
            return True
        # URL match: engineBookId is the full URL (URL-imported books)
        if kid_lower == url_lower:
            return True
        # Quarter+year match: both contain the same qN_YYYY token
        if qy_token:
            kid_qy = re.search(r"q[1-4][_\s]?\d{4}", kid_lower)
            if kid_qy and kid_qy.group(0).replace(" ", "_") == qy_token:
                return True
    return False


# ── ED Updates URL pattern generator ────────────────────────────────────────

ED_UPDATE_BASE = (
    "https://documents.ottawa.ca/sites/default/files/"
)

def _generate_ed_update_urls() -> list[str]:
    """Generate known ED Update PDF URLs from Q1 2022 to Q4 2025."""
    urls = []
    for year in range(2022, 2026):
        for quarter in range(1, 5):
            url = f"{ED_UPDATE_BASE}economic_update_q{quarter}_{year}_en.pdf"
            urls.append(url)
    return urls


# ── OREB URL pattern generator ──────────────────────────────────────────────

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Archive base (2012-2015): filenames are irregular, so hardcode them
_OREB_ARCHIVE_BASE = "https://www.oreb.ca/wp-content/themes/OREB/uploads/news_archive"
_OREB_ARCHIVE_PDFS = [
    # 2012 — different naming conventions
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/January2012NewsRelease.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/MediaNewsRelease_StatsFeb2012.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/March2012NewsRelease_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/April2012NewsRelease_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/May2012NewsRelease_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/NewsReleaseJune2012_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/July2012NewsRelease_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/August2012NewsRelease_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/September2012NewsRelease_Stats.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/OREBNewsRelease-October2012.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/OREBNewsRelease-November2012.pdf",
    f"{_OREB_ARCHIVE_BASE}/2012-ALL/OREBNewsRelease-December2012.pdf",
    # 2013-2015 — consistent OREBNewsRelease-{Month}{Year}.pdf
    *[
        f"{_OREB_ARCHIVE_BASE}/{year}-ALL/OREBNewsRelease-{month}{year}.pdf"
        for year in range(2013, 2016)
        for month in _MONTHS
    ],
    # 2014 March has an UPDATED version
    f"{_OREB_ARCHIVE_BASE}/2014-ALL/OREBNewsRelease-March2014-UPDATED.pdf",
]

# Recent (2025-2026): predictable pattern
_OREB_RECENT_BASE = "https://www.oreb.ca/wp-content/uploads"

def _generate_oreb_urls() -> dict[str, list[str]]:
    """Generate all known OREB PDF URLs.
    
    Returns dict with:
      - 'known': archive URLs (confirmed, skip HEAD check)
      - 'candidates': recent URLs (need HEAD verification)
    """
    from datetime import datetime

    known = list(_OREB_ARCHIVE_PDFS)  # 2012-2015, confirmed to exist
    candidates = []

    now = datetime.now()
    # Report for month M is published in month M+1.
    # Only generate up to current month (which covers last month's data).
    cutoff_year = now.year
    cutoff_month = now.month  # e.g. April 2026 → generate up to March 2026 data

    # Generate recent monthly updates from May 2025 to cutoff
    # Pattern: /uploads/YYYY/MM/OREB_MarketUpdate_HLP_{Month}{YY}.pdf
    year, month = 2025, 5
    while (year, month) < (cutoff_year, cutoff_month):
        yy = year % 100
        month_name = _MONTHS[month - 1]
        # November 2025 is hosted on members.oreb.ca (added separately below)
        if (year, month) == (2025, 11):
            month += 1
            continue
        # Upload date is the next month
        upload_year = year if month < 12 else year + 1
        upload_month = month + 1 if month < 12 else 1
        url = f"{_OREB_RECENT_BASE}/{upload_year}/{upload_month:02d}/OREB_MarketUpdate_HLP_{month_name}{yy}.pdf"
        candidates.append(url)
        # Advance
        month += 1
        if month > 12:
            month = 1
            year += 1

    # Special: March 2025 highlight report (different naming)
    candidates.append(f"{_OREB_RECENT_BASE}/2026/04/OttawaResidentialMarketActivity-MLSRHPI-HIGHLIGHT__March25.pdf")
    # November 2025 was on members subdomain
    candidates.append("https://members.oreb.ca/wp-content/uploads/2025/12/OREB_MarketUpdate_HLP_November25.pdf")

    return {"known": known, "candidates": candidates}


# ── Playwright-based deep crawl ─────────────────────────────────────────────

import asyncio

_PDF_EXTRACT_JS = """() => {
    const links = new Set();
    document.querySelectorAll('a[href]').forEach(a => {
        if (a.href && /\\.pdf/i.test(a.href)) links.add(a.href);
    });
    document.querySelectorAll('[data-href]').forEach(el => {
        const h = el.getAttribute('data-href');
        if (h && /\\.pdf/i.test(h)) links.add(h);
    });
    const html = document.documentElement.innerHTML;
    const matches = html.match(/https?:\\/\\/[^"'\\s<>]+\\.pdf/gi);
    if (matches) matches.forEach(m => links.add(m));
    return Array.from(links);
}"""

_ALL_LINKS_JS = """() => {
    return Array.from(document.querySelectorAll('a[href]'))
        .map(a => a.href)
        .filter(h => h && h.startsWith('http'));
}"""


def _playwright_crawl_sync(url: str, max_subpages: int = 30) -> list[str]:
    """Synchronous Playwright crawl (runs in a separate thread).
    
    Uses sync API to avoid Windows event loop subprocess issues.
    """
    from playwright.sync_api import sync_playwright

    pdf_links: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            # Load main page
            logger.info("Playwright crawl: %s", url)
            resp = page.goto(url, timeout=30_000, wait_until="networkidle")
            if resp and resp.status >= 400:
                logger.warning("HTTP %d for %s", resp.status, url)
                return []

            page.wait_for_timeout(1500)
            # Scroll to trigger lazy loading
            for _ in range(5):
                prev_h = page.evaluate("document.body.scrollHeight")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(500)
                if page.evaluate("document.body.scrollHeight") == prev_h:
                    break

            # Extract PDF links from the DOM
            found = page.evaluate(_PDF_EXTRACT_JS)
            pdf_links.update(found)
            logger.info("Main page: %d PDFs found", len(found))

            # Load fixed crawl config for this domain
            crawl_cfg = _get_crawl_config(url)
            fixed_subpages = crawl_cfg.get("subpages", [])
            article_pattern = crawl_cfg.get("article_pattern", "")
            cfg_max_articles = crawl_cfg.get("max_articles", max_subpages)

            # Collect all page links for dynamic discovery
            all_links = page.evaluate(_ALL_LINKS_JS)

            # Classify links
            parsed_base = urlparse(url)
            article_urls: list[str] = []
            seen = {url.rstrip("/")}
            for fp in fixed_subpages:
                seen.add(fp.rstrip("/"))

            _SKIP_SEGMENTS = {
                "/tag/", "/category/", "/author/", "/login", "/wp-admin",
                "/feed", "/cart", "/checkout", "/account", "/contact",
                "/wp-json/", "/xmlrpc", ".css", ".js", ".png", ".jpg",
                "/privacy", "/terms", "/cookie", "/search",
            }

            def _collect_articles(links: list[str]) -> None:
                pat = re.compile(article_pattern, re.IGNORECASE) if article_pattern else None
                for link in links:
                    parsed = urlparse(link)
                    if parsed.netloc != parsed_base.netloc:
                        continue
                    norm = link.rstrip("/").split("#")[0].split("?")[0]
                    if norm in seen:
                        continue
                    lower = norm.lower()
                    if any(skip in lower for skip in _SKIP_SEGMENTS):
                        continue
                    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                    if len(path_parts) < 2:
                        continue
                    seen.add(norm)
                    # If article pattern is set, only collect matching links
                    if pat:
                        if pat.search(norm):
                            article_urls.append(link)
                    else:
                        article_urls.append(link)

            _collect_articles(all_links)

            # Phase 1: Crawl fixed sub-pages (pagination, archive, etc.)
            logger.info("Crawling %d fixed sub-pages", len(fixed_subpages))
            for sub_url in fixed_subpages:
                try:
                    sub_resp = page.goto(sub_url, timeout=20_000, wait_until="domcontentloaded")
                    if sub_resp and sub_resp.status >= 400:
                        logger.debug("  Skip %s (HTTP %d)", sub_url, sub_resp.status)
                        continue
                    page.wait_for_timeout(1000)
                    # Scroll for lazy content
                    for _ in range(3):
                        prev_h = page.evaluate("document.body.scrollHeight")
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(300)
                        if page.evaluate("document.body.scrollHeight") == prev_h:
                            break
                    sub_found = page.evaluate(_PDF_EXTRACT_JS)
                    new_pdfs = [p for p in sub_found if p not in pdf_links]
                    pdf_links.update(sub_found)
                    if new_pdfs:
                        logger.info("  Fixed page %s: %d new PDFs", sub_url.rsplit("/", 1)[-1][:30], len(new_pdfs))
                    # Discover article links from this page
                    more_links = page.evaluate(_ALL_LINKS_JS)
                    _collect_articles(more_links)
                except Exception as e:
                    logger.debug("Fixed page failed %s: %s", sub_url, str(e)[:100])

            # Phase 2: Crawl discovered article/content pages
            effective_max = cfg_max_articles
            logger.info("Crawling %d articles (max %d)", len(article_urls), effective_max)
            for art_url in article_urls[:effective_max]:
                try:
                    art_resp = page.goto(art_url, timeout=20_000, wait_until="domcontentloaded")
                    if art_resp and art_resp.status >= 400:
                        continue
                    page.wait_for_timeout(1000)
                    art_found = page.evaluate(_PDF_EXTRACT_JS)
                    new_pdfs = [p for p in art_found if p not in pdf_links]
                    pdf_links.update(art_found)
                    if new_pdfs:
                        logger.info("  Article %s: %d new PDFs", art_url.rsplit("/", 1)[-1][:40], len(new_pdfs))
                    more_links = page.evaluate(_ALL_LINKS_JS)
                    _collect_articles(more_links)
                except Exception as e:
                    logger.debug("Article failed %s: %s", art_url, str(e)[:100])

        finally:
            page.close()
            context.close()
            browser.close()

    logger.info("Playwright total: %d PDFs", len(pdf_links))
    return list(pdf_links)


async def _playwright_crawl(url: str, max_subpages: int = 30) -> list[str]:
    """Async wrapper: runs sync Playwright in a thread to avoid event loop issues."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        logger.warning("Playwright not installed, falling back to httpx")
        return await _httpx_crawl(url)

    try:
        return await asyncio.to_thread(_playwright_crawl_sync, url, max_subpages)
    except Exception as e:
        logger.error("Playwright crawl failed: %s", e)
        return await _httpx_crawl(url)


async def _httpx_crawl(url: str) -> list[str]:
    """Fallback: simple httpx-based crawl for PDF links."""
    logger.info("httpx crawl fallback: %s", url)
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; OttawaEcDevBot/1.0)"},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return _extract_pdf_links(resp.text, url)


# ── Per-source crawl config ─────────────────────────────────────────────────
# Fixed sub-pages for known data sources that require deep crawling.
# Keyed by domain → list of sub-page URLs to visit.

_SOURCE_CRAWL_CONFIG: dict[str, dict] = {
    "www.oreb.ca": {
        "subpages": [
            "https://www.oreb.ca/newsroom/news-releases/page/2/",
            "https://www.oreb.ca/newsroom/news-releases/page/3/",
            "https://www.oreb.ca/newsroom/news-releases/page/4/",
            "https://www.oreb.ca/newsroom/news-releases/page/5/",
            "https://www.oreb.ca/newsroom/news-archive",
            "https://www.oreb.ca/newsroom/industry-news",
        ],
        "article_pattern": r"oreb\.ca/newsroom/[a-z0-9-]+/?$",
        "max_articles": 25,
    },
    "www.cmhc-schl.gc.ca": {
        "subpages": [
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/market-reports/housing-market",
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-research/research-reports",
            "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/market-reports/mortgage-market",
        ],
        "max_articles": 10,
    },
    "www.colliers.com": {
        "subpages": [
            "https://www.colliers.com/en-ca/research",
            "https://www.colliers.com/en-ca/research/canada",
        ],
        "max_articles": 10,
    },
    "www.investottawa.ca": {
        "subpages": [
            "https://www.investottawa.ca/ottawa-profile/",
            "https://www.investottawa.ca/knowledge-base/",
        ],
        "max_articles": 10,
    },
}

def _get_crawl_config(url: str) -> dict:
    """Get crawl config for a source URL by domain."""
    domain = urlparse(url).netloc
    return _SOURCE_CRAWL_CONFIG.get(domain, {})


# ── Route ────────────────────────────────────────────────────────────────────

@router.post("/sources/discover", response_model=DiscoverResponse)
async def discover_pdfs(req: DiscoverRequest) -> DiscoverResponse:
    """Discover PDF documents from a web source URL."""
    try:
        pdf_urls: list[str] = []

        # Strategy 1: Known URL pattern (ED Updates, OREB)
        candidate_urls: list[str] = []
        known_urls: list[str] = []  # confirmed URLs (skip HEAD check)
        domain = urlparse(req.url).netloc.lower()

        if req.type == "url_pattern" or "ottawa.ca" in req.url.lower():
            logger.info("Using ED Updates URL pattern for: %s", req.url)
            candidate_urls = _generate_ed_update_urls()
        elif "oreb.ca" in domain:
            logger.info("Using OREB URL pattern for: %s", req.url)
            oreb_result = _generate_oreb_urls()
            known_urls = oreb_result["known"]
            candidate_urls = oreb_result["candidates"]

        # Add confirmed URLs directly (no HEAD check needed)
        if known_urls:
            pdf_urls.extend(known_urls)
            logger.info("Added %d known/confirmed PDFs", len(known_urls))

        if candidate_urls:
            # Verify candidate URLs with HEAD requests — mark 404s as unavailable
            logger.info("Verifying %d candidate URLs...", len(candidate_urls))
            unavailable_urls: set[str] = set()
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; OttawaEcDevBot/1.0; "
                        "+https://ottawa.ca)"
                    )
                },
            ) as client:
                for url in candidate_urls:
                    try:
                        head_resp = await client.head(url)
                        if head_resp.status_code == 200:
                            pdf_urls.append(url)
                        else:
                            pdf_urls.append(url)
                            unavailable_urls.add(url)
                            logger.debug("Unavailable: %s (HTTP %d)", url, head_resp.status_code)
                    except Exception:
                        pdf_urls.append(url)
                        unavailable_urls.add(url)
                        logger.debug("Unavailable: %s (unreachable)", url)
            logger.info("Verified: %d available, %d unavailable", len(candidate_urls) - len(unavailable_urls), len(unavailable_urls))

        # Strategy 2: Playwright-based crawl (fallback for unknown sources)
        if not pdf_urls:
            pdf_urls = await _playwright_crawl(req.url)

        # Apply optional filename filter
        if req.pdf_pattern:
            regex = re.compile(req.pdf_pattern, re.IGNORECASE)
            pdf_urls = [u for u in pdf_urls if regex.search(u)]

        # Build result list with dedup check (newest first)
        _MONTHS = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }

        def _sort_key(url: str) -> tuple:
            """Extract date for descending sort; newest first."""
            fname = url.rsplit("/", 1)[-1].lower()
            # Quarterly: q1_2022, q3_2024
            m = re.search(r'q(\d)[_\s]?(\d{4})', fname, re.IGNORECASE)
            if m:
                return (-int(m.group(2)), -int(m.group(1)))
            # Monthly with 4-digit year: July2014, March2013
            m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})', fname, re.IGNORECASE)
            if m:
                return (-int(m.group(2)), -_MONTHS.get(m.group(1).lower(), 0))
            # Monthly with 2-digit year: _July25.pdf, _March25.pdf
            m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{2})(?:\.pdf|$)', fname, re.IGNORECASE)
            if m:
                yr = int(m.group(2))
                full_year = 2000 + yr if yr < 50 else 1900 + yr
                return (-full_year, -_MONTHS.get(m.group(1).lower(), 0))
            # Upload path year: /uploads/2026/04/
            m = re.search(r'/uploads/(\d{4})/(\d{2})/', url)
            if m:
                return (-int(m.group(1)), -int(m.group(2)))
            return (0, 0)  # unknown dates go last

        pdfs: list[DiscoveredPdf] = []
        for url in sorted(pdf_urls, key=_sort_key):
            fname = _filename_from_url(url)
            imported = _is_already_imported(
                fname, url, req.known_book_ids
            )
            is_unavailable = url in unavailable_urls if 'unavailable_urls' in dir() else False
            pdfs.append(
                DiscoveredPdf(
                    url=url,
                    filename=fname,
                    title=_title_from_filename(fname),
                    already_imported=imported,
                    unavailable=is_unavailable,
                )
            )

        new_count = sum(1 for p in pdfs if not p.already_imported and not p.unavailable)
        existing_count = sum(1 for p in pdfs if p.already_imported)

        return DiscoverResponse(
            success=True,
            source_url=req.url,
            total_found=len(pdfs),
            new_count=new_count,
            existing_count=existing_count,
            pdfs=pdfs,
        )

    except httpx.HTTPStatusError as exc:
        msg = f"HTTP {exc.response.status_code} fetching {req.url}"
        logger.warning(msg)
        return DiscoverResponse(
            success=False, source_url=req.url, error=msg
        )
    except Exception as exc:
        logger.exception("Discovery failed for %s", req.url)
        return DiscoverResponse(
            success=False, source_url=req.url, error=str(exc)
        )


# ── Download PDF endpoint ────────────────────────────────────────────────────

class DownloadPdfRequest(BaseModel):
    """Request to download a PDF from URL to local storage."""
    url: str = Field(..., description="PDF URL to download")
    category: str = Field("ecdev", description="Category subdirectory (e.g. ecdev, textbook)")
    filename: str | None = Field(None, description="Override filename (default: derived from URL)")


class DownloadPdfResponse(BaseModel):
    """Result of a PDF download."""
    success: bool
    path: str = ""
    filename: str = ""
    size_bytes: int = 0
    error: str | None = None


@router.post("/sources/download-pdf", response_model=DownloadPdfResponse)
async def download_pdf(req: DownloadPdfRequest) -> DownloadPdfResponse:
    """Download a PDF from a URL and save to data/raw_pdfs/{category}/."""
    from engine_v2.settings import DATA_DIR

    try:
        # Derive filename from URL if not provided
        filename = req.filename or _filename_from_url(req.url)
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        # Ensure target directory exists
        target_dir = DATA_DIR / "raw_pdfs" / req.category
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename

        # Skip if already downloaded
        if target_path.exists() and target_path.stat().st_size > 0:
            logger.info("PDF already exists at {}, skipping download", target_path)
            return DownloadPdfResponse(
                success=True,
                path=str(target_path),
                filename=filename,
                size_bytes=target_path.stat().st_size,
            )

        # Download the PDF
        logger.info("Downloading PDF: {} → {}", req.url, target_path)
        async with httpx.AsyncClient(
            timeout=120.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; OttawaEcDevBot/1.0; "
                    "+https://ottawa.ca)"
                )
            },
        ) as client:
            resp = await client.get(req.url)
            resp.raise_for_status()

            # Verify it looks like a PDF
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type and not resp.content[:5] == b"%PDF-":
                return DownloadPdfResponse(
                    success=False,
                    error=f"URL did not return a PDF (content-type: {content_type})",
                )

            # Write to disk
            target_path.write_bytes(resp.content)

        size = target_path.stat().st_size
        logger.info("Downloaded {} bytes → {}", size, target_path)

        return DownloadPdfResponse(
            success=True,
            path=str(target_path),
            filename=filename,
            size_bytes=size,
        )

    except httpx.HTTPStatusError as exc:
        msg = f"HTTP {exc.response.status_code} downloading {req.url}"
        logger.warning(msg)
        return DownloadPdfResponse(success=False, error=msg)
    except Exception as exc:
        logger.exception("PDF download failed for %s", req.url)
        return DownloadPdfResponse(success=False, error=str(exc))

