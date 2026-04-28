"""sampler — Stratified chunk sampling for Question Dataset generation.

Responsibilities:
    - Sample chunks from ChromaDB by book → chapter → content_type
    - Support stratified, chapter_balanced, and random strategies
    - Return rich metadata for each sampled chunk

Ref: llama_index.core.llama_dataset.generator — RagDatasetGenerator node input
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import chromadb
from loguru import logger

from engine_v2.settings import CHROMA_COLLECTION, CHROMA_PERSIST_DIR


# ============================================================
# Data types
# ============================================================
@dataclass
class SampledChunk:
    """A single sampled chunk with full metadata."""

    id: str
    text: str
    book_id: str = ""
    book_title: str = ""
    chapter_key: str = ""
    page_idx: int = 0
    content_type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Stratified Chunk Sampler (QD-04)
# ============================================================
class StratifiedChunkSampler:
    """Sample chunks from ChromaDB with stratified coverage guarantees.

    Strategies:
        - stratified: by content_type (text:60%, table:20%, image:20%)
        - chapter_balanced: uniform across chapters
        - random: pure random baseline
    """

    # Target content_type ratios for stratified sampling
    _TYPE_RATIOS = {"text": 0.6, "table": 0.2, "image": 0.2}

    def __init__(
        self,
        collection_name: str = CHROMA_COLLECTION,
    ) -> None:
        self._collection_name = collection_name

    def sample(
        self,
        book_ids: list[str] | None = None,
        k_per_book: int = 10,
        strategy: str = "stratified",
    ) -> list[SampledChunk]:
        """Sample chunks from ChromaDB with the specified strategy.

        Args:
            book_ids: Filter to specific books; None = all books.
            k_per_book: Number of chunks to sample per book.
            strategy: 'stratified' | 'chapter_balanced' | 'random'.

        Returns:
            List of SampledChunk with full metadata.
        """
        all_chunks = self._load_all_chunks(book_ids)
        if not all_chunks:
            logger.warning("No chunks found for sampling")
            return []

        # Group by book_id
        by_book = self._group_by_key(all_chunks, "book_id")

        sampled: list[SampledChunk] = []
        for bid, chunks in by_book.items():
            k = min(k_per_book, len(chunks))
            if strategy == "stratified":
                picked = self._stratified_sample(chunks, k)
            elif strategy == "chapter_balanced":
                picked = self._chapter_balanced_sample(chunks, k)
            else:
                picked = self._random_sample(chunks, k)

            logger.info(
                "Sampled {}/{} chunks from book={} strategy={}",
                len(picked), len(chunks), bid, strategy,
            )
            sampled.extend(picked)

        return sampled

    # ── Strategy implementations ─────────────────────────────

    def _stratified_sample(
        self, chunks: list[SampledChunk], k: int,
    ) -> list[SampledChunk]:
        """Sample by content_type with target ratios."""
        by_type = self._group_by_key(chunks, "content_type")

        result: list[SampledChunk] = []
        remaining = k

        for ctype, ratio in self._TYPE_RATIOS.items():
            pool = by_type.get(ctype, [])
            n = min(int(k * ratio), len(pool), remaining)
            if n > 0 and pool:
                result.extend(random.sample(pool, n))
                remaining -= n

        # Fill remainder from any type
        if remaining > 0:
            used_ids = {c.id for c in result}
            leftover = [c for c in chunks if c.id not in used_ids]
            fill = min(remaining, len(leftover))
            if fill > 0:
                result.extend(random.sample(leftover, fill))

        return result

    def _chapter_balanced_sample(
        self, chunks: list[SampledChunk], k: int,
    ) -> list[SampledChunk]:
        """Sample uniformly across chapters."""
        by_chapter = self._group_by_key(chunks, "chapter_key")
        if not by_chapter:
            return self._random_sample(chunks, k)

        per_chapter = max(1, k // len(by_chapter))
        result: list[SampledChunk] = []

        for _ch, pool in by_chapter.items():
            n = min(per_chapter, len(pool))
            result.extend(random.sample(pool, n))

        # Fill to k if under
        if len(result) < k:
            used_ids = {c.id for c in result}
            leftover = [c for c in chunks if c.id not in used_ids]
            fill = min(k - len(result), len(leftover))
            if fill > 0:
                result.extend(random.sample(leftover, fill))

        return result[:k]

    @staticmethod
    def _random_sample(
        chunks: list[SampledChunk], k: int,
    ) -> list[SampledChunk]:
        """Pure random baseline."""
        return random.sample(chunks, min(k, len(chunks)))

    # ── ChromaDB loading ─────────────────────────────────────

    def _load_all_chunks(
        self, book_ids: list[str] | None,
    ) -> list[SampledChunk]:
        """Load chunks from ChromaDB with optional book filter."""
        client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name=self._collection_name,
        )

        where = self._build_where(book_ids)
        results = collection.get(
            where=where,
            include=["documents", "metadatas"],
        )

        if not results["documents"]:
            return []

        chunks: list[SampledChunk] = []
        for i, doc in enumerate(results["documents"]):
            if not doc:
                continue
            meta = results["metadatas"][i] if results["metadatas"] else {}
            chunks.append(SampledChunk(
                id=results["ids"][i],
                text=doc,
                book_id=meta.get("book_id", ""),
                book_title=meta.get("book_title", ""),
                chapter_key=meta.get("chapter_key", ""),
                page_idx=meta.get("page_idx", 0),
                content_type=meta.get("content_type", "text"),
                metadata=meta or {},
            ))

        return chunks

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _build_where(
        book_ids: list[str] | None,
    ) -> dict[str, Any] | None:
        """Build ChromaDB where filter for book IDs."""
        if not book_ids:
            return None
        if len(book_ids) == 1:
            return {"book_id": book_ids[0]}
        return {"$or": [{"book_id": bid} for bid in book_ids]}

    @staticmethod
    def _group_by_key(
        chunks: list[SampledChunk], key: str,
    ) -> dict[str, list[SampledChunk]]:
        """Group SampledChunk list by a given attribute."""
        groups: dict[str, list[SampledChunk]] = {}
        for c in chunks:
            val = getattr(c, key, "") or "unknown"
            groups.setdefault(val, []).append(c)
        return groups
