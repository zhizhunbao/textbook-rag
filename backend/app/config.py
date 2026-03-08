"""Application configuration — reads environment variables with sensible defaults."""

from __future__ import annotations

import os
from pathlib import Path

# Project root: two levels up from backend/app/config.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATABASE_PATH: Path = Path(
    os.getenv("DATABASE_PATH", str(_PROJECT_ROOT / "data" / "textbook_rag.sqlite3"))
)
CHROMA_PERSIST_DIR: Path = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(_PROJECT_ROOT / "data" / "chroma_persist"))
)
TEXTBOOKS_DIR: Path = Path(
    os.getenv("TEXTBOOKS_DIR", str(_PROJECT_ROOT / "textbooks"))
)
DATA_DIR: Path = Path(
    os.getenv("DATA_DIR", str(_PROJECT_ROOT / "data"))
)

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000"
).split(",")

TOP_K_DEFAULT: int = int(os.getenv("TOP_K_DEFAULT", "5"))
