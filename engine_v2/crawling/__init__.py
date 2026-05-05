"""crawling — URL discovery + full-page PDF archival for web data sources.

Two-phase pipeline:
    Phase 1: crawl4ai BFS → manifest.json (URL index)
    Phase 2: Playwright page.pdf() → meaningful PDF files

Downstream: MinerU processes PDFs → LlamaIndex Documents → ChromaDB.
"""

# v2: profile-driven engine (site-specific logic in sites/*.py)
from engine_v2.crawling.web_crawler_v2 import (
    discover_urls,
    save_pdfs_from_manifest,
    crawl_and_save_pdfs,
    CrawlResult,
)

# NOTE: ingest_web (Crawl4AI → ChromaDB) is deprecated.
# Active pipeline: MinerU → PDF → LlamaIndex → ChromaDB.

__all__ = [
    "discover_urls",
    "save_pdfs_from_manifest",
    "crawl_and_save_pdfs",
    "CrawlResult",
]
