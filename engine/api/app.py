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
from engine.api.routes import books, health, ingest, query

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
    # When an unhandled exception causes a 500, FastAPI's default error
    # response may NOT include CORS headers, so the browser reports a
    # misleading "CORS blocked" error.  This handler ensures the real error
    # message is always visible in the browser console.
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
    app.include_router(ingest.router, prefix="/engine")
    app.include_router(books.router, prefix="/engine")

    return app


app = create_app()
