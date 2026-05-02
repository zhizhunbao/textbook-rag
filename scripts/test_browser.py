"""Direct crawl4ai test — bypass Engine API, run crawler directly to see full error."""

import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


async def main():
    browser_config = BrowserConfig(
        headless=False,   # should pop up browser
        verbose=True,
    )

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=30_000,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.3,
                threshold_type="fixed",
                min_word_threshold=0,
            ),
        ),
        remove_overlay_elements=True,
    )

    print("Starting crawler with headless=False...")
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://www.canada.ca/en/services/immigration-citizenship.html",
            config=run_config,
        )
        print(f"Success: {result.success}")
        print(f"Error: {result.error_message}")
        print(f"Status: {result.status_code}")
        if result.markdown:
            fit = result.markdown.fit_markdown or ""
            raw = result.markdown.raw_markdown or ""
            print(f"Fit markdown length: {len(fit)}")
            print(f"Raw markdown length: {len(raw)}")
            print(f"First 300 chars:\n{(fit or raw)[:300]}")
        else:
            print("No markdown returned")


asyncio.run(main())
