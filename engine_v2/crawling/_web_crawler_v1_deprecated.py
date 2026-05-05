"""web_crawler — Two-phase URL discovery + full-page PDF archival.

Pipeline:
    Phase 1: discover_urls() — BFS via crawl4ai → manifest.json
    Phase 2: save_pdfs_from_manifest() — Playwright page.pdf() per URL

Output structure:
    data/crawled_web/{persona}/
        manifest.json        — URL index with titles and filenames
        express-entry.pdf    — meaningful filenames from URL path
        eligibility.pdf
        ...

Downstream: MinerU processes PDFs → LlamaIndex Documents → ChromaDB.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger

# ── Windows fix: run Playwright in a dedicated thread with ProactorEventLoop ─
_CRAWL_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="crawl4ai")


def _run_in_proactor(coro):
    """Run an async coroutine in a fresh ProactorEventLoop on a separate thread."""
    def _thread_target():
        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    future = _CRAWL_EXECUTOR.submit(_thread_target)
    return future


# ── Default output directory ─────────────────────────────────────────────────
_DEFAULT_OUTPUT_DIR = Path("data/crawled_web")


@dataclass
class CrawlResult:
    """Result from processing a single URL."""
    url: str
    filename: str = ""
    pdf_path: str = ""
    title: str = ""
    success: bool = True
    error: str | None = None
    file_size: int = 0


MAX_SEGMENT_LEN = 50   # Max chars per path segment


def _url_to_relpath(url: str) -> str:
    """Convert URL path into a relative directory path that mirrors the website.

    Faithfully preserves the full URL hierarchy so the local archive
    matches the original site structure exactly.

    Examples:
        .../en/immigration-refugees-citizenship/services/study-canada.html
            → en/immigration-refugees-citizenship/services/study-canada
        .../en/immigration-refugees-citizenship/corporate/publications-manuals/ops.html
            → en/immigration-refugees-citizenship/corporate/publications-manuals/ops
    """
    import hashlib

    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Strip .html etc from last segment
    path = re.sub(r"\.(html?|asp|php)$", "", path, flags=re.IGNORECASE)

    if not path:
        return "index"

    # Clean each segment, truncate if too long
    segments = path.split("/")
    clean_segments = []
    for seg in segments:
        seg = re.sub(r"[^\w\-]", "-", seg).strip("-")
        if not seg:
            continue
        if len(seg) > MAX_SEGMENT_LEN:
            hash_suffix = hashlib.md5(seg.encode()).hexdigest()[:8]
            prefix_len = MAX_SEGMENT_LEN - 9
            seg = f"{seg[:prefix_len]}-{hash_suffix}"
        clean_segments.append(seg)

    return "/".join(clean_segments) if clean_segments else "index"


def _url_to_filename(url: str) -> str:
    """Legacy flat filename extractor (for backward compat)."""
    return _url_to_relpath(url).replace("/", "--")


def _normalize_url(url: str) -> str:
    """Strip query params and fragments for deduplication."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Phase 1: URL Discovery → manifest.json                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def discover_urls(
    seed_url: str,
    *,
    persona_slug: str = "general",
    max_depth: int = 2,
    max_pages: int = 20,
    headless: bool = True,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    url_filter: Any | None = None,
) -> Path:
    """Discover same-domain sub-page URLs via BFS and save manifest.json.

    Args:
        url_filter: Optional callable(url: str) -> bool.
                    Return True to KEEP the URL, False to skip.
                    Applied after standard scope/language checks.

    Returns:
        Path to the saved manifest.json file.
    """
    if sys.platform == "win32":
        loop = asyncio.get_event_loop()
        future = _run_in_proactor(
            _discover_urls_impl(
                seed_url, persona_slug=persona_slug,
                max_depth=max_depth, max_pages=max_pages,
                headless=headless, output_dir=output_dir,
                url_filter=url_filter,
            )
        )
        return await loop.run_in_executor(None, future.result)
    else:
        return await _discover_urls_impl(
            seed_url, persona_slug=persona_slug,
            max_depth=max_depth, max_pages=max_pages,
            headless=headless, output_dir=output_dir,
            url_filter=url_filter,
        )


