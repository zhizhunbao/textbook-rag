"""RetrievalOrchestrator — runs enabled strategies and fuses with RRF.

STORY-007 full implementation. This file is a stub for STORY-001.
"""

from __future__ import annotations

import sqlite3

from engine.rag.config import QueryConfig, RAGConfig
from engine.rag.strategies.registry import StrategyRegistry
from engine.rag.types import RetrievalResult, StrategyResult


class RetrievalOrchestrator:
    """Runs the enabled retrieval strategies and fuses results.

    Strategies are registered in __init__; each is independent and
    applies filters (category / content_type / book_ids) internally.
    """

    def __init__(self, config: RAGConfig) -> None:
        self._config = config
        self.registry = StrategyRegistry()
        self._register_strategies()

    def _register_strategies(self) -> None:
        """Wire up all available strategies. Import lazily to allow partial installs."""
        try:
            from engine.rag.strategies.fts5_strategy import FTS5BM25Strategy
            self.registry.register(FTS5BM25Strategy())
        except ImportError:
            pass

        try:
            from engine.rag.strategies.vector_strategy import VectorStrategy
            self.registry.register(VectorStrategy(self._config))
        except ImportError:
            pass

        try:
            from engine.rag.strategies.toc_strategy import TOCHeadingStrategy
            self.registry.register(TOCHeadingStrategy())
        except ImportError:
            pass

        try:
            from engine.rag.strategies.pageindex_strategy import PageIndexStrategy
            pi = PageIndexStrategy(self._config.mineru_output_dir)
            self.registry.register(pi)
        except ImportError:
            pass

        try:
            from engine.rag.strategies.sirchmunk_strategy import SirchmunkStrategy
            self.registry.register(SirchmunkStrategy(self._config))
        except ImportError:
            pass


    def retrieve(
        self,
        question: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> RetrievalResult:
        """Run enabled strategies and return fused results."""
        from engine.rag.fusion import RRFusion

        strategies = self.registry.get_enabled(config.effective_strategies)

        if not strategies:
            return RetrievalResult(
                chunks=[],
                per_strategy={},
                stats={"total_strategies": 0, "total_hits": 0},
            )

        per_strategy: dict[str, StrategyResult] = {}
        for strategy in strategies:
            result = strategy.search(question, config, db)
            per_strategy[strategy.name] = result

        # Fuse
        all_hit_lists = [r.hits for r in per_strategy.values()]
        if len(all_hit_lists) == 1:
            fused = all_hit_lists[0]
        else:
            fused = RRFusion.fuse(all_hit_lists, k=config.rrf_k)

        # Enrich metadata
        fused = self._enrich_metadata(fused, db)

        top_chunks = fused[: config.top_k]

        stats = {
            "total_strategies": len(strategies),
            "total_hits": len(fused),
        }
        for name, result in per_strategy.items():
            stats[f"{name}_hits"] = len(result.hits)

        return RetrievalResult(
            chunks=top_chunks,
            per_strategy=per_strategy,
            stats=stats,
        )

    def _enrich_metadata(self, hits, db: sqlite3.Connection):
        """Attach book title, chapter title, page number, bbox to each hit."""
        if not hits:
            return hits

        chunk_ids = [h.id for h in hits]
        placeholders = ",".join("?" * len(chunk_ids))

        # Book + chapter + page (category column added in v1.1; fall back gracefully)
        try:
            rows = db.execute(
                f"""
                SELECT
                    c.id           AS chunk_pk,
                    b.book_id      AS book_id_string,
                    b.title        AS book_title,
                    b.category     AS category,
                    ch.title       AS chapter_title,
                    p.page_number  AS page_number
                FROM chunks c
                LEFT JOIN books    b  ON b.id  = c.book_id
                LEFT JOIN chapters ch ON ch.id = c.chapter_id
                LEFT JOIN pages    p  ON p.id  = c.primary_page_id
                WHERE c.id IN ({placeholders})
                """,
                chunk_ids,
            ).fetchall()
        except Exception:  # noqa: BLE001  — category column missing in v1.0 DB
            rows = db.execute(
                f"""
                SELECT
                    c.id           AS chunk_pk,
                    b.book_id      AS book_id_string,
                    b.title        AS book_title,
                    '' AS category,
                    ch.title       AS chapter_title,
                    p.page_number  AS page_number
                FROM chunks c
                LEFT JOIN books    b  ON b.id  = c.book_id
                LEFT JOIN chapters ch ON ch.id = c.chapter_id
                LEFT JOIN pages    p  ON p.id  = c.primary_page_id
                WHERE c.id IN ({placeholders})
                """,
                chunk_ids,
            ).fetchall()

        meta_map = {row["chunk_pk"]: dict(row) for row in rows}


        # Source locators
        loc_rows = db.execute(
            f"""
            SELECT sl.chunk_id, sl.x0, sl.y0, sl.x1, sl.y1,
                   p.page_number, p.width, p.height
            FROM source_locators sl
            JOIN pages p ON p.id = sl.page_id
            WHERE sl.chunk_id IN ({placeholders})
            """,
            chunk_ids,
        ).fetchall()

        loc_map: dict[int, list[dict]] = {}
        for row in loc_rows:
            loc_map.setdefault(row["chunk_id"], []).append(dict(row))

        for hit in hits:
            meta = meta_map.get(hit.id, {})
            hit.book_id_string = meta.get("book_id_string") or hit.book_id_string
            hit.book_title = meta.get("book_title") or hit.book_title
            hit.category = meta.get("category") or hit.category
            hit.chapter_title = meta.get("chapter_title")
            hit.primary_page_number = meta.get("page_number")
            hit.source_locators = loc_map.get(hit.id, [])

        return hits
