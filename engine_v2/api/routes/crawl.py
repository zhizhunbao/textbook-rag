"""crawl — API routes for Crawl4AI web content ingestion.

Provides endpoints to:
    - Preview-crawl a URL (returns Markdown without ingesting)
    - Ingest a single URL into ChromaDB
    - Batch-ingest all enabled data sources for a persona
    - Sync all enabled autoSync data sources

These complement the existing PDF-based sources/discover endpoint.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(tags=["crawl"])


# ── Request / Response schemas ───────────────────────────────────────────────

class CrawlPreviewRequest(BaseModel):
    """Preview a URL — crawl and return Markdown without ingesting."""
    url: str = Field(..., description="URL to crawl")


class CrawlPreviewResponse(BaseModel):
    """Preview result with Markdown content."""
    success: bool
    url: str
    title: str = ""
    markdown: str = ""
    word_count: int = 0
    error: Optional[str] = None


class IngestWebRequest(BaseModel):
    """Ingest a web URL into ChromaDB."""
    url: str = Field(..., description="URL to crawl and ingest")
    persona_slug: Optional[str] = Field(
        None, description="Persona slug for collection targeting"
    )
    collection_name: Optional[str] = Field(
        None, description="Override ChromaDB collection name"
    )
    data_source_id: Optional[str] = Field(
        None, description="Payload data-source ID (for status updates)"
    )
    deep_crawl: bool = Field(
        True, description="Follow same-domain links to discover sub-pages"
    )
    max_depth: int = Field(2, description="Max link depth for deep crawl")
    max_pages: int = Field(20, description="Max pages to crawl")
    headless: bool = Field(
        True, description="Run browser in headless mode (False = show browser window)"
    )


class IngestWebResponse(BaseModel):
    """Result of a web ingestion."""
    success: bool
    url: str
    chunk_count: int = 0
    pages_crawled: int = 0
    total_words: int = 0
    collection: str = ""
    status: str = ""
    errors: list[str] = []


class SyncPersonaRequest(BaseModel):
    """Sync all enabled data sources for a persona."""
    persona_slug: str = Field(..., description="Persona slug to sync")


class SyncPersonaResponse(BaseModel):
    """Result of a persona sync."""
    success: bool
    persona_slug: str
    total_sources: int = 0
    synced: int = 0
    failed: int = 0
    results: list[IngestWebResponse] = []
    error: Optional[str] = None


class SyncAllRequest(BaseModel):
    """Sync all enabled autoSync data sources across all personas."""
    dry_run: bool = Field(
        False, description="If true, list sources without crawling"
    )


class SyncAllResponse(BaseModel):
    """Result of syncing all data sources."""
    success: bool
    total_sources: int = 0
    synced: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[dict] = []
    error: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/crawl/preview", response_model=CrawlPreviewResponse)
async def crawl_preview(req: CrawlPreviewRequest) -> CrawlPreviewResponse:
    """Preview-crawl a URL — returns clean Markdown without ingesting.

    Useful for testing crawl quality before committing to ingest.
    """
    from engine_v2.crawling.web_crawler import crawl_url

    result = await crawl_url(req.url)

    return CrawlPreviewResponse(
        success=result.success,
        url=result.url,
        title=result.title,
        markdown=result.markdown[:50_000],  # Cap preview at 50k chars
        word_count=result.word_count,
        error=result.error,
    )


@router.post("/crawl/ingest", response_model=IngestWebResponse)
async def ingest_web(req: IngestWebRequest) -> IngestWebResponse:
    """Crawl a URL and ingest its content into ChromaDB.

    Full pipeline: URL → Crawl4AI → Markdown → Embed → ChromaDB.
    """
    from engine_v2.crawling.ingest_web import ingest_web_source

    result = await ingest_web_source(
        url=req.url,
        persona_slug=req.persona_slug,
        collection_name=req.collection_name,
        data_source_id=req.data_source_id,
        deep_crawl=req.deep_crawl,
        max_depth=req.max_depth,
        max_pages=req.max_pages,
        headless=req.headless,
    )

    return IngestWebResponse(
        success=result.get("status") == "synced",
        url=result.get("url", req.url),
        chunk_count=result.get("chunk_count", 0),
        pages_crawled=result.get("pages_crawled", 0),
        total_words=result.get("total_words", 0),
        collection=result.get("collection", ""),
        status=result.get("status", ""),
        errors=result.get("errors", []),
    )


@router.post("/crawl/sync-persona", response_model=SyncPersonaResponse)
async def sync_persona(req: SyncPersonaRequest) -> SyncPersonaResponse:
    """Sync all enabled data sources for a specific persona.

    Fetches data sources from Payload CMS, filters by persona slug
    and enabled=true, then crawls and ingests each one.
    """
    import httpx
    from engine_v2.ingestion.pipeline import _payload_headers
    from engine_v2.settings import PAYLOAD_URL
    from engine_v2.crawling.ingest_web import ingest_web_source

    try:
        # Fetch data sources for this persona from Payload CMS
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{PAYLOAD_URL}/api/data-sources",
                params={
                    "where[persona.slug][equals]": req.persona_slug,
                    "where[enabled][equals]": "true",
                    "limit": "100",
                },
                headers=_payload_headers(),
            )
            resp.raise_for_status()
            sources = resp.json().get("docs", [])

        if not sources:
            return SyncPersonaResponse(
                success=True,
                persona_slug=req.persona_slug,
                total_sources=0,
                error="No enabled data sources found for this persona",
            )

        # Ingest each source
        results: list[IngestWebResponse] = []
        synced = 0
        failed = 0

        for src in sources:
            url = src.get("discoveryUrl", "")
            if not url:
                continue

            result = await ingest_web_source(
                url=url,
                persona_slug=req.persona_slug,
                data_source_id=str(src.get("id", "")),
            )

            resp_item = IngestWebResponse(
                success=result.get("status") == "synced",
                url=url,
                chunk_count=result.get("chunk_count", 0),
                word_count=result.get("word_count", 0),
                title=result.get("title", ""),
                collection=result.get("collection", ""),
                status=result.get("status", ""),
                errors=result.get("errors", []),
            )
            results.append(resp_item)

            if resp_item.success:
                synced += 1
            else:
                failed += 1

        return SyncPersonaResponse(
            success=True,
            persona_slug=req.persona_slug,
            total_sources=len(sources),
            synced=synced,
            failed=failed,
            results=results,
        )

    except Exception as e:
        logger.exception("Persona sync failed for {}", req.persona_slug)
        return SyncPersonaResponse(
            success=False,
            persona_slug=req.persona_slug,
            error=str(e),
        )


@router.post("/crawl/sync-all", response_model=SyncAllResponse)
async def sync_all(
    req: SyncAllRequest,
    background_tasks: BackgroundTasks,
) -> SyncAllResponse:
    """Sync all enabled autoSync data sources across all personas.

    If dry_run=true, returns the list of sources without crawling.
    Otherwise, triggers background ingestion for all sources.
    """
    import httpx
    from engine_v2.ingestion.pipeline import _payload_headers
    from engine_v2.settings import PAYLOAD_URL

    try:
        # Fetch all autoSync-enabled data sources
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{PAYLOAD_URL}/api/data-sources",
                params={
                    "where[enabled][equals]": "true",
                    "where[autoSync][equals]": "true",
                    "limit": "200",
                },
                headers=_payload_headers(),
            )
            resp.raise_for_status()
            sources = resp.json().get("docs", [])

        if req.dry_run:
            return SyncAllResponse(
                success=True,
                total_sources=len(sources),
                results=[
                    {
                        "url": s.get("discoveryUrl", ""),
                        "nameEn": s.get("nameEn", ""),
                        "persona": s.get("persona", {}).get("slug", "")
                        if isinstance(s.get("persona"), dict) else "",
                        "syncInterval": s.get("syncInterval", ""),
                    }
                    for s in sources
                ],
            )

        # Run sync in background
        async def _run_sync():
            from engine_v2.crawling.ingest_web import ingest_web_source

            for src in sources:
                url = src.get("discoveryUrl", "")
                if not url:
                    continue

                persona = src.get("persona", {})
                slug = persona.get("slug", "") if isinstance(persona, dict) else ""

                try:
                    await ingest_web_source(
                        url=url,
                        persona_slug=slug or None,
                        data_source_id=str(src.get("id", "")),
                    )
                except Exception as e:
                    logger.error("Sync failed for {}: {}", url, e)

        background_tasks.add_task(asyncio.create_task, _run_sync())

        return SyncAllResponse(
            success=True,
            total_sources=len(sources),
            synced=0,  # Running in background
            error="Sync started in background" if sources else None,
        )

    except Exception as e:
        logger.exception("Sync-all failed")
        return SyncAllResponse(success=False, error=str(e))
