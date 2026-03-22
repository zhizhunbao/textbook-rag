"""Engine dependency injection."""

from __future__ import annotations

from functools import lru_cache

from engine.config import DATABASE_PATH, CHROMA_PERSIST_DIR, OLLAMA_BASE_URL, OLLAMA_MODEL
from engine.rag.config import RAGConfig
from engine.rag.core import RAGCore


@lru_cache(maxsize=1)
def get_rag_core() -> RAGCore:
    """Return singleton RAGCore instance."""
    config = RAGConfig(
        db_path=str(DATABASE_PATH),
        chroma_persist_dir=str(CHROMA_PERSIST_DIR),
        ollama_base_url=OLLAMA_BASE_URL,
        default_model=OLLAMA_MODEL,
    )
    return RAGCore(db_path=str(DATABASE_PATH), config=config)
