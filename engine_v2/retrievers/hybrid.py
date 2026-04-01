"""HybridRetriever — BM25 + Vector → RRF fusion.

Aligns with llama_index.core.retrievers.QueryFusionRetriever.
Combines:
    - VectorIndexRetriever (from ChromaVectorStore)
    - BM25Retriever (from llama-index-retrievers-bm25)
    - QueryFusionRetriever with RECIPROCAL_RANK fusion
"""

from __future__ import annotations

import logging

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    TOP_K,
)

logger = logging.getLogger(__name__)


def get_hybrid_retriever(
    similarity_top_k: int = TOP_K,
    collection_name: str = CHROMA_COLLECTION,
) -> QueryFusionRetriever:
    """Build a hybrid BM25 + Vector retriever with RRF fusion.

    Architecture:
        QueryFusionRetriever (RRF, k=60)
        ├── VectorIndexRetriever (ChromaDB cosine similarity)
        └── BM25Retriever (rank_bm25 on docstore nodes)

    Both retrievers share the same VectorStoreIndex so they operate
    on the same set of nodes.

    Args:
        similarity_top_k: Number of results to return.
        collection_name: ChromaDB collection name.

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

    # Vector retriever
    vector_retriever = index.as_retriever(similarity_top_k=similarity_top_k)

    # BM25 retriever (operates on the same nodes)
    bm25_retriever = BM25Retriever.from_defaults(
        index=index,
        similarity_top_k=similarity_top_k,
    )

    # Fuse with Reciprocal Rank Fusion (k=60, industry standard)
    hybrid_retriever = QueryFusionRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        retriever_weights=[0.5, 0.5],
        similarity_top_k=similarity_top_k,
        num_queries=1,  # no query augmentation, just fuse the two retrievers
        mode=FUSION_MODES.RECIPROCAL_RANK,
        use_async=False,
    )

    logger.info(
        "HybridRetriever ready: vector + BM25 → RRF (top_k=%d)", similarity_top_k
    )
    return hybrid_retriever
