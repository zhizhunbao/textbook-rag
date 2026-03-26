"""Package init for strategies."""

from backend.app.core.strategies.base import RetrievalStrategy
from backend.app.core.strategies.fts5_strategy import FTS5BM25Strategy

from backend.app.core.strategies.pageindex_strategy import PageIndexStrategy
from backend.app.core.strategies.registry import StrategyRegistry
from backend.app.core.strategies.toc_strategy import TOCHeadingStrategy
from backend.app.core.strategies.vector_strategy import VectorStrategy

__all__ = [
    "RetrievalStrategy",
    "StrategyRegistry",
    "FTS5BM25Strategy",
    "VectorStrategy",
    "TOCHeadingStrategy",
    "PageIndexStrategy",

]
