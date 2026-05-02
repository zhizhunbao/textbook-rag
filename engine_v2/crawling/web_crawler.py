"""web_crawler — Crawl4AI wrapper for single/multi-URL crawling.

Responsibilities:
    - Crawl a URL or list of URLs via Crawl4AI AsyncWebCrawler
    - Return clean, LLM-ready Markdown (fit_markdown preferred)
    - Handle timeouts, retries, and error logging
    - Optionally follow internal links for deeper discovery

Design choices:
    - headless=True always (no GUI needed on server)
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
    metadata: dict[str, Any] = field(default_factory=dict)


async def crawl_url(
    url: str,
    *,
    timeout: int = 30_000,
    remove_overlay: bool = True,
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
        headless=True,
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

            logger.info(
                "Crawled {} — {} words, {} links, title='{}'",
                url, word_count, links_count, title[:60],
            )

            return CrawlResult(
                url=url,
                markdown=md,
                title=title,
                success=True,
                word_count=word_count,
                links_found=links_count,
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
