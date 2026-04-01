"""Shared data types — aligns with llama_index.core.schema.

Extends LlamaIndex's Document/TextNode with textbook-specific metadata.
Replaces engine v1's rag/types.py + ingest/chunk_builder.py dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BookMeta:
    """Metadata for a single book (lives in Payload CMS)."""

    book_id: str
    title: str
    authors: str = ""
    category: str = "textbook"
    total_pages: int = 0


@dataclass
class SourceLocator:
    """Bounding box for a chunk on a PDF page."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    page_width: float = 0.0
    page_height: float = 0.0


@dataclass
class RAGResponse:
    """Full response from QueryEngine.query()."""

    answer: str
    sources: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
