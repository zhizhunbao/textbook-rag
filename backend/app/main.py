"""FastAPI application entry-point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import CORS_ORIGINS
from backend.app.routers import books, query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup — nothing to initialise beyond lazy singletons
    yield
    # Shutdown


app = FastAPI(
    title="Textbook RAG API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(query.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
