"""SQLite connection helper — provides a FastAPI dependency that yields a
read-only connection with WAL mode and foreign keys enabled."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends

from backend.app.config import DATABASE_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


DB = Annotated[sqlite3.Connection, Depends(get_db)]
