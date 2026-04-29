"""retrievers — hybrid BM25 + Vector retrieval with RRF fusion."""

from engine_v2.retrievers.consulting import dual_collection_query
from engine_v2.retrievers.hybrid import get_hybrid_retriever

__all__ = ["dual_collection_query", "get_hybrid_retriever"]
