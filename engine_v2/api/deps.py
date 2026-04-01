"""Dependency injection — singleton QueryEngine."""

from __future__ import annotations

from functools import lru_cache

from llama_index.core.query_engine import RetrieverQueryEngine

from engine_v2.query_engine.citation import get_query_engine


@lru_cache(maxsize=1)
def get_engine() -> RetrieverQueryEngine:
    """Return singleton RetrieverQueryEngine instance.

    Composes:
        retrievers/    → QueryFusionRetriever (BM25 + Vector → RRF)
        response_synthesizers/ → CitationSynthesizer
        query_engine/  → RetrieverQueryEngine (orchestrator)
    """
    return get_query_engine()
