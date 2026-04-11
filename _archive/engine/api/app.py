"""Engine FastAPI application — thin internal API.

Only Payload CMS calls this API. Not exposed to the public internet.
Endpoints:
  POST /engine/query   → RAGCore.query()
  POST /engine/ingest  → IngestPipeline.run()
  GET  /engine/health
  GET  /engine/strategies
  GET  /engine/models
  GET  /engine/providers
  GET  /engine/prompt-templates
"""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engine.config import CORS_ORIGINS
from engine.api.routes import books, chunks, health, ingest, pipeline_preview, query, query_stream, questions, reindex, sync

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Textbook RAG Engine",
        description="Internal Python Engine API — called by Payload CMS only",
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

    # --- Global exception handler -------------------------------------------
    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url, tb)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb},
        )

    app.include_router(health.router, prefix="/engine")
    app.include_router(query.router, prefix="/engine")
    app.include_router(query_stream.router, prefix="/engine")
    app.include_router(ingest.router, prefix="/engine")
    app.include_router(books.router, prefix="/engine")
    app.include_router(chunks.router, prefix="/engine")
    app.include_router(pipeline_preview.router, prefix="/engine")
    app.include_router(reindex.router, prefix="/engine")
    app.include_router(sync.router, prefix="/engine")
    app.include_router(questions.router, prefix="/engine")

    return app


app = create_app()
