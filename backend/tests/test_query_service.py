"""Tests for query_service — orchestration of retrieval + generation."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

from backend.app.schemas.query import QueryResponse
from backend.app.services import query_service


def _fake_chunks() -> list[dict]:
    return [
        {
            "id": 1,
            "chunk_id": "ch-1",
            "book_id": 10,
            "chapter_id": 20,
            "text": "Backpropagation is a method for computing gradients.",
            "book_title": "Deep Learning",
            "chapter_title": "Training",
            "source_locators": [
                {"chunk_id": 1, "page_number": 42, "x0": 0, "y0": 0, "x1": 100, "y1": 100},
            ],
        },
    ]


def test_query_happy_path(db: sqlite3.Connection) -> None:
    """query() should return a QueryResponse with answer, sources, stats."""
    with (
        patch(
            "backend.app.services.query_service.retrieval_service.retrieve",
            return_value=(_fake_chunks(), {"fts_hits": 5, "vector_hits": 0, "fused_count": 1}),
        ),
        patch(
            "backend.app.services.query_service.generation_service.generate",
            return_value="Backpropagation computes gradients.",
        ),
    ):
        resp = query_service.query(db, "What is backpropagation?", top_k=3)

    assert isinstance(resp, QueryResponse)
    assert resp.answer == "Backpropagation computes gradients."
    assert len(resp.sources) == 1
    assert resp.sources[0].book_title == "Deep Learning"
    assert resp.retrieval_stats.fts_hits == 5


def test_query_sources_have_bbox(db: sqlite3.Connection) -> None:
    """Sources with locators should include bbox data."""
    with (
        patch(
            "backend.app.services.query_service.retrieval_service.retrieve",
            return_value=(_fake_chunks(), {"fts_hits": 1, "vector_hits": 0, "fused_count": 1}),
        ),
        patch(
            "backend.app.services.query_service.generation_service.generate",
            return_value="Answer",
        ),
    ):
        resp = query_service.query(db, "test", top_k=1)
    src = resp.sources[0]
    assert src.bbox is not None
    assert src.page_number == 43


def test_query_no_results(db: sqlite3.Connection) -> None:
    """When retrieval returns no chunks, sources should be empty."""
    with (
        patch(
            "backend.app.services.query_service.retrieval_service.retrieve",
            return_value=([], {"fts_hits": 0, "vector_hits": 0, "fused_count": 0}),
        ),
        patch(
            "backend.app.services.query_service.generation_service.generate",
            return_value="I don't have enough context.",
        ),
    ):
        resp = query_service.query(db, "nonexistent topic xyz", top_k=3)
    assert resp.sources == []
    assert resp.answer == "I don't have enough context."
