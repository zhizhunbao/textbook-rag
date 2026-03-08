"""Vector repository — ChromaDB similarity search wrapper."""

from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.app.config import CHROMA_PERSIST_DIR

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is not None:
        return _collection
    _client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    _collection = _client.get_or_create_collection(
        name="textbook_chunks",
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def search(
    query_text: str,
    top_k: int = 10,
    filters: dict | None = None,
) -> list[dict]:
    """Query ChromaDB for the *top_k* most similar chunks.

    Returns a list of dicts with keys ``chroma_id``, ``distance``, ``text``.
    *filters* may contain ``book_ids`` (mapped to ChromaDB ``where`` clause).
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    where: dict | None = None
    if filters and filters.get("book_ids"):
        ids = filters["book_ids"]
        if len(ids) == 1:
            where = {"book_id": ids[0]}
        else:
            where = {"book_id": {"$in": ids}}

    results = collection.query(
        query_texts=[query_text],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["distances", "documents"],
    )

    items: list[dict] = []
    if results and results["ids"]:
        for i, cid in enumerate(results["ids"][0]):
            items.append({
                "chroma_id": cid,
                "distance": results["distances"][0][i] if results["distances"] else 0,
                "text": (results["documents"][0][i] if results["documents"] else ""),
            })
    return items
