"""vectors — ChromaDB vector stats endpoint.

Provides per-book vector statistics: count, embedding dimensions,
and random chunk samples for the acquisition Vector Check tab.

Ref: AQ-09 — Vector Check Tab + Engine API
"""

from __future__ import annotations

import random
from typing import Any

import chromadb
from fastapi import APIRouter, HTTPException
from loguru import logger

from engine_v2.settings import CHROMA_COLLECTION, CHROMA_PERSIST_DIR

router = APIRouter(tags=["vectors"])


def _get_chroma_collection(
    collection_name: str = CHROMA_COLLECTION,
) -> chromadb.Collection:
    """Connect to the persistent ChromaDB collection."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


@router.get("/vectors/stats")
async def get_vector_stats(
    book_id: str | None = None,
    sample_count: int = 5,
    collection_name: str = CHROMA_COLLECTION,
) -> dict[str, Any]:
    """Get ChromaDB vector statistics, optionally filtered by book_id.

    Returns:
        - totalVectors: total vector count in collection
        - bookVectors: vector count for the specified book (if book_id given)
        - dimensions: embedding dimensionality (from first vector)
        - collectionName: ChromaDB collection name
        - samples: random chunk samples with text + metadata + vector preview

    Query params:
        book_id — engine book directory name (e.g. "bishop_prml")
        sample_count — number of random samples to return (default 5, max 20)
        collection_name — ChromaDB collection name (default from settings)
    """
    sample_count = min(sample_count, 20)

    try:
        collection = _get_chroma_collection(collection_name)
    except Exception as exc:
        raise HTTPException(500, f"Failed to connect to ChromaDB: {exc}")

    total_vectors = collection.count()

    # Book-scoped stats
    book_vectors = 0
    dimensions = 0
    samples: list[dict[str, Any]] = []

    if book_id:
        where_clause = {"book_id": book_id}

        # Count vectors for this book (fetch IDs only for minimal payload)
        try:
            all_ids = collection.get(
                where=where_clause,
                include=[],  # IDs only, minimal payload
            )
            book_vectors = len(all_ids["ids"])
        except Exception as exc:
            logger.warning("Failed to count book vectors for {}: {}", book_id, exc)

        # Random samples (includes embeddings for dimension + preview)
        if book_vectors > 0 and sample_count > 0:
            try:
                fetch_limit = min(book_vectors, max(sample_count * 4, 50))
                batch = collection.get(
                    where=where_clause,
                    include=["documents", "metadatas", "embeddings"],
                    limit=fetch_limit,
                )

                indices = list(range(len(batch["ids"])))
                if len(indices) > sample_count:
                    indices = random.sample(indices, sample_count)

                embeddings_list = batch.get("embeddings")
                metadatas_list = batch.get("metadatas")
                documents_list = batch.get("documents")

                for i in indices:
                    embedding = None
                    if embeddings_list is not None:
                        try:
                            embedding = embeddings_list[i]
                        except (IndexError, TypeError):
                            pass

                    meta = metadatas_list[i] if metadatas_list else {}
                    text = documents_list[i] if documents_list else ""

                    sample: dict[str, Any] = {
                        "chunkId": batch["ids"][i],
                        "text": text[:200] if text else "",
                        "metadata": {
                            "book_id": meta.get("book_id", "") if meta else "",
                            "content_type": meta.get("content_type", "") if meta else "",
                            "page_idx": meta.get("page_idx", 0) if meta else 0,
                        },
                    }
                    if embedding is not None:
                        vec = list(embedding[:8]) if hasattr(embedding, '__getitem__') else []
                        sample["vectorPreview"] = [float(v) for v in vec]
                        sample["dimensions"] = len(embedding)
                        # Derive dimensions from first sample
                        if dimensions == 0:
                            dimensions = len(embedding)

                    samples.append(sample)

            except Exception as exc:
                logger.warning("Failed to sample vectors for {}: {}", book_id, exc)
    else:
        # No book filter — collection-level stats only
        book_vectors = total_vectors

    # Fallback: get dimensions from a single vector if not derived from samples
    if dimensions == 0 and total_vectors > 0:
        try:
            peek = collection.get(limit=1, include=["embeddings"])
            embs = peek.get("embeddings")
            if embs is not None and len(embs) > 0:
                dimensions = len(embs[0])
        except Exception as exc:
            logger.warning("Failed to get embedding dimensions: {}", exc)

    return {
        "totalVectors": total_vectors,
        "bookVectors": book_vectors,
        "dimensions": dimensions,
        "collectionName": collection_name,
        "samples": samples,
    }