async def _discover_urls_impl(
    seed_url: str,
    *,
    persona_slug: str = "general",
    max_depth: int = 2,
    max_pages: int = 20,
    headless: bool = True,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
    url_filter: Any | None = None,
) -> Path:
    """Internal: BFS URL discovery → manifest.json."""
    try:
        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
    except ImportError:
        logger.error("crawl4ai not installed")
        return _write_manifest(
            [{"url": seed_url, "filename": _url_to_filename(seed_url)}],
            persona_slug, seed_url, output_dir,
        )

    logger.info("=" * 60)
    logger.info("PHASE 1: URL Discovery")
    logger.info("  seed: {}", seed_url)
    logger.info("  depth={}, max_pages={}", max_depth, max_pages)
    logger.info("=" * 60)

    browser_config = BrowserConfig(
        headless=headless,
        extra_args=["--disable-gpu", "--no-sandbox"],
    )

    # Build BFS filter chain — inject our url_filter into crawl4ai's BFS
    # so unwanted paths are rejected DURING discovery, not just post-BFS
    from crawl4ai.deep_crawling.filters import FilterChain, URLFilter
    bfs_filters = []
    if url_filter:
        class _PathScopeFilter(URLFilter):
            """Wraps our url_filter as a crawl4ai URLFilter for BFS injection."""
            def __init__(self, fn):
                super().__init__(name="PathScope")
                self._fn = fn
            def apply(self, url: str) -> bool:
                return self._fn(url)
        bfs_filters.append(_PathScopeFilter(url_filter))

    deep_strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth,
        max_pages=max_pages,
        include_external=False,
        filter_chain=FilterChain(bfs_filters) if bfs_filters else FilterChain(),
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=30_000,
        deep_crawl_strategy=deep_strategy,
        delay_before_return_html=2.0,
        mean_delay=8.0,        # polite: 8s ± 3s between pages (gov sites rate-limit aggressively)
        max_range=3.0,
        stream=True,           # CRITICAL: stream mode → sequential fetching (batch mode fires all URLs in parallel!)
        # Strip nav/header/footer BEFORE link extraction —
        # forces BFS to only follow links in the main content body,
        # not site-wide navigation menus
        excluded_tags=["nav", "header", "footer", "aside"],
        exclude_external_links=True,
    )

    discovered: list[str] = []
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            logger.info("Browser launched, starting BFS (stream mode)...")
            results = await crawler.arun(url=seed_url, config=run_config)

            # stream=True → results is an async generator
            async for result in results:
                if result.success and result.url:
                    discovered.append(result.url)
                elif not result.success and result.url:
                    # Capture failed URLs that are still valuable for Phase 2:
                    # 1. CMS download links ("Download is starting" error)
                    # 2. Native .pdf files (crawl4ai can't parse as HTML, but HTTP download works)
                    url_lower = result.url.lower()
                    is_download_error = "Download is starting" in (result.error_message or "")
                    is_pdf_url = url_lower.endswith(".pdf")
                    if is_download_error or is_pdf_url:
                        discovered.append(result.url)
                        logger.info("  [download-link] {}", result.url)

    except Exception as e:
        logger.error("URL discovery error: {}", e)

    if not discovered:
        discovered = [seed_url]

    # ── Filter & deduplicate ────────────────────────────────────────────────
    seed_parsed = urlparse(seed_url)
    path_parts = seed_parsed.path.strip("/").split("/")
    # canada.ca: tight scope (department-level, e.g. /en/immigration-refugees-citizenship/)
    # Provincial sites: broad scope (same domain, allow all paths)
    is_canada_ca = "canada.ca" in seed_parsed.netloc
    if is_canada_ca:
        scope_prefix = "/" + "/".join(path_parts[:2]) if len(path_parts) >= 2 else "/"
    else:
        # For provincial sites, use first path segment only (e.g. /immigrate-to-b-c/)
        # or "/" if the seed is at root
        scope_prefix = "/" + path_parts[0] if path_parts and path_parts[0] else "/"

    seen: set[str] = set()
    entries: list[dict] = []
    skipped: list[str] = []

    for url in discovered:
        norm = _normalize_url(url)
        if norm in seen:
            continue
        seen.add(norm)

        parsed = urlparse(norm)
        path = parsed.path

        # Skip binary/download file URLs (crash crawl4ai when BFS tries to navigate)
        _SKIP_EXTENSIONS = {".zip", ".exe", ".msi", ".dmg", ".iso", ".tar", ".gz",
                            ".rar", ".7z", ".mp4", ".mp3", ".wav", ".doc", ".docx",
                            ".ppt", ".pptx", ".xls", ".xlsx"}
        if any(path.lower().endswith(ext) for ext in _SKIP_EXTENSIONS):
            skipped.append(f"[binary] {norm}")
            continue


        # Native PDF files bypass scope/path filters — they're often hosted
        # at different paths (e.g. /sites/default/files/) but linked from
        # relevant pages, so always keep them.
        is_native_pdf = path.lower().endswith(".pdf")

        # Filter: must be English (canada.ca uses /en/ prefix; skip for other domains)
        is_canada_ca = "canada.ca" in seed_parsed.netloc
        if is_canada_ca and not path.startswith("/en/") and not is_native_pdf:
            skipped.append(f"[lang] {norm}")
            continue
        if not is_native_pdf and not url_filter and not path.startswith(scope_prefix):
            skipped.append(f"[scope] {norm}")
            continue

        # Custom URL filter (per-province scope control) — skip for native PDFs
        if not is_native_pdf and url_filter and not url_filter(norm):
            skipped.append(f"[filter] {norm}")
            continue

        # Mirror website structure: URL path → local directory path
        relpath = _url_to_relpath(norm)

        # Handle duplicate paths by appending counter
        base = relpath
        counter = 2
        existing_names = {e["filename"] for e in entries}
        while relpath in existing_names:
            relpath = f"{base}-{counter}"
            counter += 1

        entries.append({
            "url": norm,
            "filename": relpath,  # now a relative path like study-canada/study-permit
        })

    for s in skipped:
        logger.info("  SKIP: {}", s[:80])

    logger.info("Discovered {} relevant URLs (skipped {})", len(entries), len(skipped))

    # ── Write manifest ──────────────────────────────────────────────────────
    manifest_path = _write_manifest(entries, persona_slug, seed_url, output_dir)
    return manifest_path


