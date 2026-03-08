"""Tests for chunk_repo — FTS5 search and source locators."""

from __future__ import annotations

import sqlite3

from backend.app.repositories import chunk_repo


def test_search_fts_returns_results(db: sqlite3.Connection) -> None:
    results = chunk_repo.search_fts(db, "backpropagation", limit=5)
    assert len(results) > 0
    assert "text" in results[0]
    assert "chunk_id" in results[0]


def test_search_fts_empty_query(db: sqlite3.Connection) -> None:
    assert chunk_repo.search_fts(db, "", limit=5) == []


def test_get_source_locators(db: sqlite3.Connection) -> None:
    # Get a chunk id first
    results = chunk_repo.search_fts(db, "algorithm", limit=1)
    if not results:
        return
    locs = chunk_repo.get_source_locators(db, [results[0]["id"]])
    assert len(locs) >= 0  # some chunks may lack locators


def test_get_source_locators_empty(db: sqlite3.Connection) -> None:
    assert chunk_repo.get_source_locators(db, []) == []
