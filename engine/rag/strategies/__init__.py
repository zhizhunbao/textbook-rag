"""Retrieval strategies — 5 v1.1 strategies + Azure Search (v2.0)."""

from engine.rag.strategies.base import RetrievalStrategy
from engine.rag.strategies.fts5_strategy import FTS5BM25Strategy
from engine.rag.strategies.pageindex_strategy import PageIndexStrategy
from engine.rag.strategies.registry import StrategyRegistry
from engine.rag.strategies.toc_strategy import TOCHeadingStrategy
from engine.rag.strategies.vector_strategy import VectorStrategy
from engine.rag.strategies.sirchmunk_strategy import SirchmunkStrategy

__all__ = [
    "RetrievalStrategy",
    "StrategyRegistry",
    "FTS5BM25Strategy",
    "VectorStrategy",
    "TOCHeadingStrategy",
    "PageIndexStrategy",
    "SirchmunkStrategy",
]