def _write_manifest(
    entries: list[dict],
    persona_slug: str,
    seed_url: str,
    output_dir: Path | str,
) -> Path:
    """Write manifest.json, merging with existing entries if present.

    Supports incremental discovery: run discover with different seed URLs
    and new pages are appended (deduped by URL) instead of overwriting.
    """
    out_dir = Path(output_dir) / persona_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"

    # ── Load existing manifest if present ──
    existing_pages: list[dict] = []
    seed_urls: list[str] = []
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            existing_pages = existing.get("pages", [])
            # Track seed URLs (backward-compat: old format has single seed_url)
            old_seeds = existing.get("seed_urls", [])
            if not old_seeds:
                old_seed = existing.get("seed_url", "")
                old_seeds = [old_seed] if old_seed else []
            seed_urls = old_seeds
        except (json.JSONDecodeError, OSError):
            pass

    # Add current seed URL if not already tracked
    if seed_url and seed_url not in seed_urls:
        seed_urls.append(seed_url)

    # ── Merge: existing pages + new entries, deduplicate by URL ──
    seen_urls: set[str] = set()
    merged: list[dict] = []

    # Existing pages first (preserve status/title from previous runs)
    for page in existing_pages:
        url = _normalize_url(page.get("url", ""))
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(page)

    # New entries (skip duplicates)
    new_count = 0
    for entry in entries:
        url = _normalize_url(entry.get("url", ""))
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(entry)
            new_count += 1

    # ── Also deduplicate filenames in merged list ──
    used_names: set[str] = set()
    for page in merged:
        fname = page.get("filename", "")
        if fname in used_names:
            base = fname
            counter = 2
            while fname in used_names:
                fname = f"{base}-{counter}"
                counter += 1
            page["filename"] = fname
        used_names.add(fname)

    manifest = {
        "seed_urls": seed_urls,
        "persona": persona_slug,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "total_urls": len(merged),
        "pages": merged,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "Manifest saved: {} ({} total, {} new)",
        manifest_path, len(merged), new_count,
    )

    # Log new entries only
    if new_count > 0:
        for entry in entries[-new_count:]:
            logger.info("  [NEW] {} -> {}.pdf", entry["url"][:70], entry["filename"])

    return manifest_path


# ── Direct file helpers ──────────────────────────────────────────────────────

_DIRECT_EXTENSIONS = {".pdf", ".json", ".csv", ".xlsx", ".xls", ".xml", ".txt"}


def _get_direct_file_ext(url: str) -> str | None:
    """Return the file extension if URL points to a direct download, else None."""
    from urllib.parse import urlparse

    path = urlparse(url).path.lower().rstrip("/")
    for ext in _DIRECT_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return None


async def _download_direct_file(url: str, out_path: Path) -> "CrawlResult":
    """Download a file directly via HTTP (no browser needed)."""
    import httpx

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.content)
            size = out_path.stat().st_size
            logger.info("    downloaded: {} ({:.1f} KB)", out_path.name, size / 1024)
            return CrawlResult(
                url=url, pdf_path=str(out_path),
                title=out_path.name, success=True, file_size=size,
            )
    except Exception as e:
        logger.error("    download failed: {} - {}", url[:60], e)
        return CrawlResult(url=url, success=False, error=str(e))


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Phase 2: manifest.json → PDF files                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def save_pdfs_from_manifest(
    manifest_path: Path | str,
    *,
    headless: bool = True,
    timeout: int = 30_000,
    delay_between: float = 2.0,
    pre_pdf_js: str | None = None,
) -> list[CrawlResult]:
    """Read manifest.json and save each URL as a full-page PDF.

    Sequential with polite delay between requests.

    Returns:
        List of CrawlResult (one per URL).
    """
    manifest_path = Path(manifest_path)
    out_dir = manifest_path.parent

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    pages = manifest.get("pages", [])
    if not pages:
        logger.warning("Manifest is empty: {}", manifest_path)
        return []

    logger.info("=" * 60)
    logger.info("PHASE 2: PDF Capture ({} pages)", len(pages))
    logger.info("  output: {}", out_dir)
    logger.info("=" * 60)

    results: list[CrawlResult] = []
    for i, entry in enumerate(pages):
        url = entry["url"]
        filename = entry["filename"]

        # ── Detect direct file links (.pdf, .json, .csv) ─────────────
        direct_ext = _get_direct_file_ext(url)
        if direct_ext:
            out_file = out_dir / f"{filename}{direct_ext}"
        else:
            out_file = out_dir / f"{filename}.pdf"


        # Windows: convert to extended-length path to bypass 260-char limit
        if sys.platform == "win32":
            _abs = str(out_file.resolve())
            _prefix = chr(92) * 2 + "?" + chr(92)
            if not _abs.startswith(_prefix):
                out_file = Path(_prefix + _abs)

        # Create nested directories (filename can be a/b/c style path)
        out_file.parent.mkdir(parents=True, exist_ok=True)


        # Skip if already saved
        if out_file.exists():
            size = out_file.stat().st_size
            logger.info("  [{}/{}] SKIP (exists): {} ({:.1f} KB)",
                        i + 1, len(pages), out_file.name, size / 1024)
            results.append(CrawlResult(
                url=url, filename=filename, pdf_path=str(out_file),
                success=True, file_size=size,
            ))
            continue

        # ── Direct file download (no browser needed) ─────────────────
        if direct_ext:
            logger.info("  [{}/{}] Downloading: {} -> {}",
                        i + 1, len(pages), url[:60], out_file.name)
            result = await _download_direct_file(url, out_file)
            result.filename = filename
            results.append(result)
        else:
            # ── Browser-based PDF capture ─────────────────────────────
            logger.info("  [{}/{}] Saving: {} -> {}.pdf",
                        i + 1, len(pages), url, filename)
            try:
                result = await asyncio.wait_for(
                    _save_single_pdf(url, out_file, headless=headless, timeout=timeout, pre_pdf_js=pre_pdf_js),
                    timeout=120,  # Hard 120s cap — Playwright timeouts unreliable on Windows
                )
            except asyncio.TimeoutError:
                logger.error("    TIMEOUT (120s): {} — skipping", url)
                result = CrawlResult(url=url, success=False, error="hard_timeout_120s")
            result.filename = filename

            # Fallback: if Playwright fails because URL triggers a download
            # (common with CMS URLs like /some-guide-pdf), try HTTP download
            if not result.success and result.error and "Download is starting" in result.error:
                logger.info("    [FALLBACK] Playwright download detected, trying HTTP...")
                dl_path = out_file.parent / (out_file.stem + ".download.pdf")
                result = await _download_direct_file(url, dl_path)
                result.filename = filename

            results.append(result)

        # Detect error pages (503, WAF blocks, soft-404, blank pages) and retry once
        _is_error = False
        _error_reason = ""
        if result.success and result.title:
            _t = result.title.lower()
            if any(k in _t for k in ['503', '403', 'temporarily unavailable',
                                       'access denied', 'forbidden', 'just a moment']):
                _is_error = True
                _error_reason = f"error_title: {result.title[:50]}"
            elif 'not found' in _t or 'page not found' in _t:
                _is_error = True
                _error_reason = f"soft_404: {result.title[:50]}"
        # Size-based check removed — too many false positives on legitimately
        # small pages (e.g. business-fundamentals 58KB). Early checks + title
        # detection handle real error pages.

        
        if _is_error:
            logger.warning("    Error page detected (title=%s, size=%s) — backing off 15s...",
                          result.title[:40] if result.title else 'N/A', result.file_size)
            try:
                out_file.unlink(missing_ok=True)
            except Exception:
                pass
            import time
            time.sleep(15)
            result = await _save_single_pdf(url, out_file, headless=headless, timeout=timeout, pre_pdf_js=pre_pdf_js)
            result.filename = filename
            # Check again
            _still_error = False
            if result.success and result.title:
                _t2 = result.title.lower()
                _still_error = any(k in _t2 for k in ['503', '403', 'temporarily unavailable',
                                                       'access denied', 'forbidden'])
            if result.success and result.file_size and result.file_size < 80_000:
                _still_error = True
            if _still_error:
                logger.error("    Still error after retry — skipping")
                result.success = False
                result.error = "error_page_after_retry"
                try:
                    out_file.unlink(missing_ok=True)
                except Exception:
                    pass
            results[-1] = result

        # Update manifest with title
        if result.success:
            entry["title"] = result.title
            entry["file_size"] = result.file_size
            entry["status"] = "saved"
        else:
            entry["status"] = "error"
            entry["error"] = result.error

        # Polite delay (minimum 3s to avoid rate-limiting)
        effective_delay = max(delay_between, 5.0)
        if i < len(pages) - 1:
            logger.info("    waiting {:.1f}s...", effective_delay)
            await asyncio.sleep(effective_delay)

    # Update manifest with results
    manifest["saved_at"] = datetime.now(timezone.utc).isoformat()
    manifest["pages"] = pages
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    succeeded = sum(1 for r in results if r.success)
    total_size = sum(r.file_size for r in results if r.success)
    logger.info("=" * 60)
    logger.info("PHASE 2 COMPLETE: {}/{} saved ({:.1f} MB)", succeeded, len(results), total_size / 1024 / 1024)
    logger.info("=" * 60)

    return results


