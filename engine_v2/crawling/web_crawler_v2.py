"""web_crawler_v2 — Profile-driven URL discovery + PDF archival.

Refactored from web_crawler.py: all site-specific JS/CSS extracted to
js_snippets.py + sites/*.py profiles. Engine is now fully site-agnostic.

Pipeline unchanged:
    Phase 1: discover_urls() → manifest.json
    Phase 2: save_pdfs_from_manifest() → PDFs
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

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import get_profile, compute_scope_prefix

# Ensure site profiles are registered
import engine_v2.crawling.sites  # noqa: F401

_CRAWL_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="crawl4ai")
_DEFAULT_OUTPUT_DIR = Path("data/crawled_web")
MAX_SEGMENT_LEN = 200


def _run_in_proactor(coro):
    def _thread_target():
        loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return _CRAWL_EXECUTOR.submit(_thread_target)


@dataclass
class CrawlResult:
    url: str
    filename: str = ""
    pdf_path: str = ""
    title: str = ""
    success: bool = True
    error: str | None = None
    file_size: int = 0


# ── URL Utilities (unchanged) ────────────────────────────────────────────────

def _url_to_relpath(url: str) -> str:
    import hashlib
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    path = re.sub(r"\.(html?|asp|php)$", "", path, flags=re.IGNORECASE)
    if not path:
        return "index"
    segments = path.split("/")
    clean_segments = []
    for seg in segments:
        seg = re.sub(r"[^\w\-]", "-", seg).strip("-")
        if not seg:
            continue
        if len(seg) > MAX_SEGMENT_LEN:
            hash_suffix = hashlib.md5(seg.encode()).hexdigest()[:8]
            seg = f"{seg[:MAX_SEGMENT_LEN - 9]}-{hash_suffix}"
        clean_segments.append(seg)
    return "/".join(clean_segments) if clean_segments else "index"


def _url_to_filename(url: str) -> str:
    return _url_to_relpath(url).replace("/", "--")


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


_SKIP_EXTENSIONS = {".zip", ".exe", ".msi", ".dmg", ".iso", ".tar", ".gz",
                    ".rar", ".7z", ".mp4", ".mp3", ".wav", ".doc", ".docx",
                    ".ppt", ".pptx", ".xls", ".xlsx"}

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Phase 1: URL Discovery → manifest.json                                  ║
# ╚════════════════════════════════════════════════════════════════════════════╝

async def discover_urls(
    seed_url: str, *, persona_slug: str = "general", max_depth: int = 2,
    max_pages: int = 20, headless: bool = True,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR, url_filter: Any | None = None,
) -> Path:
    if sys.platform == "win32":
        loop = asyncio.get_event_loop()
        future = _run_in_proactor(
            _discover_urls_impl(seed_url, persona_slug=persona_slug,
                max_depth=max_depth, max_pages=max_pages, headless=headless,
                output_dir=output_dir, url_filter=url_filter))
        return await loop.run_in_executor(None, future.result)
    return await _discover_urls_impl(
        seed_url, persona_slug=persona_slug, max_depth=max_depth,
        max_pages=max_pages, headless=headless, output_dir=output_dir,
        url_filter=url_filter)


async def _discover_urls_impl(
    seed_url: str, *, persona_slug: str = "general", max_depth: int = 2,
    max_pages: int = 20, headless: bool = True,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR, url_filter: Any | None = None,
) -> Path:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
    except ImportError:
        logger.error("crawl4ai not installed")
        return _write_manifest([{"url": seed_url, "filename": _url_to_filename(seed_url)}],
                               persona_slug, seed_url, output_dir)

    profile = get_profile(seed_url)
    logger.info("=" * 60)
    logger.info("PHASE 1: URL Discovery [profile={}]", profile.name)
    logger.info("  seed: {}", seed_url)
    logger.info("  depth={}, max_pages={}", max_depth, max_pages)
    logger.info("=" * 60)

    browser_config = BrowserConfig(headless=headless, extra_args=["--disable-gpu", "--no-sandbox"])

    from crawl4ai.deep_crawling.filters import FilterChain, URLFilter
    bfs_filters = []
    if url_filter:
        class _PathScopeFilter(URLFilter):
            def __init__(self, fn):
                super().__init__(name="PathScope")
                self._fn = fn
            def apply(self, url: str) -> bool:
                return self._fn(url)
        bfs_filters.append(_PathScopeFilter(url_filter))

    deep_strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth, max_pages=max_pages, include_external=False,
        filter_chain=FilterChain(bfs_filters) if bfs_filters else FilterChain())

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, page_timeout=30_000,
        deep_crawl_strategy=deep_strategy, delay_before_return_html=2.0,
        mean_delay=8.0, max_range=3.0, stream=True,
        excluded_tags=["nav", "header", "footer", "aside"],
        exclude_external_links=True)

    discovered: list[str] = []
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            logger.info("Browser launched, starting BFS (stream mode)...")
            results = await crawler.arun(url=seed_url, config=run_config)
            async for result in results:
                if result.success and result.url:
                    discovered.append(result.url)
                elif not result.success and result.url:
                    url_lower = result.url.lower()
                    is_download = "Download is starting" in (result.error_message or "")
                    if is_download or url_lower.endswith(".pdf"):
                        discovered.append(result.url)
                        logger.info("  [download-link] {}", result.url)
    except Exception as e:
        logger.error("URL discovery error: {}", e)

    if not discovered:
        discovered = [seed_url]

    # ── Filter & deduplicate (profile-driven) ────────────────────────────
    scope_prefix = compute_scope_prefix(seed_url, profile)

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

        if any(path.lower().endswith(ext) for ext in _SKIP_EXTENSIONS):
            skipped.append(f"[binary] {norm}")
            continue

        is_native_pdf = path.lower().endswith(".pdf")

        # Language filter (profile-driven, replaces hardcoded canada.ca check)
        if profile.language_filter and not is_native_pdf:
            if not path.startswith(profile.language_filter):
                skipped.append(f"[lang] {norm}")
                continue

        # Scope filter
        if not is_native_pdf and not url_filter and not path.startswith(scope_prefix):
            skipped.append(f"[scope] {norm}")
            continue

        if not is_native_pdf and url_filter and not url_filter(norm):
            skipped.append(f"[filter] {norm}")
            continue

        relpath = _url_to_relpath(norm)
        base = relpath
        counter = 2
        existing_names = {e["filename"] for e in entries}
        while relpath in existing_names:
            relpath = f"{base}-{counter}"
            counter += 1
        entries.append({"url": norm, "filename": relpath})

    for s in skipped:
        logger.info("  SKIP: {}", s[:80])
    logger.info("Discovered {} relevant URLs (skipped {})", len(entries), len(skipped))

    return _write_manifest(entries, persona_slug, seed_url, output_dir)


def _write_manifest(entries, persona_slug, seed_url, output_dir):
    out_dir = Path(output_dir) / persona_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"

    existing_pages, seed_urls = [], []
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            existing_pages = existing.get("pages", [])
            seed_urls = existing.get("seed_urls", [])
            if not seed_urls:
                old = existing.get("seed_url", "")
                seed_urls = [old] if old else []
        except (json.JSONDecodeError, OSError):
            pass

    if seed_url and seed_url not in seed_urls:
        seed_urls.append(seed_url)

    seen_urls: set[str] = set()
    merged: list[dict] = []
    for page in existing_pages:
        url = _normalize_url(page.get("url", ""))
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(page)

    new_count = 0
    for entry in entries:
        url = _normalize_url(entry.get("url", ""))
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(entry)
            new_count += 1

    used_names: set[str] = set()
    for page in merged:
        fname = page.get("filename", "")
        if fname in used_names:
            base, counter = fname, 2
            while fname in used_names:
                fname = f"{base}-{counter}"
                counter += 1
            page["filename"] = fname
        used_names.add(fname)

    manifest = {"seed_urls": seed_urls, "persona": persona_slug,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "total_urls": len(merged), "pages": merged}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Manifest saved: {} ({} total, {} new)", manifest_path, len(merged), new_count)
    if new_count > 0:
        for entry in entries[-new_count:]:
            logger.info("  [NEW] {} -> {}.pdf", entry["url"][:70], entry["filename"])
    return manifest_path


# ── Direct file helpers ──────────────────────────────────────────────────────

_DIRECT_EXTENSIONS = {".pdf", ".json", ".csv", ".xlsx", ".xls", ".xml", ".txt"}

def _get_direct_file_ext(url: str) -> str | None:
    path = urlparse(url).path.lower().rstrip("/")
    for ext in _DIRECT_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return None

async def _download_direct_file(url: str, out_path: Path) -> CrawlResult:
    import httpx
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.content)
            size = out_path.stat().st_size
            logger.info("    downloaded: {} ({:.1f} KB)", out_path.name, size / 1024)
            return CrawlResult(url=url, pdf_path=str(out_path), title=out_path.name,
                               success=True, file_size=size)
    except Exception as e:
        logger.error("    download failed: {} - {}", url[:60], e)
        return CrawlResult(url=url, success=False, error=str(e))


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Phase 2: manifest.json → PDF files (profile-driven)                     ║
# ╚════════════════════════════════════════════════════════════════════════════╝

async def save_pdfs_from_manifest(
    manifest_path: Path | str, *, headless: bool = True,
    timeout: int = 30_000, delay_between: float = 2.0,
) -> list[CrawlResult]:
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
        direct_ext = _get_direct_file_ext(url)
        out_file = out_dir / (f"{filename}{direct_ext}" if direct_ext else f"{filename}.pdf")

        if sys.platform == "win32":
            _abs = str(out_file.resolve())
            _prefix = chr(92) * 2 + "?" + chr(92)
            if not _abs.startswith(_prefix):
                out_file = Path(_prefix + _abs)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if out_file.exists():
            size = out_file.stat().st_size
            logger.info("  [{}/{}] SKIP (exists): {} ({:.1f} KB)", i+1, len(pages), out_file.name, size/1024)
            results.append(CrawlResult(url=url, filename=filename, pdf_path=str(out_file),
                                       success=True, file_size=size))
            continue

        if direct_ext:
            logger.info("  [{}/{}] Downloading: {} -> {}", i+1, len(pages), url[:60], out_file.name)
            result = await _download_direct_file(url, out_file)
            result.filename = filename
            results.append(result)
        else:
            logger.info("  [{}/{}] Saving: {} -> {}.pdf", i+1, len(pages), url, filename)
            try:
                result = await asyncio.wait_for(
                    _save_single_pdf(url, out_file, headless=headless, timeout=timeout),
                    timeout=120)
            except asyncio.TimeoutError:
                logger.error("    TIMEOUT (120s): {} — skipping", url)
                result = CrawlResult(url=url, success=False, error="hard_timeout_120s")
            result.filename = filename

            if not result.success and result.error and "Download is starting" in result.error:
                logger.info("    [FALLBACK] Playwright download detected, trying HTTP...")
                dl_path = out_file.parent / (out_file.stem + ".download.pdf")
                result = await _download_direct_file(url, dl_path)
                result.filename = filename
            results.append(result)

        # ── Error detection & retry (profile-driven) ─────────────────────
        profile = get_profile(url)
        _is_error = False
        _error_reason = ""
        if result.success and result.title:
            _t = result.title.lower()
            if any(k in _t for k in profile.error_title_keywords):
                _is_error = True
                _error_reason = f"error_title: {result.title[:50]}"
            elif any(k in _t for k in profile.soft_404_keywords):
                _is_error = True
                _error_reason = f"soft_404: {result.title[:50]}"

        if _is_error:
            logger.warning("    Error page detected (title=%s) — backing off %.0fs...",
                          result.title[:40] if result.title else 'N/A', profile.retry_backoff_sec)
            try:
                out_file.unlink(missing_ok=True)
            except Exception:
                pass
            import time
            time.sleep(profile.retry_backoff_sec)
            result = await _save_single_pdf(url, out_file, headless=headless, timeout=timeout)
            result.filename = filename
            _still_error = False
            if result.success and result.title:
                _t2 = result.title.lower()
                _still_error = any(k in _t2 for k in profile.error_title_keywords)
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

        if result.success:
            entry["title"] = result.title
            entry["file_size"] = result.file_size
            entry["status"] = "saved"
        else:
            entry["status"] = "error"
            entry["error"] = result.error

        effective_delay = max(delay_between, profile.min_delay_between)
        if i < len(pages) - 1:
            logger.info("    waiting {:.1f}s...", effective_delay)
            await asyncio.sleep(effective_delay)

    manifest["saved_at"] = datetime.now(timezone.utc).isoformat()
    manifest["pages"] = pages
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    succeeded = sum(1 for r in results if r.success)
    total_size = sum(r.file_size for r in results if r.success)
    logger.info("=" * 60)
    logger.info("PHASE 2 COMPLETE: {}/{} saved ({:.1f} MB)", succeeded, len(results), total_size/1024/1024)
    logger.info("=" * 60)
    return results


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Core: Profile-driven PDF rendering                                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

async def _save_single_pdf(url, pdf_path, *, headless=True, timeout=30_000):
    return await _render_page_to_pdf(url, pdf_path, headless=headless, timeout=timeout)


async def _render_page_to_pdf(
    url: str, pdf_path: Path, *, headless: bool = True, timeout: int = 30_000,
) -> CrawlResult:
    """Render URL to PDF — all site-specific behavior driven by SiteProfile."""
    from playwright.async_api import async_playwright

    profile = get_profile(url)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()
            await page.set_viewport_size({"width": profile.viewport_width, "height": profile.viewport_height})
            await page.emulate_media(media="screen")
            page.set_default_timeout(90_000)

            await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(profile.wait_after_load_ms)

            # ── Early validation ─────────────────────────────────────────
            title = await page.title()
            info = await page.evaluate(JS.EARLY_PAGE_INFO)

            # Generic: soft-404
            if any(k in title.lower() for k in profile.soft_404_keywords):
                logger.info("    SKIP soft-404: {}.pdf (title='{}')", pdf_path.stem, title[:50])
                await browser.close()
                return CrawlResult(url=url, title=title, success=False, error="skipped_soft_404")

            # Site-specific skip rules
            for rule in profile.skip_rules:
                if rule(info, url):
                    logger.info("    SKIP (rule): {}.pdf (words={})", pdf_path.stem, info["wordCount"])
                    await browser.close()
                    return CrawlResult(url=url, title=title, success=False, error="skipped_by_rule")

            # Generic: interactive/form-heavy
            if info["requiredFields"] >= 2 and info["wordCount"] < 200:
                logger.info("    SKIP interactive: {}.pdf (forms={}, words={})",
                           pdf_path.stem, info["forms"], info["wordCount"])
                await browser.close()
                return CrawlResult(url=url, title=title, success=False, error="skipped_interactive")

            # ── 0. Cookie consent ────────────────────────────────────────
            await page.evaluate(JS.DISMISS_COOKIE_CONSENT)
            await page.wait_for_timeout(500)

            # ── 1. Content loading ───────────────────────────────────────
            await page.evaluate(JS.FORCE_LAZY_IMAGES)
            await page.evaluate(JS.SCROLL_TO_BOTTOM)

            # ── 2. Generic content expansion ─────────────────────────────
            await page.evaluate(JS.EXPAND_DETAILS)

            await page.evaluate(JS.EXPAND_SHOW_MORE)
            await page.wait_for_timeout(1000)

            await page.evaluate(JS.EXPAND_GENERIC_TABS)
            await page.wait_for_timeout(1000)

            await page.evaluate(JS.EXPAND_BOOTSTRAP_COLLAPSE)
            await page.wait_for_timeout(1000)

            # ── 3. Site-specific expansion (from profile) ────────────────
            for js_code, wait_ms in profile.extra_expansion_steps:
                await page.evaluate(js_code)
                if wait_ms > 0:
                    await page.wait_for_timeout(wait_ms)

            # ── 4. Wait for images ───────────────────────────────────────
            await page.evaluate(JS.WAIT_FOR_IMAGES)

            # ── 5. Noise removal ─────────────────────────────────────────
            await page.evaluate(JS.DISMISS_COOKIE_CONSENT)   # second pass
            await page.evaluate(JS.REMOVE_POPUPS_AND_OVERLAYS)
            await page.evaluate(JS.REMOVE_GENERIC_CHATBOTS)

            if profile.extra_noise_removal_js:
                await page.evaluate(profile.extra_noise_removal_js)

            # ── 6. Final preparation ─────────────────────────────────────
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            # Print CSS
            if profile.print_css:
                await page.add_style_tag(content=profile.print_css)

            # Pre-PDF cleanup JS
            if profile.pre_pdf_js:
                await page.evaluate(profile.pre_pdf_js)

            # Source URL banner
            if profile.inject_source_banner:
                capture_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                await page.evaluate(JS.SOURCE_BANNER, {
                    "url": url, "date": capture_date,
                    "borderColor": profile.banner_border_color,
                })

            # ── Save PDF ─────────────────────────────────────────────────
            await page.pdf(
                path=str(pdf_path), width="1280px", print_background=True,
                margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"})
            await browser.close()

        file_size = pdf_path.stat().st_size
        logger.info("    saved: {}.pdf ({:.1f} KB) '{}'", pdf_path.stem, file_size/1024, title[:50])
        return CrawlResult(url=url, pdf_path=str(pdf_path), title=title,
                           success=True, file_size=file_size)

    except Exception as e:
        logger.error("    FAILED: {} - {}", url[:60], e)
        return CrawlResult(url=url, success=False, error=str(e))


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Combined: discover → save                                                ║
# ╚════════════════════════════════════════════════════════════════════════════╝

async def crawl_and_save_pdfs(
    seed_url: str, *, persona_slug: str = "general", max_depth: int = 2,
    max_pages: int = 20, headless: bool = True, delay_between: float = 2.0,
    output_dir: Path | str = _DEFAULT_OUTPUT_DIR,
) -> list[CrawlResult]:
    manifest_path = await discover_urls(
        seed_url, persona_slug=persona_slug, max_depth=max_depth,
        max_pages=max_pages, headless=headless, output_dir=output_dir)
    return await save_pdfs_from_manifest(
        manifest_path, headless=headless, delay_between=delay_between)
