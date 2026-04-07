"""HybridRetriever — BM25 + Vector → RRF fusion with metadata filtering.

Aligns with llama_index.core.retrievers.QueryFusionRetriever.
Combines:
    - VectorIndexRetriever (from ChromaVectorStore, with MetadataFilters)
    - BM25Retriever (from llama-index-retrievers-bm25)
    - QueryFusionRetriever with RECIPROCAL_RANK fusion

Filtering:
    - Vector retriever uses ChromaDB native where clause via MetadataFilters
    - BM25 results are post-filtered by a FilterPostprocessor since BM25
      doesn't support metadata filtering natively
"""

from __future__ import annotations

import logging
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    TOP_K,
)

logger = logging.getLogger(__name__)


def _build_metadata_filters(
    book_id_strings: list[str] | None = None,
) -> MetadataFilters | None:
    """Build LlamaIndex MetadataFilters from filter parameters.

    These filters are pushed down to the ChromaDB vector store so only
    matching chunks are retrieved, preventing cross-book contamination.

    Args:
        book_id_strings: List of book directory names to restrict search to.

    Returns:
        MetadataFilters or None (if no filters specified).
    """
    if not book_id_strings:
        return None

    if len(book_id_strings) == 1:
        # Single book — simple equality filter
        return MetadataFilters(
            filters=[
                MetadataFilter(
                    key="book_id",
                    value=book_id_strings[0],
                    operator=FilterOperator.EQ,
                ),
            ],
        )

    # Multiple books — OR condition
    return MetadataFilters(
        filters=[
            MetadataFilter(
                key="book_id",
                value=bid,
                operator=FilterOperator.EQ,
            )
            for bid in book_id_strings
        ],
        condition=FilterCondition.OR,
    )


def get_hybrid_retriever(
    similarity_top_k: int = TOP_K,
    collection_name: str = CHROMA_COLLECTION,
    book_id_strings: list[str] | None = None,
) -> QueryFusionRetriever:
    """Build a hybrid BM25 + Vector retriever with RRF fusion.

    Architecture:
        QueryFusionRetriever (RRF, k=60)
        ├── VectorIndexRetriever (ChromaDB cosine similarity + MetadataFilters)
        └── BM25Retriever (rank_bm25 on docstore nodes)

    Both retrievers share the same VectorStoreIndex so they operate
    on the same set of nodes.

    Falls back to vector-only retrieval when the collection is empty
    (no documents ingested yet) to avoid BM25 crash on empty corpus.

    Args:
        similarity_top_k: Number of results to return.
        collection_name: ChromaDB collection name.
        book_id_strings: Optional list of book directory names to filter on.
            When provided, only chunks from these books are retrieved.

    Returns:
        QueryFusionRetriever ready for use in a QueryEngine.
    """
    # Connect to existing ChromaDB collection
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    vector_store = ChromaVectorStore(chroma_collection=collection)

    # Build VectorStoreIndex from existing store
    index = VectorStoreIndex.from_vector_store(vector_store)

    # Build MetadataFilters for book scoping
    metadata_filters = _build_metadata_filters(book_id_strings)

    # Vector retriever — applies metadata filters at the ChromaDB level
    vector_retriever = index.as_retriever(
        similarity_top_k=similarity_top_k,
        filters=metadata_filters,
    )

    filter_desc = f", book_filter={book_id_strings}" if book_id_strings else ""
    logger.info(
        "Vector retriever ready (top_k=%d%s)", similarity_top_k, filter_desc
    )

    # Check if the collection has documents before building BM25
    # BM25Retriever crashes with ValueError on empty corpus (bm25s bug)
    doc_count = collection.count()
    retrievers_list = [vector_retriever]
    weights = [1.0]

    if doc_count > 0:
        try:
            bm25_retriever = BM25Retriever.from_defaults(
                index=index,
                similarity_top_k=similarity_top_k,
            )
            retrievers_list.append(bm25_retriever)
            weights = [0.5, 0.5]
            logger.info("BM25 retriever initialised (%d docs)", doc_count)
        except (ValueError, Exception) as exc:
            logger.warning("BM25 retriever unavailable, vector-only mode: %s", exc)
    else:
        logger.warning(
            "Collection '%s' is empty — using vector-only retrieval. "
            "Run ingestion to enable hybrid BM25+Vector mode.",
            collection_name,
        )

    # Fuse with Reciprocal Rank Fusion (k=60, industry standard)
    hybrid_retriever = QueryFusionRetriever(
        retrievers=retrievers_list,
        retriever_weights=weights,
        similarity_top_k=similarity_top_k,
        num_queries=1,  # no query augmentation, just fuse the two retrievers
        mode=FUSION_MODES.RECIPROCAL_RANK,
        use_async=False,
    )

    mode = "hybrid BM25+Vector" if len(retrievers_list) > 1 else "vector-only"
    logger.info(
        "HybridRetriever ready: %s → RRF (top_k=%d%s)", mode, similarity_top_k, filter_desc
    )
    return hybrid_retriever