async def _save_single_pdf(
    url: str,
    pdf_path: Path,
    *,
    headless: bool = True,
    timeout: int = 30_000,
    pre_pdf_js: str | None = None,
) -> CrawlResult:
    """Save a single URL as PDF using Playwright."""
    # Python 3.12+ on Windows uses ProactorEventLoop by default,
    # no need for the _run_in_proactor thread wrapper (which causes hangs).
    return await _save_single_pdf_impl(url, pdf_path, headless=headless, timeout=timeout, pre_pdf_js=pre_pdf_js)


async def _save_single_pdf_impl(
    url: str,
    pdf_path: Path,
    *,
    headless: bool = True,
    timeout: int = 30_000,
    pre_pdf_js: str | None = None,
) -> CrawlResult:
    """Internal: render URL to PDF, auto-skip form-heavy pages."""
    from playwright.async_api import async_playwright

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            # ── Force desktop viewport + screen media ──────────────────
            # Many sites (Algonquin, etc.) switch to mobile layout below ~1024px.
            # A4 width (~794px) triggers mobile, hiding tabs/sidebars.
            # Set wide viewport to keep desktop layout for PDF capture.
            await page.set_viewport_size({"width": 1280, "height": 900})
            await page.emulate_media(media="screen")

            # Total page-level timeout: 90 seconds max for entire render pipeline.
            # page.goto has its own timeout, but subsequent JS/tab expansion can hang.
            page.set_default_timeout(90_000)

            # domcontentloaded is more reliable than networkidle for gov sites
            # (analytics/tracking scripts prevent networkidle from ever firing)
            await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(1500)  # brief wait for initial render

            # ── Early page validation (all checks before expensive expansion) ──
            # Check BEFORE tabs, scrolling, image loading, etc.
            _early_title = await page.title()
            _early_info = await page.evaluate("""() => {
                const main = document.querySelector('main') || document.body;
                const text = main.innerText || '';
                const wordCount = text.split(/\\s+/).filter(w => w.length > 0).length;
                const forms = main.querySelectorAll('form').length;
                const requiredFields = main.querySelectorAll('[required]').length;
                return { wordCount, forms, requiredFields };
            }""")

            # 1. Soft-404: title contains "not found"
            if 'not found' in _early_title.lower():
                logger.info(
                    "    SKIP soft-404: {}.pdf (title='{}')",
                    pdf_path.stem, _early_title[:50],
                )
                await browser.close()
                return CrawlResult(
                    url=url, pdf_path="", title=_early_title,
                    success=False, error="skipped_soft_404",
                )

            # 2. Blank page: almost no content (dead program links)
            if _early_info["wordCount"] < 30 and "/program/" in url:
                logger.info(
                    "    SKIP blank page: {}.pdf (words={}, title='{}')",
                    pdf_path.stem, _early_info["wordCount"], _early_title[:50],
                )
                await browser.close()
                return CrawlResult(
                    url=url, pdf_path="", title=_early_title,
                    success=False, error="skipped_blank_page",
                )

            # 3. Interactive/form-heavy page: mostly input fields, little text
            if _early_info["requiredFields"] >= 2 and _early_info["wordCount"] < 200:
                logger.info(
                    "    SKIP interactive: {}.pdf (forms={}, required={}, words={})",
                    pdf_path.stem, _early_info["forms"],
                    _early_info["requiredFields"], _early_info["wordCount"],
                )
                await browser.close()
                return CrawlResult(
                    url=url, pdf_path="", title=_early_title,
                    success=False, error="skipped_interactive",
                )

            # All early checks passed — use the title for later references
            title = _early_title

            # ── 0. Dismiss cookie consent banners FIRST ──────────────────
            # Must run before any tab clicks / content expansion,
            # otherwise the consent overlay blocks all interactions.
            await page.evaluate("""() => {
                // Click "Allow All" / "Accept All" / "Essential Only" buttons
                const allBtns = document.querySelectorAll('button, a.btn, [role="button"]');
                for (const btn of allBtns) {
                    const text = (btn.textContent || '').toLowerCase().trim();
                    if (
                        text === 'allow all' || text === 'accept all' ||
                        text === 'accept all cookies' || text === 'accept cookies' ||
                        text === 'essential only' || text === 'i agree' ||
                        text === 'got it' ||
                        text.includes('accept all') || text.includes('allow all')
                    ) {
                        try { btn.click(); return; } catch(e) {}
                    }
                }
                // Fallback: force-remove common consent elements
                document.querySelectorAll(
                    '[class*="cookie"], [id*="cookie"], [class*="consent"], [id*="consent"], ' +
                    '[class*="CookieConsent"], [id*="CookieConsent"], ' +
                    '[class*="privacy-banner"], [id*="privacy-banner"], ' +
                    '#onetrust-consent-sdk, #CybotCookiebotDialog, .cc-window, .cc-banner'
                ).forEach(el => el.remove());
            }""")
            await page.wait_for_timeout(500)

            # ── Ensure 100% content loading ──────────────────────────────
            # 1. Force all images to load eagerly (remove lazy loading)
            await page.evaluate("""() => {
                document.querySelectorAll('img[loading="lazy"]').forEach(img => {
                    img.loading = 'eager';
                    // Force reload by resetting src
                    const src = img.src;
                    img.src = '';
                    img.src = src;
                });
            }""")

            # 2. Scroll to bottom — triggers any remaining lazy content
            await page.evaluate("""async () => {
                const delay = ms => new Promise(r => setTimeout(r, ms));
                const height = () => document.body.scrollHeight;
                let prev = 0;
                while (height() !== prev) {
                    prev = height();
                    window.scrollTo(0, height());
                    await delay(500);
                }
            }""")

            # 3. Expand all collapsible content sections (canada.ca uses <details>)
            await page.evaluate("""() => {
                // Only expand <details> in main content, NOT nav menus
                const main = document.querySelector('main') || document.body;
                main.querySelectorAll('details').forEach(d => d.open = true);
            }""")

            # 3b. Auto-click common 'show more' / 'expand all' buttons
            await page.evaluate("""() => {
                const main = document.querySelector('main') || document.body;
                const btns = main.querySelectorAll(
                    'button, a, [role="button"], .show-more, .expand-all'
                );
                for (const btn of btns) {
                    // Skip <a> links that navigate to other pages
                    if (btn.tagName === 'A') {
                        const href = (btn.getAttribute('href') || '').trim();
                        // Allow: #, javascript:, empty, or same-page anchors
                        // Block: /path/..., http://..., relative URLs to other pages
                        if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
                            continue;  // Real navigation link — skip!
                        }
                    }
                    const text = (btn.textContent || '').toLowerCase().trim();
                    if (
                        text.includes('show all') || text.includes('expand all') ||
                        text.includes('show more') || text.includes('view all') ||
                        text.includes('load more') || text.includes('see all')
                    ) {
                        try { btn.click(); } catch(e) {}
                    }
                }
                
                // Algonquin: click course description "Read More" links
                // These are in-page JS expanders, NOT navigation links
                main.querySelectorAll('a.link-read-more').forEach(link => {
                    try { link.click(); } catch(e) {}
                });
                
                // Fallback: swap data-description into DOM directly
                main.querySelectorAll('a.link-read-more[data-description]').forEach(link => {
                    try {
                        const full = link.getAttribute('data-description');
                        const descSpan = link.previousElementSibling;
                        if (descSpan && descSpan.classList.contains('course-description')) {
                            descSpan.innerHTML = full;
                        }
                        link.style.display = 'none';
                    } catch(e) {}
                });
            }""")
            await page.wait_for_timeout(1000)

            # 3c. Expand tabbed content (Algonquin + generic)
            await page.evaluate("""() => {
                const main = document.querySelector('main') || document.body;
                
                // A. Force ALL tab panels visible (Algonquin + generic)
                const panels = main.querySelectorAll(
                    '.tabs-monograph-content, ' +
                    '[role="tabpanel"], .tab-pane, .tab-content > div, ' +
                    '[class*="tab-panel"]'
                );
                for (const panel of panels) {
                    try {
                        if (!panel || !panel.style) continue;
                        panel.style.display = 'block';
                        panel.style.visibility = 'visible';
                        panel.style.opacity = '1';
                        panel.style.height = 'auto';
                        panel.style.overflow = 'visible';
                        panel.classList.add('active', 'show', 'in');
                    } catch(e) {}
                }
                
                // B. Expand course accordions (Algonquin)
                main.querySelectorAll('.course-accordion').forEach(btn => {
                    try {
                        btn.setAttribute('aria-expanded', 'true');
                        btn.classList.add('active');
                    } catch(e) {}
                });
                main.querySelectorAll('.course-panel').forEach(panel => {
                    try {
                        panel.removeAttribute('hidden');
                        panel.style.display = 'block';
                    } catch(e) {}
                });
                
                // C. Generic: expand any [role="tab"] panels
                main.querySelectorAll('[role="tab"]').forEach(tab => {
                    try { tab.click(); } catch(e) {}
                });
                
                // D. Reorder Algonquin content panels to match sidebar nav order
                const container = document.getElementById('monograph-tabs-content');
                const navButtons = document.querySelectorAll('#tab-menu .monograph-tab');
                if (container && navButtons.length > 0) {
                    // Extract panel IDs from button onclick: programPageInfo(event, 'summary')
                    const order = [];
                    navButtons.forEach(btn => {
                        const match = (btn.getAttribute('onclick') || '').match(/'([^']+)'/);
                        if (match) order.push(match[1]);
                    });
                    // Reorder panels by appending in sidebar order
                    order.forEach(id => {
                        const panel = document.getElementById(id);
                        if (panel) container.appendChild(panel);
                    });
                }
            }""")
            await page.wait_for_timeout(1500)

            # 3d. Expand generic accordions / Bootstrap collapse / WordPress toggles
            # Handles the "Step 1: Choose a Program" style accordions with + icons
            await page.evaluate("""() => {
                const main = document.querySelector('main') || document.body;
                
                // A. Bootstrap collapse: click triggers + force panels visible
                main.querySelectorAll(
                    '[data-toggle="collapse"], [data-bs-toggle="collapse"]'
                ).forEach(trigger => {
                    try {
                        // Click to expand (toggles aria-expanded)
                        if (trigger.getAttribute('aria-expanded') !== 'true') {
                            trigger.click();
                        }
                    } catch(e) {}
                });
                // Force all .collapse panels visible regardless of click
                main.querySelectorAll('.collapse, .panel-collapse').forEach(panel => {
                    try {
                        panel.classList.add('show', 'in');
                        panel.style.display = 'block';
                        panel.style.height = 'auto';
                        panel.style.overflow = 'visible';
                    } catch(e) {}
                });
                
                // B. Generic aria-expanded buttons (WordPress, custom JS)
                main.querySelectorAll('[aria-expanded="false"]').forEach(btn => {
                    try {
                        btn.setAttribute('aria-expanded', 'true');
                        btn.click();
                    } catch(e) {}
                });
                
                // C. Accordion panels: force all visible
                main.querySelectorAll(
                    '.accordion-collapse, .accordion-body, .accordion-content, ' +
                    '.panel-body, .panel-content, ' +
                    '[class*="accordion-panel"], [class*="accordion-item"] > div:last-child, ' +
                    '.wp-block-details, .toggle-content, ' +
                    '[class*="collapsible-content"], [class*="expandable"]'
                ).forEach(panel => {
                    try {
                        panel.style.display = 'block';
                        panel.style.visibility = 'visible';
                        panel.style.height = 'auto';
                        panel.style.maxHeight = 'none';
                        panel.style.overflow = 'visible';
                        panel.style.opacity = '1';
                        panel.classList.add('show', 'in', 'active', 'open');
                        panel.classList.remove('collapsed', 'hidden');
                        panel.removeAttribute('hidden');
                    } catch(e) {}
                });
                
                // D. Algonquin "whistle" accordions (day-time-programs steps)
                // Pattern: <h3 class="whistle-title" aria-selected="false">Step 1:...</h3>
                // Clicking toggles aria-selected and shows the sibling content div
                main.querySelectorAll('.whistle-title').forEach(trigger => {
                    try {
                        trigger.setAttribute('aria-selected', 'true');
                        trigger.classList.add('active', 'open');
                        trigger.click();
                    } catch(e) {}
                });
                // Also handle aria-selected="false" generically
                main.querySelectorAll('[aria-selected="false"]').forEach(el => {
                    try {
                        el.setAttribute('aria-selected', 'true');
                        el.click();
                    } catch(e) {}
                });
                
                // E. Generic toggle-items / step-accordions
                main.querySelectorAll(
                    '.toggle-item, .step-accordion, ' +
                    '[class*="toggle-trigger"], [class*="step-toggle"]'
                ).forEach(trigger => {
                    try {
                        trigger.classList.add('active', 'open');
                        trigger.setAttribute('aria-expanded', 'true');
                        const next = trigger.nextElementSibling;
                        if (next) {
                            next.style.display = 'block';
                            next.style.height = 'auto';
                            next.removeAttribute('hidden');
                        }
                    } catch(e) {}
                });
            }""")
            await page.wait_for_timeout(1000)

            # 3e. Expand FooTable paginated tables (Algonquin scholarships, etc.)
            # FooTable is a client-side pagination plugin — ALL data is already in
            # the DOM, just hidden.  We set page size to 9999 to show all rows.
            await page.evaluate("""() => {
                // Method 1: trigger FooTable API to show all rows
                const tables = document.querySelectorAll('.footable, table.footable');
                tables.forEach(table => {
                    try {
                        const ft = FooTable.get(table);
                        if (ft && ft.rows && ft.rows.all) {
                            ft.pageSize(9999);
                        }
                    } catch(e) {}
                });
                // Method 2: select "200" (max) from the page-size dropdown
                document.querySelectorAll('.nt_pager_selection').forEach(sel => {
                    try {
                        // Pick the largest option
                        const opts = Array.from(sel.options);
                        if (opts.length > 0) {
                            const maxOpt = opts[opts.length - 1];
                            sel.value = maxOpt.value;
                            sel.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    } catch(e) {}
                });
                // Method 3: brute-force — unhide all footable rows
                document.querySelectorAll('.footable-page, tr.footable-detail-row')
                    .forEach(row => {
                        row.style.display = '';
                        row.classList.remove('footable-paging-hidden');
                    });
                document.querySelectorAll('tr').forEach(row => {
                    if (row.style.display === 'none' &&
                        row.closest('.footable, table.footable')) {
                        row.style.display = '';
                    }
                });
            }""")
            await page.wait_for_timeout(1500)

            # 3f. Expand Algonquin checklistToggleHead accordions
            # Pattern: <div class="checklistToggleHead">Title<span class="toggleHandle"/></div>
            #          <div class="checklistToggleBody" style="display:none">Content</div>
            await page.evaluate("""() => {
                // Click all toggle headers to trigger their JS expansion
                document.querySelectorAll('.checklistToggleHead, [class*="ToggleHead"]').forEach(head => {
                    try { head.click(); } catch(e) {}
                });
                // Brute-force: show all toggle body siblings
                document.querySelectorAll(
                    '.checklistToggleBody, [class*="ToggleBody"], [class*="toggle-body"]'
                ).forEach(body => {
                    try {
                        body.style.display = 'block';
                        body.style.visibility = 'visible';
                        body.style.height = 'auto';
                        body.style.overflow = 'visible';
                    } catch(e) {}
                });
                // Fallback: for any toggleHead, force-show next sibling
                document.querySelectorAll('[class*="ToggleHead"], [class*="toggle-head"]').forEach(head => {
                    try {
                        const next = head.nextElementSibling;
                        if (next) {
                            next.style.display = 'block';
                            next.style.visibility = 'visible';
                            next.style.height = 'auto';
                        }
                    } catch(e) {}
                });
            }""")
            await page.wait_for_timeout(1000)

            # 4. Wait for ALL images to fully load
            await page.evaluate("""() => {
                return Promise.all(
                    Array.from(document.images)
                        .filter(img => !img.complete)
                        .map(img => new Promise(r => {
                            img.onload = img.onerror = r;
                        }))
                );
            }""")

            # 5. Dismiss popups, survey modals, cookie banners
            await page.evaluate("""() => {
                // 5a. Click cookie consent "Accept/Allow" buttons to dismiss properly
                const allBtns = document.querySelectorAll('button, a.btn, [role="button"]');
                for (const btn of allBtns) {
                    const text = (btn.textContent || '').toLowerCase().trim();
                    if (
                        text === 'allow all' || text === 'accept all' ||
                        text === 'accept all cookies' || text === 'accept cookies' ||
                        text === 'essential only' || text === 'i agree' ||
                        text === 'got it' || text === 'ok' ||
                        text.includes('accept all') || text.includes('allow all')
                    ) {
                        try { btn.click(); } catch(e) {}
                    }
                }
                
                // 5b. Remove survey/feedback/cookie popups, chatbot widgets, and overlays
                //     IMPORTANT: skip body/html/main to avoid destroying page structure
                const keepTags = new Set(['BODY', 'HTML', 'MAIN', 'ARTICLE', 'SECTION']);
                document.querySelectorAll(
                    '.gc-popup, .modal, ' +
                    '[class*="survey"], [id*="survey"], ' +
                    '[class*="popup"], [id*="popup"], ' +
                    '.foresee-invitation, [class*="medallia"], ' +
                    '[role="dialog"], [aria-modal="true"], ' +
                    '[class*="cookie-banner"], [class*="cookie-consent"], ' +
                    '[id*="cookie-banner"], [id*="cookie-consent"], ' +
                    '[class*="CookieConsent"], [id*="CookieConsent"], ' +
                    '[class*="privacy-banner"], [id*="privacy-banner"], ' +
                    '#onetrust-consent-sdk, .onetrust-pc-dark-filter, ' +
                    '#CybotCookiebotDialog, .cc-window, .cc-banner, ' +
                    /* Chatbot / live-chat widgets */
                    '[class*="chat-widget"], [id*="chat-widget"], ' +
                    '[class*="chatbot"], [id*="chatbot"], ' +
                    '[class*="live-chat"], [id*="live-chat"], ' +
                    '[class*="livechat"], [id*="livechat"], ' +
                    '[class*="webchat"], [id*="webchat"], ' +
                    '#drift-widget, #hubspot-messages-iframe-container, ' +
                    '#intercom-container, .intercom-lightweight-app, ' +
                    '[class*="Intercom"], [id*="intercom"], ' +
                    'iframe[title*="chat" i], iframe[title*="Chat" i], ' +
                    'iframe[src*="chat"], iframe[src*="livechat"]'
                ).forEach(el => {
                    if (!keepTags.has(el.tagName)) el.remove();
                });
                
                // 5b-extra. Specific chat platforms + fixed-position chat launchers
                // Freshchat (Algonquin's green chat bubble), Tawk, Zendesk, etc.
                document.querySelectorAll(
                    '#fc_frame, #fc-widget-container, [class*="freshchat"], ' +
                    '#tawkto-chat, .tawk-widget, [id*="tawk-"], ' +
                    '#launcher[data-testid], iframe[title*="Messaging" i], ' +
                    '#tidio-chat, [class*="tidio"], ' +
                    '#zsiq_float, .zsiq_theme1, ' +
                    '#crisp-chatbox, [class*="crisp-client"], ' +
                    /* Wysdom AI (Algonquin College chat widget) */
                    '#wysdom-highlight, #wysdom-chat-bot, [id*="wysdom"], [class*="wysdom"]'
                ).forEach(el => {
                    if (!keepTags.has(el.tagName)) el.remove();
                });
                // Catch-all: nuke any small position:fixed element near bottom-right
                // (chat launcher bubbles are always fixed, small, bottom-right)
                document.querySelectorAll('div, iframe, button').forEach(el => {
                    if (keepTags.has(el.tagName)) return;
                    const s = window.getComputedStyle(el);
                    if (s.position !== 'fixed') return;
                    const r = el.getBoundingClientRect();
                    if (r.width < 400 && r.height < 400 &&
                        r.bottom > window.innerHeight - 100 &&
                        r.right > window.innerWidth - 100) {
                        el.remove();
                    }
                });

                // 5c. Remove backdrop/overlay masks (only divs, not structural elements)
                document.querySelectorAll(
                    '.modal-backdrop, .overlay-mask'
                ).forEach(el => {
                    if (!keepTags.has(el.tagName)) el.remove();
                });
                
                // 5d. Restore body scroll
                if (document.body) {
                    document.body.style.overflow = 'auto';
                    document.body.classList.remove('modal-open');
                }
            }""")

            # 6. Scroll back to top + final wait for rendering
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)



            # ── Save PDF (proper pagination + full content) ────────────
            # Use page.pdf() for smart pagination (no cut text).
            # Inject CSS to override print stylesheets so header/footer/
            # images remain visible in print mode.

            await page.add_style_tag(content="""
                @media print {
                    * {
                        color-adjust: exact !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                    body, html { width: 100% !important; }
                    /* Neutralize ALL sticky/fixed elements — prevents nav overlapping content */
                    [style*="position: fixed"], [style*="position: sticky"],
                    header, footer, nav, aside,
                    .gcweb-menu, #wb-info, #wb-sm, #wb-bnr,
                    [role="banner"], [role="contentinfo"], [role="navigation"] {
                        position: relative !important;
                        top: auto !important;
                        z-index: auto !important;
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                        height: auto !important;
                        overflow: visible !important;
                    }
                    img {
                        display: inline-block !important;
                        visibility: visible !important;
                        max-width: 100% !important;
                    }
                    .noprint, .wb-inv { display: none !important; }
                }
            """)

            # Run caller-provided site-specific cleanup JS (if any).
            # This decouples site-specific DOM manipulation from the engine.
            if pre_pdf_js:
                await page.evaluate(pre_pdf_js)

            # Inject a clickable source URL banner at the top of the page.
            # This becomes part of the page content (not a PDF margin note),
            # so it's visible, readable, and the URL is a real clickable link.
            from datetime import datetime as _dt
            capture_date = _dt.now().strftime("%Y-%m-%d %H:%M")
            await page.evaluate("""(args) => {
                const banner = document.createElement('div');
                banner.innerHTML = `
                    <div style="
                        background: #f0f0f0;
                        border-bottom: 2px solid #26374a;
                        padding: 8px 16px;
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                        color: #333;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <span>
                            Source: <a href="${args.url}" style="color: #2b4380; text-decoration: underline; font-size: 12px;">${args.url}</a>
                        </span>
                        <span style="color: #666; font-size: 11px;">
                            Captured: ${args.date}
                        </span>
                    </div>
                `;
                document.body.insertBefore(banner, document.body.firstChild);
            }""", {"url": url, "date": capture_date})


            # Let Chromium's print engine handle pagination naturally.
            # Do NOT set height to scrollHeight — that creates a single
            # giant page that MinerU cannot process (layout model scales
            # to fixed height, crushing width to ~77px on long pages).
            await page.pdf(
                path=str(pdf_path),
                width="1280px",
                print_background=True,
                margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
            )

            await browser.close()

        file_size = pdf_path.stat().st_size
        logger.info("    saved: {}.pdf ({:.1f} KB) '{}'",
                     pdf_path.stem, file_size / 1024, title[:50])

        return CrawlResult(
            url=url, pdf_path=str(pdf_path), title=title,
            success=True, file_size=file_size,
        )

    except Exception as e:
        logger.error("    FAILED: {} - {}", url[:60], e)
        return CrawlResult(url=url, success=False, error=str(e))


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Combined: discover → save (convenience wrapper)                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def crawl_and_save_pdfs(
    seed_url: str,
    *,
    persona_slug: str = "general",
    max_depth: int = 2,
    max_pages: int = 20,
    headless: bool = True,
    delay_between: float = 2.0,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> list[CrawlResult]:
    """Full pipeline: Phase 1 (discover) + Phase 2 (save PDFs)."""

    # Phase 1: Discover URLs → manifest.json
    manifest_path = await discover_urls(
        seed_url,
        persona_slug=persona_slug,
        max_depth=max_depth,
        max_pages=max_pages,
        headless=headless,
        output_dir=output_dir,
    )

    # Phase 2: Save PDFs from manifest
    results = await save_pdfs_from_manifest(
        manifest_path,
        headless=headless,
        delay_between=delay_between,
    )

    return results
