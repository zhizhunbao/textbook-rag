"""vector_builder.py — build ChromaDB vector index from IngestResult.

v2.0: Extracted from scripts/build_vectors.py.
"""

from __future__ import annotations

import logging
from sentence_transformers import SentenceTransformer

from engine.adapters.chroma_adapter import get_collection
from engine.config import EMBEDDING_MODEL
from engine.ingest.chunk_builder import IngestResult

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def build_vectors(result: IngestResult, batch_size: int = 64) -> int:
    """Embed chunks and upsert into ChromaDB. Returns count of upserted docs."""
    collection = get_collection()
    model = _get_model()

    chunks = result.chunks
    if not chunks:
        return 0

    texts = [c.text for c in chunks]
    ids = [c.chunk_id for c in chunks]
    metadatas = [
        {
            "book_id": c.book_dir_name,
            "chunk_id": c.chunk_id,
            "page_idx": c.page_idx,
            "content_type": c.content_type,
            "category": result.category,
        }
        for c in chunks
    ]

    total = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]

        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        collection.upsert(
            ids=batch_ids,
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_meta,
        )
        total += len(batch_ids)
        logger.info("  vectors: %d/%d", total, len(texts))

    logger.info("vector_builder: upserted %d vectors for %s", total, result.book_dir_name)
    return total
