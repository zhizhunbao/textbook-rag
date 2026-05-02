"""crawling — Crawl4AI integration for web data-source ingestion.

Crawls persona data-source URLs → clean Markdown → LlamaIndex Documents
→ ChromaDB vector store.  Designed for government / public HTML pages
(IRCC, Ontario.ca, CIC, etc.) — no heavy anti-bot needed.
"""

from engine_v2.crawling.web_crawler import crawl_url, crawl_urls
from engine_v2.crawling.ingest_web import ingest_web_source

__all__ = ["crawl_url", "crawl_urls", "ingest_web_source"]
