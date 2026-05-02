"""web_crawler — Crawl4AI wrapper for single/multi-URL crawling.

Responsibilities:
    - Crawl a URL or list of URLs via Crawl4AI AsyncWebCrawler
    - Return clean, LLM-ready Markdown (fit_markdown preferred)
    - Handle timeouts, retries, and error logging
    - Optionally follow internal links for deeper discovery

Design choices:
    - headless=True by default (configurable via API for debugging)
    - PruningContentFilter removes nav/footer/cookie boilerplate
    - CacheMode.BYPASS for freshest content (government pages update often)
    - Timeout 30s per page (gov sites are slow but not JS-heavy)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class CrawlResult:
    """Result from crawling a single URL."""

    url: str
    markdown: str  # clean Markdown content
    title: str = ""
    success: bool = True
    error: str | None = None
    word_count: int = 0
    links_found: int = 0
    heading_anchors: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _extract_heading_anchors(html: str) -> dict[str, str]:
    """Extract heading text → HTML id mapping from raw HTML.

    Parses <h2 id="xxx"> and <h3 id="xxx"> tags to build
    a lookup table for citation anchor links.
    """
    import re

    anchors: dict[str, str] = {}
    # Match <h2 id="some-id">Heading Text</h2> and <h3 ...>
    pattern = re.compile(
        r'<h[23][^>]*\bid=["\']([^"\']+)["\'][^>]*>(.*?)</h[23]>',
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(html):
        anchor_id = m.group(1).strip()
        # Strip inner HTML tags from heading text
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if text and anchor_id:
            anchors[text] = anchor_id
    return anchors


async def crawl_url(
    url: str,
    *,
    timeout: int = 30_000,
    remove_overlay: bool = True,
    headless: bool = True,
) -> CrawlResult:
    """Crawl a single URL and return clean Markdown.

    Uses Crawl4AI's AsyncWebCrawler with:
        - PruningContentFilter to strip boilerplate
        - fit_markdown for AI-optimized output
        - Headless Chromium via Playwright

    Args:
        url: Target URL to crawl.
        timeout: Page load timeout in milliseconds.
        remove_overlay: Whether to dismiss cookie/consent popups.

    Returns:
        CrawlResult with clean Markdown or error details.
    """
    try:
        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    except ImportError as e:
        return CrawlResult(
            url=url, markdown="", success=False,
            error=f"crawl4ai not installed: {e}",
        )

    browser_config = BrowserConfig(
        headless=headless,
        verbose=False,
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,  # Always fetch fresh content
        page_timeout=timeout,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.3,       # Lower than default 0.48 — gov pages
                threshold_type="fixed",  # need more inclusive filtering
                min_word_threshold=0,
            ),
        ),
        remove_overlay_elements=remove_overlay,
    )

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

            if not result.success:
                return CrawlResult(
                    url=url, markdown="", success=False,
                    error=result.error_message or "Crawl failed (unknown reason)",
                )

            # Prefer fit_markdown (noise-filtered), fall back to raw if too short
            md = ""
            if result.markdown:
                fit = result.markdown.fit_markdown or ""
                raw = result.markdown.raw_markdown or ""
                # If fit_markdown pruned too aggressively (<50 words), use raw
                md = fit if len(fit.split()) >= 50 else raw

            title = result.metadata.get("title", "") if result.metadata else ""
            word_count = len(md.split()) if md else 0
            links_count = len(result.links.get("internal", [])) if result.links else 0

            # Extract heading → anchor ID mapping from raw HTML
            anchors = _extract_heading_anchors(result.html or "")

            logger.info(
                "Crawled {} — {} words, {} links, {} anchors, title='{}'",
                url, word_count, links_count, len(anchors), title[:60],
            )

            return CrawlResult(
                url=url,
                markdown=md,
                title=title,
                success=True,
                word_count=word_count,
                links_found=links_count,
                heading_anchors=anchors,
                metadata={
                    "status_code": result.status_code,
                    "response_headers": dict(result.response_headers)
                    if result.response_headers else {},
                },
            )

    except Exception as e:
        logger.error("Crawl error for {}: {}", url, e)
        return CrawlResult(
            url=url, markdown="", success=False, error=str(e),
        )


async def crawl_urls(
    urls: list[str],
    *,
    timeout: int = 30_000,
    max_concurrent: int = 3,
) -> list[CrawlResult]:
    """Crawl multiple URLs with controlled concurrency.

    Args:
        urls: List of target URLs.
        timeout: Per-page timeout in ms.
        max_concurrent: Max simultaneous browser tabs.

    Returns:
        List of CrawlResult, one per URL (order preserved).
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _limited_crawl(url: str) -> CrawlResult:
        async with semaphore:
            return await crawl_url(url, timeout=timeout)

    results = await asyncio.gather(
        *[_limited_crawl(u) for u in urls],
        return_exceptions=True,
    )

    # Convert exceptions to failed CrawlResults
    final: list[CrawlResult] = []
    for url, r in zip(urls, results):
        if isinstance(r, Exception):
            final.append(CrawlResult(
                url=url, markdown="", success=False, error=str(r),
            ))
        else:
            final.append(r)

    succeeded = sum(1 for r in final if r.success)
    logger.info("Batch crawl: {}/{} succeeded", succeeded, len(urls))
    return final


