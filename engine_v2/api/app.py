"""FastAPI application — thin internal API for Payload CMS.

Initialises LlamaIndex Settings on startup via lifespan.
"""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engine_v2.settings import CORS_ORIGINS, init_settings
from engine_v2.api.routes import (
    books, classify, delete, embeddings, evaluation, health, ingest, llms,
    query, questions, retrievers, sources, suggest,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise LlamaIndex Settings (LLM + embed model)."""
    # Install thread-aware stdout/stderr capture for SSE log streaming
    from engine_v2.api.log_capture import install as install_log_capture
    install_log_capture()

    init_settings()
    logger.info("LlamaIndex Settings initialised")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Textbook RAG Engine v2",
        description="LlamaIndex-native internal API — called by Payload CMS",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.error("Unhandled %s %s:\n%s", request.method, request.url, tb)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb},
        )

    app.include_router(health.router, prefix="/engine")
    app.include_router(books.router, prefix="/engine")
    app.include_router(classify.router, prefix="/engine")
    app.include_router(delete.router, prefix="/engine")
    app.include_router(embeddings.router, prefix="/engine")
    app.include_router(query.router, prefix="/engine")
    app.include_router(ingest.router, prefix="/engine")
    app.include_router(questions.router, prefix="/engine")
    app.include_router(llms.router, prefix="/engine")
    app.include_router(retrievers.router, prefix="/engine")
    app.include_router(evaluation.router, prefix="/engine")
    app.include_router(sources.router, prefix="/engine")
    print(f"[DEBUG] sources.router registered, routes: {[r.path for r in sources.router.routes]}")
    app.include_router(suggest.router, prefix="/engine")

    return app


app = create_app()
