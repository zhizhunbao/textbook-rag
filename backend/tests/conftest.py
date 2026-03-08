"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.config import DATABASE_PATH
from backend.app.database import get_db
from backend.app.main import app


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a read-only connection to the real SQLite database."""
    if not DATABASE_PATH.exists():
        pytest.skip("SQLite database not found — run scripts/rebuild_db.py first")
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def client(db: sqlite3.Connection) -> Generator[TestClient, None, None]:
    """FastAPI TestClient that overrides the DB dependency with our fixture."""

    def _override_db() -> Generator[sqlite3.Connection, None, None]:
        yield db

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