async def deep_crawl_url(
    url: str,
    *,
    max_depth: int = 2,
    max_pages: int = 20,
    timeout: int = 30_000,
    remove_overlay: bool = True,
    headless: bool = True,
) -> list[CrawlResult]:
    """Deep-crawl a URL: discover same-domain sub-pages via BFS, then crawl each.

    Uses Crawl4AI's BFSDeepCrawlStrategy to follow internal links up to `max_depth`
    levels. Constrains the crawl to same-domain pages only.

    Args:
        url: Seed URL to start crawling from.
        max_depth: How many link-levels deep to follow (default 2).
        max_pages: Maximum total pages to crawl (safety cap).
        timeout: Per-page load timeout in ms.
        remove_overlay: Whether to dismiss cookie/consent popups.

    Returns:
        List of CrawlResult for seed page + discovered sub-pages.
    """
    try:
        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    except ImportError:
        logger.error("crawl4ai not installed — cannot deep crawl")
        return [CrawlResult(url=url, markdown="", success=False, error="crawl4ai not installed")]

    browser_config = BrowserConfig(
        headless=headless,
        extra_args=["--disable-gpu", "--no-sandbox"],
    )

    deep_strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth,
        include_external=False,
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=timeout,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.45,
                threshold_type="fixed",
                min_word_threshold=30,
            ),
        ),
        remove_overlay_elements=remove_overlay,
        deep_crawl_strategy=deep_strategy,
    )

    results: list[CrawlResult] = []
    pages_crawled = 0

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            async for result in await crawler.arun(url=url, config=run_config):
                if pages_crawled >= max_pages:
                    logger.warning("Deep crawl hit max_pages cap ({}), stopping", max_pages)
                    break

                if not result.success:
                    results.append(CrawlResult(
                        url=result.url or url,
                        markdown="",
                        success=False,
                        error=result.error_message or "Sub-page crawl failed",
                    ))
                    pages_crawled += 1
                    continue

                md = ""
                if result.markdown:
                    fit = result.markdown.fit_markdown or ""
                    raw = result.markdown.raw_markdown or ""
                    md = fit if len(fit.split()) >= 50 else raw

                title = result.metadata.get("title", "") if result.metadata else ""
                word_count = len(md.split()) if md else 0
                anchors = _extract_heading_anchors(result.html or "")

                results.append(CrawlResult(
                    url=result.url or url,
                    markdown=md,
                    title=title,
                    success=True,
                    word_count=word_count,
                    links_found=len(result.links.get("internal", [])) if result.links else 0,
                    heading_anchors=anchors,
                    metadata={
                        "status_code": result.status_code,
                        "depth": pages_crawled,
                    },
                ))
                pages_crawled += 1

                logger.info(
                    "Deep crawl [{}/{}] {} — {} words",
                    pages_crawled, max_pages, (result.url or url)[:80], word_count,
                )

    except Exception as e:
        logger.error("Deep crawl error for {}: {}", url, e)
        if not results:
            results.append(CrawlResult(url=url, markdown="", success=False, error=str(e)))

    succeeded = sum(1 for r in results if r.success)
    logger.info("Deep crawl complete: {} pages ({} succeeded) from {}", len(results), succeeded, url)
    return results
