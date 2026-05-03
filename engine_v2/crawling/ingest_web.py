"""ingest_web — Crawl4AI → LlamaIndex → ChromaDB ingestion pipeline.

Responsibilities:
    - Crawl a data-source URL via Crawl4AI
    - Convert Markdown to LlamaIndex Documents
    - Run through IngestionPipeline (embed → ChromaDB)
    - Update Payload CMS data-source status

Flow:
    URL → Crawl4AI (Markdown) → LlamaIndex Document[]
    → IngestionPipeline(embed_model, ChromaVectorStore)
    → Payload CMS status update

This complements the existing PDF pipeline (MinerUReader → pipeline.py)
by adding web content ingestion for persona data sources.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import Document
from llama_index.core.settings import Settings
from loguru import logger

from engine_v2.crawling.web_crawler import CrawlResult, crawl_and_save_pdfs
from engine_v2.ingestion.pipeline import get_vector_store, _payload_headers
from engine_v2.settings import PAYLOAD_URL


def _slugify(text: str) -> str:
    """Convert heading text to a URL-safe anchor slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


def _markdown_to_documents(
    crawl_result: CrawlResult,
    *,
    persona_slug: str | None = None,
    source_id: str | None = None,
) -> list[Document]:
    """Convert a CrawlResult's Markdown into LlamaIndex Documents.

    Chunking strategy: split by Markdown headers (## and ###).
    Each section becomes one Document with rich metadata.
    """
    if not crawl_result.markdown or not crawl_result.success:
        return []

    md = crawl_result.markdown
    sections = _split_by_headers(md)
    anchors = crawl_result.heading_anchors

    docs: list[Document]= []
    for i, section in enumerate(sections):
        text = section["text"].strip()
        if not text or len(text) < 20:  # Skip trivially short sections
            continue

        # Deterministic ID: hash of URL + section index
        doc_id = hashlib.md5(
            f"{crawl_result.url}::{i}::{section['heading'][:50]}".encode()
        ).hexdigest()

        # Resolve anchor: exact HTML id match → slugified fallback
        heading = section["heading"]
        anchor = anchors.get(heading) or _slugify(heading)

        metadata: dict[str, Any] = {
            "source_url": crawl_result.url,
            "source_title": crawl_result.title or "",
            "section_heading": heading,
            "section_anchor": anchor,
            "section_index": i,
            "content_type": "text",
            "category": "web_crawl",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "word_count": len(text.split()),
        }
        if persona_slug:
            metadata["persona_slug"] = persona_slug
        if source_id:
            metadata["data_source_id"] = source_id

        doc = Document(
            text=text,
            id_=doc_id,
            metadata=metadata,
            excluded_llm_metadata_keys=[
                "crawled_at", "section_index", "section_anchor",
                "data_source_id",
            ],
            excluded_embed_metadata_keys=[
                "crawled_at", "source_url", "section_anchor",
                "data_source_id",
            ],
        )
        docs.append(doc)

    return docs


def _split_by_headers(markdown: str) -> list[dict[str, str]]:
    """Split Markdown text by ## and ### headers into sections.

    Returns list of {"heading": str, "text": str} dicts.
    """
    import re

    sections: list[dict[str, str]] = []
    # Split on lines starting with ## or ### (but not # or ####)
    pattern = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)

    matches = list(pattern.finditer(markdown))
    if not matches:
        # No headers found — treat entire content as one section
        return [{"heading": "(root)", "text": markdown}]

    # Content before first header
    pre = markdown[: matches[0].start()].strip()
    if pre:
        sections.append({"heading": "(intro)", "text": pre})

    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        text = f"## {heading}\n\n{markdown[start:end].strip()}"
        sections.append({"heading": heading, "text": text})

    return sections


def _archive_crawl_result(crawl_result: CrawlResult, persona_slug: str | None) -> None:
    """Save the crawled Markdown to disk for auditing and debugging."""
    import re
    from pathlib import Path

    # Base directory
    base_dir = Path("data/crawled_web")

    # Subdirectory by persona
    slug = persona_slug or "general"
    out_dir = base_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Safe filename from URL
    safe_name = re.sub(r"[^\w\-]", "_", crawl_result.url)
    safe_name = safe_name.strip("_")
    
    # Cap length to avoid OS filename limits
    if len(safe_name) > 100:
        safe_name = safe_name[:100].strip("_")

    out_path = out_dir / f"{safe_name}.md"

    try:
        # Save URL at top of file for reference
        content = f"<!-- URL: {crawl_result.url} -->\n\n{crawl_result.markdown}"
        out_path.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to archive {}: {}", crawl_result.url, e)


