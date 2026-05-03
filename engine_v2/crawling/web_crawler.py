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
from dataclasses import dataclass, field
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


MAX_FILENAME_LEN = 50  # Prevent Windows MAX_PATH (260) overflow


def _url_to_filename(url: str) -> str:
    """Extract meaningful filename from URL path.

    Truncates to MAX_FILENAME_LEN chars to avoid Windows path limits.
    MinerU output repeats the name 3x in the path, so keeping it short
    is critical (e.g. 123-char name → 400+ char total path → failure).

    Examples:
        .../express-entry.html      → express-entry
        .../eligibility.html        → eligibility
        ...very-long-slug.html      → very-long-slug-ab12cd34
    """
    import hashlib

    parsed = urlparse(url)
    # Take last path segment, strip extension
    last_segment = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"\.(html?|asp|php)$", "", last_segment, flags=re.IGNORECASE)
    # Clean non-alphanumeric chars
    name = re.sub(r"[^\w\-]", "-", name).strip("-")
    name = name or "index"

    # Truncate long names: keep prefix + 8-char hash for uniqueness
    if len(name) > MAX_FILENAME_LEN:
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
        prefix_len = MAX_FILENAME_LEN - 9  # 8 hash + 1 dash
        name = f"{name[:prefix_len]}-{hash_suffix}"

    return name


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
) -> Path:
    """Discover same-domain sub-page URLs via BFS and save manifest.json.

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
            )
        )
        return await loop.run_in_executor(None, future.result)
    else:
        return await _discover_urls_impl(
            seed_url, persona_slug=persona_slug,
            max_depth=max_depth, max_pages=max_pages,
            headless=headless, output_dir=output_dir,
        )


async def _discover_urls_impl(
    seed_url: str,
    *,
    persona_slug: str = "general",
    max_depth: int = 2,
    max_pages: int = 20,
    headless: bool = True,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
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

    deep_strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth,
        max_pages=max_pages,
        include_external=False,
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=30_000,
        deep_crawl_strategy=deep_strategy,
        delay_before_return_html=0.5,
        mean_delay=2.0,
        max_range=1.0,
        stream=False,
        # Strip nav/header/footer BEFORE link extraction —
        # forces BFS to only follow links in the main content body,
        # not site-wide navigation menus
        excluded_tags=["nav", "header", "footer", "aside"],
        exclude_external_links=True,
    )

    discovered: list[str] = []
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            logger.info("Browser launched, starting BFS...")
            results = await crawler.arun(url=seed_url, config=run_config)

            for result in results:
                if result.success and result.url:
                    discovered.append(result.url)

    except Exception as e:
        logger.error("URL discovery error: {}", e)

    if not discovered:
        discovered = [seed_url]

    # ── Filter & deduplicate ────────────────────────────────────────────────
    seed_parsed = urlparse(seed_url)
    # Scope: same department path (e.g. /en/immigration-refugees-citizenship/)
    path_parts = seed_parsed.path.strip("/").split("/")
    # Keep first 2 segments: en/immigration-refugees-citizenship
    scope_prefix = "/" + "/".join(path_parts[:2]) if len(path_parts) >= 2 else "/"

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

        # Filter: must be English, must be in scope
        if not path.startswith("/en/"):
            skipped.append(f"[lang] {norm}")
            continue
        if not path.startswith(scope_prefix):
            skipped.append(f"[scope] {norm}")
            continue

        filename = _url_to_filename(norm)

        # Handle duplicate filenames by appending counter
        base = filename
        counter = 2
        existing_names = {e["filename"] for e in entries}
        while filename in existing_names:
            filename = f"{base}-{counter}"
            counter += 1

        entries.append({
            "url": norm,
            "filename": filename,
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


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Phase 2: manifest.json → PDF files                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def save_pdfs_from_manifest(
    manifest_path: Path | str,
    *,
    headless: bool = True,
    timeout: int = 30_000,
    delay_between: float = 2.0,
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
        pdf_path = out_dir / f"{filename}.pdf"

        # Skip if already saved
        if pdf_path.exists():
            size = pdf_path.stat().st_size
            logger.info("  [{}/{}] SKIP (exists): {}.pdf ({:.1f} KB)",
                        i + 1, len(pages), filename, size / 1024)
            results.append(CrawlResult(
                url=url, filename=filename, pdf_path=str(pdf_path),
                success=True, file_size=size,
            ))
            continue

        logger.info("  [{}/{}] Saving: {} -> {}.pdf", i + 1, len(pages), url[:60], filename)

        result = await _save_single_pdf(url, pdf_path, headless=headless, timeout=timeout)
        result.filename = filename
        results.append(result)

        # Update manifest with title
        if result.success:
            entry["title"] = result.title
            entry["file_size"] = result.file_size
            entry["status"] = "saved"
        else:
            entry["status"] = "error"
            entry["error"] = result.error

        # Polite delay
        if i < len(pages) - 1:
            logger.info("    waiting {:.1f}s...", delay_between)
            await asyncio.sleep(delay_between)

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
) -> CrawlResult:
    """Save a single URL as PDF using Playwright."""
    if sys.platform == "win32":
        loop = asyncio.get_event_loop()
        future = _run_in_proactor(
            _save_single_pdf_impl(url, pdf_path, headless=headless, timeout=timeout)
        )
        return await loop.run_in_executor(None, future.result)
    else:
        return await _save_single_pdf_impl(url, pdf_path, headless=headless, timeout=timeout)


async def _save_single_pdf_impl(
    url: str,
    pdf_path: Path,
    *,
    headless: bool = True,
    timeout: int = 30_000,
) -> CrawlResult:
    """Internal: render URL to PDF, auto-skip form-heavy pages."""
    from playwright.async_api import async_playwright

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            # ── Force screen media (print CSS hides images on many sites) ──
            await page.emulate_media(media="screen")

            await page.goto(url, wait_until="networkidle", timeout=timeout)

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
                // Close survey/feedback popups (canada.ca uses Foresee/Medallia)
                document.querySelectorAll(
                    '.gc-popup, .modal, [class*="survey"], [class*="overlay"], ' +
                    '[class*="popup"], [id*="survey"], [id*="popup"], ' +
                    '.foresee-invitation, [class*="medallia"], ' +
                    '[role="dialog"], [aria-modal="true"]'
                ).forEach(el => el.remove());
                
                // Also remove any backdrop/overlay masks
                document.querySelectorAll(
                    '.modal-backdrop, [class*="backdrop"], [class*="mask"]'
                ).forEach(el => el.remove());
                
                // Remove body scroll lock from modals
                document.body.style.overflow = 'auto';
                document.body.classList.remove('modal-open');
            }""")

            # 6. Scroll back to top + final wait for rendering
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            # ── Auto-detect interactive/form pages ───────────────────────
            page_info = await page.evaluate("""() => {
                const main = document.querySelector('main') || document.body;
                const text = main.innerText || '';
                const forms = main.querySelectorAll('form').length;
                const selects = main.querySelectorAll('select').length;
                const inputs = main.querySelectorAll('input:not([type=hidden])').length;
                const requiredFields = main.querySelectorAll('[required]').length;
                const wordCount = text.split(/\\s+/).filter(w => w.length > 0).length;
                return { forms, selects, inputs, requiredFields, wordCount };
            }""")

            is_interactive = (
                page_info["requiredFields"] >= 2
                and page_info["wordCount"] < 200
            )

            title = await page.title()

            if is_interactive:
                logger.info(
                    "    SKIP interactive: {}.pdf (forms={}, required={}, words={})",
                    pdf_path.stem, page_info["forms"],
                    page_info["requiredFields"], page_info["wordCount"],
                )
                await browser.close()
                return CrawlResult(
                    url=url, pdf_path="", title=title,
                    success=False, error="skipped_interactive",
                )

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
                    header, footer, nav, aside,
                    .gcweb-menu, #wb-info, #wb-sm, #wb-bnr,
                    [role="banner"], [role="contentinfo"], [role="navigation"] {
                        display: block !important;
                        visibility: visible !important;
                        opacity: 1 !important;
                        height: auto !important;
                        overflow: visible !important;
                        position: relative !important;
                    }
                    img {
                        display: inline-block !important;
                        visibility: visible !important;
                        max-width: 100% !important;
                    }
                    .noprint, .wb-inv { display: none !important; }
                }
            """)

            # Let Chromium's print engine handle pagination naturally.
            # Do NOT set height to scrollHeight — that creates a single
            # giant page that MinerU cannot process (layout model scales
            # to fixed height, crushing width to ~77px on long pages).
            await page.pdf(
                path=str(pdf_path),
                format="Letter",
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
