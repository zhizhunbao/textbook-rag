"""crawling — URL discovery + full-page PDF archival for web data sources.

Two-phase pipeline:
    Phase 1: crawl4ai BFS → manifest.json (URL index)
    Phase 2: Playwright page.pdf() → meaningful PDF files

Downstream: MinerU processes PDFs → LlamaIndex Documents → ChromaDB.
"""

from engine_v2.crawling.web_crawler import (
    discover_urls,
    save_pdfs_from_manifest,
    crawl_and_save_pdfs,
    CrawlResult,
)
from engine_v2.crawling.ingest_web import ingest_web_source

__all__ = [
    "discover_urls",
    "save_pdfs_from_manifest",
    "crawl_and_save_pdfs",
    "CrawlResult",
    "ingest_web_source",
]
