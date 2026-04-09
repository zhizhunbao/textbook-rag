"""Dependency injection — singleton QueryEngine."""

from __future__ import annotations

from functools import lru_cache

from engine_v2.query_engine.citation import (
    TextbookCitationQueryEngine,
    get_query_engine,
)


@lru_cache(maxsize=1)
def get_engine() -> TextbookCitationQueryEngine:
    """Return singleton TextbookCitationQueryEngine instance.

    Composes:
        retrievers/    → QueryFusionRetriever (BM25 + Vector → RRF)
        _create_citation_nodes → merge same-page + Source N labels
        response_synthesizers/ → CitationSynthesizer
    """
    return get_query_engine()
