"""Strategy registry — registers and resolves retrieval strategies by name."""

from __future__ import annotations

from engine.rag.strategies.base import RetrievalStrategy


class StrategyRegistry:
    """Holds all registered strategies and resolves subsets by name.

    Usage:
        registry = StrategyRegistry()
        registry.register(FTS5BM25Strategy(db))
        registry.register(VectorStrategy())
        enabled = registry.get_enabled(["fts5_bm25", "vector"])
    """

    def __init__(self) -> None:
        self._strategies: dict[str, RetrievalStrategy] = {}

    def register(self, strategy: RetrievalStrategy) -> None:
        """Register a strategy instance. Later registrations overwrite earlier ones."""
        self._strategies[strategy.name] = strategy

    def get_enabled(self, names: list[str]) -> list[RetrievalStrategy]:
        """Return strategy instances for the requested names, skipping unavailable ones."""
        result = []
        for name in names:
            strategy = self._strategies.get(name)
            if strategy is None:
                continue
            if not strategy.is_available():
                continue
            result.append(strategy)
        return result

    def list_all(self) -> list[dict]:
        """Return metadata for all registered strategies (for API /strategies endpoint)."""
        return [
            {
                "name": s.name,
                "display_name": s.display_name,
                "default_enabled": s.default_enabled,
                "available": s.is_available(),
            }
            for s in self._strategies.values()
        ]
