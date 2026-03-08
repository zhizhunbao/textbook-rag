"""Tests for retrieval_service — hybrid search, RRF fusion, metadata enrichment."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

from backend.app.services import retrieval_service


def test_retrieve_returns_results(db: sqlite3.Connection) -> None:
    """Smoke test: retrieve with a known term should return ranked chunks."""
    with patch(
        "backend.app.services.retrieval_service.vector_repo.search",
        return_value=[],
    ):
        chunks, stats = retrieval_service.retrieve(db, "backpropagation", top_k=3)
    assert len(chunks) > 0
    assert len(chunks) <= 3
    assert stats["fts_hits"] > 0
    assert stats["fused_count"] == len(chunks)
    # Each chunk should have enriched book_title
    assert chunks[0].get("book_title")


def test_retrieve_empty_query(db: sqlite3.Connection) -> None:
    """Empty query should return no results."""
    with patch(
        "backend.app.services.retrieval_service.vector_repo.search",
        return_value=[],
    ):
        chunks, stats = retrieval_service.retrieve(db, "", top_k=5)
    assert chunks == []
    assert stats["fts_hits"] == 0


def test_retrieve_with_book_filter(db: sqlite3.Connection) -> None:
    """Filters should be forwarded to FTS search."""
    # Get a valid book_id first
    row = db.execute("SELECT id FROM books LIMIT 1").fetchone()
    book_id = row["id"]
    with patch(
        "backend.app.services.retrieval_service.vector_repo.search",
        return_value=[],
    ):
        chunks, stats = retrieval_service.retrieve(
            db, "algorithm", filters={"book_ids": [book_id]}, top_k=5
        )
    # All returned chunks should belong to the filtered book
    for c in chunks:
        assert c["book_id"] == book_id


def test_retrieve_source_locators_attached(db: sqlite3.Connection) -> None:
    """Each returned chunk should have a source_locators key."""
    with patch(
        "backend.app.services.retrieval_service.vector_repo.search",
        return_value=[],
    ):
        chunks, _ = retrieval_service.retrieve(db, "algorithm", top_k=3)
    for c in chunks:
        assert "source_locators" in c
        assert isinstance(c["source_locators"], list)


def test_rrf_fuse_deduplicates() -> None:
    """RRF fusion should deduplicate by chunk id and sum scores."""
    a = [{"id": 1, "text": "a"}, {"id": 2, "text": "b"}]
    b = [{"id": 2, "text": "b"}, {"id": 3, "text": "c"}]
    fused = retrieval_service._rrf_fuse(a, b, k=60)
    ids = [d["id"] for d in fused]
    # id=2 appears in both lists so should rank highest
    assert ids[0] == 2
    assert set(ids) == {1, 2, 3}


def test_rrf_fuse_empty_lists() -> None:
    """RRF with empty lists should return empty."""
    assert retrieval_service._rrf_fuse([], [], k=60) == []
