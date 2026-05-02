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

from engine_v2.crawling.web_crawler import CrawlResult, crawl_url, crawl_urls
from engine_v2.ingestion.pipeline import get_vector_store, _payload_headers
from engine_v2.settings import PAYLOAD_URL


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

    docs: list[Document]= []
    for i, section in enumerate(sections):
        text = section["text"].strip()
        if not text or len(text) < 20:  # Skip trivially short sections
            continue

        # Deterministic ID: hash of URL + section index
        doc_id = hashlib.md5(
            f"{crawl_result.url}::{i}::{section['heading'][:50]}".encode()
        ).hexdigest()

        metadata: dict[str, Any] = {
            "source_url": crawl_result.url,
            "source_title": crawl_result.title or "",
            "section_heading": section["heading"],
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
                "crawled_at", "section_index", "data_source_id",
            ],
            excluded_embed_metadata_keys=[
                "crawled_at", "source_url", "data_source_id",
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


async def ingest_web_source(
    url: str,
    *,
    persona_slug: str | None = None,
    collection_name: str | None = None,
    data_source_id: str | None = None,
) -> dict[str, Any]:
    """Full pipeline: Crawl URL → Markdown → Embed → ChromaDB.

    Args:
        url: Web page URL to crawl and ingest.
        persona_slug: Optional persona slug for metadata tagging.
        collection_name: ChromaDB collection override.
            Defaults to persona's collection or textbook_chunks.
        data_source_id: Payload CMS data-source ID (for status updates).

    Returns:
        dict with: url, chunk_count, status, collection, errors
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
        "Web ingest: url={}, persona={}, collection={}",
        url[:80], persona_slug, target_collection,
    )

    # Step 2: Crawl the URL
    crawl_result = await crawl_url(url)
    if not crawl_result.success:
        error_msg = f"Crawl failed: {crawl_result.error}"
        logger.error(error_msg)
        _update_data_source_status(data_source_id, "error", error=error_msg)
        return {
            "url": url,
            "chunk_count": 0,
            "status": "error",
            "collection": target_collection,
            "errors": [error_msg],
        }

    # Step 3: Convert Markdown → LlamaIndex Documents
    documents = _markdown_to_documents(
        crawl_result,
        persona_slug=persona_slug,
        source_id=data_source_id,
    )
    if not documents:
        msg = f"No content extracted from {url}"
        logger.warning(msg)
        _update_data_source_status(data_source_id, "empty", error=msg)
        return {
            "url": url,
            "chunk_count": 0,
            "status": "empty",
            "collection": target_collection,
            "errors": [msg],
        }

    logger.info("Extracted {} documents from {}", len(documents), url[:60])

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
        last_synced_at=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "url": url,
        "chunk_count": len(nodes),
        "word_count": crawl_result.word_count,
        "title": crawl_result.title,
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
    last_synced_at: str | None = None,
    error: str | None = None,
) -> None:
    """Update a data-source record in Payload CMS."""
    if not data_source_id:
        return

    import httpx

    body: dict[str, Any] = {"syncStatus": status}
    if chunk_count is not None:
        body["chunkCount"] = chunk_count
    if last_synced_at:
        body["lastSyncedAt"] = last_synced_at
    if error:
        body["syncError"] = error

    try:
        httpx.patch(
            f"{PAYLOAD_URL}/api/data-sources/{data_source_id}",
            json=body,
            headers=_payload_headers(),
            timeout=15.0,
        ).raise_for_status()
        logger.info("Updated data-source {} status → {}", data_source_id, status)
    except Exception as e:
        logger.warning("Failed to update data-source {}: {}", data_source_id, e)
