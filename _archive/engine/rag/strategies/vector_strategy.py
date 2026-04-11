"""VectorStrategy — ChromaDB cosine-similarity vector search.

STORY-003: extracted from retrieval_service.py + vector_repo.search().
Resolves ChromaDB document IDs back to SQLite chunk rows so the result
is a list[ChunkHit] consistent with all other strategies.
"""

from __future__ import annotations

import sqlite3

from engine.rag.config import QueryConfig, RAGConfig
from engine.rag.strategies.base import RetrievalStrategy
from engine.rag.types import ChunkHit, StrategyResult


class VectorStrategy(RetrievalStrategy):
    """ChromaDB semantic similarity strategy.

    Requires:
    - ChromaDB persistent client at ``config.chroma_persist_dir``
    - Collection named ``textbook_chunks`` (created by rebuild_db)

    Filters: book_ids (mapped to ChromaDB metadata ``where`` clause).
    categories / content_types are NOT supported by ChromaDB metadata in this
    schema, so they are applied post-hoc on the SQLite-resolved rows.
    """

    name: str = "vector"
    display_name: str = "Vector (ChromaDB)"
    default_enabled: bool = True

    def __init__(self, config: RAGConfig) -> None:
        self._config = config
        self._client = None
        self._collection = None

    def is_available(self) -> bool:
        """Return False if ChromaDB persist directory doesn't exist or collection is empty/broken."""
        import os
        persist_dir = self._config.chroma_persist_dir
        if not persist_dir:
            try:
                from engine.config import CHROMA_PERSIST_DIR
                persist_dir = str(CHROMA_PERSIST_DIR)
            except Exception:  # noqa: BLE001
                return False
        # Must be an existing directory with actual content (not auto-created empty dir)
        if not os.path.isdir(persist_dir):
            return False
        # Check that it has some files (non-empty ChromaDB store)
        try:
            entries = os.listdir(persist_dir)
        except OSError:
            return False
        if not entries:
            return False
        try:
            self._get_collection()
            return True
        except Exception:  # noqa: BLE001
            return False

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        persist_dir = self._config.chroma_persist_dir
        if not persist_dir:
            # Fall back to global config path used by legacy vector_repo
            from engine.config import CHROMA_PERSIST_DIR
            persist_dir = str(CHROMA_PERSIST_DIR)

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="textbook_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def search(
        self,
        query: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> StrategyResult:
        """Query ChromaDB, resolve to ChunkHit rows via SQLite."""
        fetch_k = config.effective_fetch_k
        f = config.filters

        try:
            collection = self._get_collection()
            if collection.count() == 0:
                return StrategyResult(strategy=self.name, hits=[], query_used=query)

            # ChromaDB where clause (book_ids only — supported natively)
            where: dict | None = None
            if f.book_ids:
                ids = f.book_ids
                where = {"book_id": ids[0]} if len(ids) == 1 else {"book_id": {"$in": ids}}

            results = collection.query(
                query_texts=[query],
                n_results=min(fetch_k, collection.count()),
                where=where,
                include=["distances", "documents"],
            )
        except Exception as exc:  # noqa: BLE001
            return StrategyResult(
                strategy=self.name, hits=[], query_used=query, error=str(exc)
            )

        if not results or not results["ids"]:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        chroma_ids = results["ids"][0]
        distances = results["distances"][0] if results["distances"] else []

        # Resolve chroma_ids → SQLite rows
        if not chroma_ids:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        ph = ",".join("?" * len(chroma_ids))
        sql = (
            "SELECT id, chunk_id, book_id, chapter_id, primary_page_id,"
            "       content_type, text, reading_order, chroma_document_id "
            f"FROM chunks WHERE chroma_document_id IN ({ph})"
        )
        rows = db.execute(sql, chroma_ids).fetchall()
        row_map = {r["chroma_document_id"]: dict(r) for r in rows}

        # Post-hoc filters: content_types, categories
        hits: list[ChunkHit] = []
        for rank, (cid, dist) in enumerate(zip(chroma_ids, distances), start=1):
            r = row_map.get(cid)
            if r is None:
                continue
            if f.content_types and r.get("content_type") not in f.content_types:
                continue
            # categories not available here (need books JOIN); skip post-hoc for now
            hits.append(
                ChunkHit(
                    id=r["id"],
                    chunk_id=r["chunk_id"],
                    book_id=r["book_id"],
                    text=r["text"],
                    content_type=r.get("content_type", "text"),
                    reading_order=r.get("reading_order", 0),
                    chroma_document_id=cid,
                    vec_rank=rank,
                    vec_distance=float(dist),
                )
            )

        return StrategyResult(strategy=self.name, hits=hits, query_used=query)
