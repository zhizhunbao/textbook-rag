"""LLMs routes — Model Hub API endpoints.

Endpoints:
    GET    /engine/llms/providers              — list available LLM providers
    GET    /engine/llms/models                 — current LLM + embed model info
    GET    /engine/llms/library/search         — search curated model catalog (MH-03)
    GET    /engine/llms/library/categories     — list catalog categories
    GET    /engine/llms/benchmark/questions    — list standard benchmark questions
    POST   /engine/llms/models/pull            — SSE stream pull model from Ollama (MH-04)
    POST   /engine/llms/models/test            — run benchmark test on a model
    POST   /engine/llms/models/test-batch      — serial benchmark across multiple models (SSE)
    DELETE /engine/llms/models/{name}          — delete model from Ollama + invalidate cache

Ref: Sprint MH — Ollama Model Hub
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from engine_v2.llms.resolver import is_azure_configured, list_providers
from engine_v2.settings import OLLAMA_BASE_URL

router = APIRouter(prefix="/llms", tags=["llms"])

OLLAMA_TIMEOUT = 30.0


# ============================================================
# Request / Response models
# ============================================================
class PullModelRequest(BaseModel):
    """Request to pull a model from Ollama registry."""
    name: str


class TestModelRequest(BaseModel):
    """Request to run a benchmark test on a single model."""
    model: str
    question: str
    provider: str | None = None


class TestBatchRequest(BaseModel):
    """Request to run benchmark tests across multiple models (serial)."""
    models: list[str]
    questions: list[str]


# ============================================================
# Existing endpoints
# ============================================================
@router.get("/providers")
async def providers():
    """List available LLM providers and their status."""
    return {"providers": list_providers()}


@router.get("/models")
async def models():
    """Return current LLM and embedding model info."""
    from llama_index.core.settings import Settings

    return {
        "llm": {
            "model": str(Settings.llm.metadata.model_name) if Settings.llm else None,
            "provider": "azure_openai" if is_azure_configured() else "ollama",
        },
        "embed_model": {
            "model": str(Settings.embed_model.model_name) if Settings.embed_model else None,
        },
    }




# ============================================================
# MH-03: Search catalog (dynamic — fetches from Ollama + HuggingFace APIs)
# ============================================================
@router.get("/library/search")
async def search_library(
    q: str | None = Query(None, description="Text search query"),
    category: str | None = Query(None, description="Category filter"),
    source: str | None = Query(None, description="Source filter (e.g. 'ollama', 'huggingface')"),
    sort: str | None = Query(None, description="Sort order: 'newest' (default), 'downloads', 'name'"),
    force: bool = Query(False, description="Bypass cache and rebuild catalog from APIs"),
    debug: bool = Query(False, description="Include catalog debug metadata"),
):
    """Search the model catalog (dynamically built from APIs)."""
    from engine_v2.llms import catalog as catalog_module
    from engine_v2.llms.catalog import build_catalog_from_apis, catalog_to_dict, get_catalog

    if force:
        # Full rebuild — bypass stale-while-revalidate cache entirely
        logger.info("Catalog force-rebuild triggered (sync path)")
        all_models = await build_catalog_from_apis()
        # Update cache with fresh data so subsequent page loads benefit
        catalog_module._cache["catalog"] = all_models
        catalog_module._cache["timestamp"] = __import__("time").time()
    else:
        all_models = await get_catalog()

    # Apply filters
    results = all_models
    if category:
        results = [m for m in results if m.category == category]
    if source:
        results = [m for m in results if m.source == source]
    if q:
        _q = q.lower()
        results = [
            m for m in results
            if _q in m.name.lower()
            or _q in m.family.lower()
            or _q in m.display_name.lower()
            or _q in m.description.lower()
        ]
    if sort == "downloads":
        results.sort(key=lambda m: (0 if m.installed else 1, -m.downloads))
    elif sort == "name":
        results.sort(key=lambda m: (0 if m.installed else 1, m.name.lower()))

    payload = {
        "models": [catalog_to_dict(m) for m in results],
        "count": len(results),
    }
    if debug:
        from engine_v2.llms._discovery import fetch_browsable_from_ollama_library
        ollama_names = await fetch_browsable_from_ollama_library(limit=20)
        payload["debug"] = {
            "catalog_file": catalog_module.__file__,
            "ollama_library_count": len(ollama_names),
            "ollama_library_sample": ollama_names[:20],
            "source_counts": {
                "ollama": sum(1 for m in results if m.source == "ollama"),
                "huggingface": sum(1 for m in results if m.source == "huggingface"),
            },
            "force": force,
        }
    return payload


@router.get("/library/categories")
async def list_categories():
    """List available catalog categories."""
    from engine_v2.llms.catalog import CATEGORIES

    return {"categories": CATEGORIES}


@router.post("/library/refresh")
async def refresh_catalog():
    """Force refresh the catalog cache (re-fetch from APIs)."""
    from engine_v2.llms.catalog import invalidate_cache

    invalidate_cache()
    return {"status": "cache_invalidated"}


# ============================================================
# Benchmark questions
# ============================================================
@router.get("/benchmark/questions")
async def list_benchmark_questions(
    category: str | None = Query(None, description="Category filter"),
):
    """List standard benchmark test questions."""
    from engine_v2.llms.prompts import get_benchmark_questions, question_to_dict

    questions = get_benchmark_questions(category=category)
    return {
        "questions": [question_to_dict(q) for q in questions],
        "count": len(questions),
    }


# ============================================================
# MH-04: Pull model from Ollama (SSE stream)
# ============================================================
@router.post("/models/pull")
async def pull_model(req: PullModelRequest):
    """Pull a model from Ollama registry with SSE progress streaming.

    Proxies to Ollama POST /api/pull (stream=true) and relays
    progress events to the frontend as Server-Sent Events.
    """
    logger.info("Pull model — name={}", req.name)

    async def stream_pull() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"name": req.name, "stream": True},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            yield f"data: {json.dumps(data)}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            error_data = {"status": "error", "error": str(exc)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        stream_pull(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Model benchmark test
# ============================================================
@router.post("/models/test")
async def test_model(req: TestModelRequest):
    """Run a benchmark test on a single model.

    Returns latency, token counts, and cost estimate.
    """
    from engine_v2.llms.benchmark import run_benchmark

    logger.info("Test model — model={}, question={}", req.model, req.question[:60])
    result = await run_benchmark(
        model=req.model,
        question=req.question,
        provider=req.provider,
    )
    return result.to_dict()


@router.post("/models/test-batch")
async def test_batch(req: TestBatchRequest):
    """Run benchmark tests across multiple models serially (SSE).

    4060 8GB constraint: models are loaded one at a time.
    Each result is streamed as an SSE event as it completes.
    """
    from engine_v2.llms.benchmark import run_benchmark

    logger.info(
        "Batch test — {} models × {} questions",
        len(req.models), len(req.questions),
    )

    total_tasks = len(req.models) * len(req.questions)

    async def stream_results() -> AsyncGenerator[str, None]:
        completed = 0
        for model in req.models:
            for question in req.questions:
                # Emit "running" status
                running = {
                    "type": "running",
                    "model": model,
                    "question": question[:80],
                    "progress": f"{completed}/{total_tasks}",
                }
                yield f"data: {json.dumps(running)}\n\n"

                # Run benchmark (serial — one model at a time)
                result = await run_benchmark(model=model, question=question)
                completed += 1

                # Emit result
                event = {
                    "type": "result",
                    **result.to_dict(),
                    "progress": f"{completed}/{total_tasks}",
                }
                yield f"data: {json.dumps(event)}\n\n"

                # Small delay to let Ollama unload between models
                await asyncio.sleep(0.1)

        # Emit completion
        done = {"type": "done", "total": completed}
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        stream_results(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# MH-05: Delete model from Ollama
# ============================================================
@router.delete("/models/{name:path}")
async def delete_model(name: str):
    """Delete a model from local Ollama installation + invalidate catalog cache.

    Proxies to Ollama DELETE /api/delete endpoint, then forces
    a catalog rebuild so the UI reflects the change immediately.
    """
    from engine_v2.llms.catalog import invalidate_cache

    logger.info("Delete model — name={}", name)
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.request(
                "DELETE",
                f"{OLLAMA_BASE_URL}/api/delete",
                json={"name": name},
            )
            if resp.status_code == 404:
                return {"status": "not_found", "name": name}
            resp.raise_for_status()
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.error("Failed to delete model {}:\n{}", name, tb)
        return {"status": "error", "name": name, "error": str(exc), "tb": tb}

    # Force catalog rebuild so the model disappears from library
    invalidate_cache()
    return {"status": "deleted", "name": name}
