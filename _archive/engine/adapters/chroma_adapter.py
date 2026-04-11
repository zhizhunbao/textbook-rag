"""ChromaDB adapter — wraps chromadb client for Engine use.

v2.0: extracted from vector_strategy / build_vectors.py into a shared adapter.
"""

from __future__ import annotations

import chromadb

from engine.config import CHROMA_PERSIST_DIR

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    """Return a singleton ChromaDB persistent client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection(name: str = "textbook_chunks") -> chromadb.Collection:
    """Return (or create) the named ChromaDB collection."""
    client = get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