async def ingest_web_source(
    url: str,
    *,
    persona_slug: str | None = None,
    collection_name: str | None = None,
    data_source_id: str | None = None,
    deep_crawl: bool = True,
    max_depth: int = 2,
    max_pages: int = 20,
    headless: bool = True,
) -> dict[str, Any]:
    """Full pipeline: Crawl URL → Markdown → Embed → ChromaDB.

    Args:
        url: Web page URL to crawl and ingest.
        persona_slug: Optional persona slug for metadata tagging.
        collection_name: ChromaDB collection override.
            Defaults to persona's collection or textbook_chunks.
        data_source_id: Payload CMS data-source ID (for status updates).
        deep_crawl: If True, follow same-domain links (BFS) to discover sub-pages.
        max_depth: Max link depth for deep crawl (default 2).
        max_pages: Max pages to crawl in deep mode (default 20).

    Returns:
        dict with: url, chunk_count, pages_crawled, status, collection, errors
    """
    from engine_v2.personas.registry import get_collection_name

    # Step 1: Resolve target collection
    if collection_name:
        target_collection = collection_name
    elif persona_slug:
        target_collection = get_collection_name(persona_slug)
    else:
        from engine_v2.settings import CHROMA_COLLECTION
        target_collection = CHROMA_COLLECTION

    logger.info(
        "Web ingest: url={}, persona={}, collection={}, deep={}",
        url[:80], persona_slug, target_collection, deep_crawl,
    )

    # Step 2: Crawl the URL (single or deep)
    if deep_crawl:
        crawl_results = await deep_crawl_url(
            url, max_depth=max_depth, max_pages=max_pages, headless=headless,
        )
    else:
        single_result = await crawl_url(url, headless=headless)
        crawl_results = [single_result]

    successful_crawls = [r for r in crawl_results if r.success]
    if not successful_crawls:
        error_msg = f"Crawl failed for all pages from {url}"
        if crawl_results:
            error_msg = f"Crawl failed: {crawl_results[0].error}"
        logger.error(error_msg)
        _update_data_source_status(data_source_id, "error", error=error_msg)
        return {
            "url": url,
            "chunk_count": 0,
            "pages_crawled": 0,
            "status": "error",
            "collection": target_collection,
            "errors": [error_msg],
        }

    # Step 3: Convert Markdown → LlamaIndex Documents (all pages)
    documents: list[Document] = []
    for crawl_result in successful_crawls:
        _archive_crawl_result(crawl_result, persona_slug)
        docs = _markdown_to_documents(
            crawl_result,
            persona_slug=persona_slug,
            source_id=data_source_id,
        )
        documents.extend(docs)

    if not documents:
        msg = f"No content extracted from {url} ({len(successful_crawls)} pages crawled)"
        logger.warning(msg)
        _update_data_source_status(data_source_id, "empty", error=msg)
        return {
            "url": url,
            "chunk_count": 0,
            "pages_crawled": len(successful_crawls),
            "status": "empty",
            "collection": target_collection,
            "errors": [msg],
        }

    logger.info(
        "Extracted {} documents from {} pages (seed: {})",
        len(documents), len(successful_crawls), url[:60],
    )

    # Step 4: Run LlamaIndex IngestionPipeline
    vector_store = get_vector_store(collection_name=target_collection)
    pipeline = IngestionPipeline(
        transformations=[
            Settings.embed_model,  # auto-embed via HuggingFace
        ],
        vector_store=vector_store,  # auto-upsert into ChromaDB
    )
    nodes = pipeline.run(documents=documents, show_progress=False)
    logger.info("Ingested {} nodes into collection '{}'", len(nodes), target_collection)

    # Step 5: Update Payload CMS data-source status
    _update_data_source_status(
        data_source_id,
        "synced",
        chunk_count=len(nodes),
        last_synced=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "url": url,
        "chunk_count": len(nodes),
        "pages_crawled": len(successful_crawls),
        "total_words": sum(r.word_count for r in successful_crawls),
        "status": "synced",
        "collection": target_collection,
        "errors": [],
    }


async def ingest_web_sources_batch(
    sources: list[dict[str, Any]],
    *,
    max_concurrent: int = 3,
) -> list[dict[str, Any]]:
    """Batch ingest multiple web data sources.

    Each source dict should have:
        - url (required)
        - persona_slug (optional)
        - collection_name (optional)
        - data_source_id (optional)

    Returns list of result dicts (one per source).
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[dict[str, Any]] = []

    async def _ingest_one(src: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await ingest_web_source(
                url=src["url"],
                persona_slug=src.get("persona_slug"),
                collection_name=src.get("collection_name"),
                data_source_id=src.get("data_source_id"),
            )

    tasks = [_ingest_one(s) for s in sources]
    raw = await asyncio.gather(*tasks, return_exceptions=True)

    for src, r in zip(sources, raw):
        if isinstance(r, Exception):
            results.append({
                "url": src["url"],
                "chunk_count": 0,
                "status": "error",
                "errors": [str(r)],
            })
        else:
            results.append(r)

    succeeded = sum(1 for r in results if r.get("status") == "synced")
    logger.info("Batch web ingest: {}/{} succeeded", succeeded, len(sources))
    return results


# ── Payload CMS helpers ─────────────────────────────────────────────────────

def _update_data_source_status(
    data_source_id: str | None,
    status: str,
    *,
    chunk_count: int | None = None,
    last_synced: str | None = None,
    error: str | None = None,
) -> None:
    """Update a data-source record in Payload CMS."""
    if not data_source_id:
        return

    import httpx

    body: dict[str, Any] = {"syncStatus": status}
    if chunk_count is not None:
        body["chunkCount"] = chunk_count
    if last_synced:
        body["lastSynced"] = last_synced
    if error:
        body["syncError"] = error

    url = f"{PAYLOAD_URL}/api/data-sources/{data_source_id}"

    try:
        resp = httpx.patch(url, json=body, headers=_payload_headers(), timeout=15.0)
        if resp.status_code == 403:
            # Token expired — force re-login and retry once
            logger.info("Token expired, refreshing for data-source {}", data_source_id)
            resp = httpx.patch(url, json=body, headers=_payload_headers(force_refresh=True), timeout=15.0)
        resp.raise_for_status()
        logger.info("Updated data-source {} status → {}", data_source_id, status)
    except Exception as e:
        logger.warning("Failed to update data-source {}: {}", data_source_id, e)
