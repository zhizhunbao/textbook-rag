"""RAGCore — unified RAG pipeline shared by FastAPI and ROS2."""

from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Generator
from typing import Any

from engine.rag.config import QueryConfig, RAGConfig
from engine.rag.types import RAGResponse

logger = logging.getLogger(__name__)


class RAGCore:
    """Unified RAG pipeline entry point.

    Both FastAPI routers and the ROS2 node import and instantiate this class.
    Internal components are wired here; callers only call query().

    Components are resolved lazily on first use to keep startup fast.

    Example (FastAPI):
        core = RAGCore(db_path=str(DATABASE_PATH), config=rag_cfg)
        response = core.query("What is BM25?")

    Example (ROS2):
        core = RAGCore(db_path="/path/to/db", config=RAGConfig(default_model="qwen2.5:0.5b"))
        response = core.query(question, QueryConfig(top_k=3))
    """

    def __init__(self, db_path: str, config: RAGConfig | None = None) -> None:
        self._db_path = db_path
        self._config = config or RAGConfig(db_path=db_path)
        self._config.db_path = db_path

        # Components wired lazily (avoid circular import at module load time)
        self._retriever = None
        self._generator = None
        self._citation = None
        self._trace = None
        self._quality = None

    # ------------------------------------------------------------------
    # Lazy component accessors
    # ------------------------------------------------------------------

    def _get_db(self) -> sqlite3.Connection:
        """Open a fresh connection (thread-safe; caller closes it)."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _get_retriever(self):
        if self._retriever is None:
            from engine.rag.retrieval import RetrievalOrchestrator
            self._retriever = RetrievalOrchestrator(self._config)
        return self._retriever

    def _get_generator(self):
        if self._generator is None:
            from engine.rag.generation import GenerationEngine
            self._generator = GenerationEngine(self._config)
        return self._generator

    def _get_citation(self):
        if self._citation is None:
            from engine.rag.citation import CitationEngine
            self._citation = CitationEngine()
        return self._citation

    def _get_trace(self):
        from engine.rag.trace import TraceCollector
        # TraceCollector is per-query; return a fresh instance each time
        return TraceCollector()

    def _get_quality(self):
        if self._quality is None:
            from engine.rag.quality import QualityChecker
            self._quality = QualityChecker()
        return self._quality

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def query(self, question: str, config: QueryConfig | None = None) -> RAGResponse:
        """Execute the full RAG pipeline.

        Pipeline:
            1. Retrieve — run enabled strategies, fuse with RRF
            2. Generate — build prompt, call Ollama
            3. Citation  — validate, sanitize, map to sources
            4. Quality   — check for warnings
            5. Trace     — collect full audit trail

        Args:
            question: User question string.
            config:   Per-query config. None → sensible defaults (v1.0 behaviour).

        Returns:
            RAGResponse with answer, sources, trace, warnings, stats.
        """
        cfg = config or QueryConfig()
        trace = self._get_trace()
        db = self._get_db()

        t_start = time.perf_counter()
        logger.info("═══ RAG query start: %s", question[:80])

        try:
            # 0. Resolve string book IDs → integer IDs
            cfg.filters.resolve_book_ids(db)

            # 1. Retrieve
            t0 = time.perf_counter()
            retrieval_result = self._get_retriever().retrieve(question, cfg, db)
            t_retrieve = time.perf_counter() - t0
            logger.info(
                "  [1/4] Retrieve: %.2fs | %d strategies, %d chunks",
                t_retrieve,
                retrieval_result.stats.get("total_strategies", 0),
                len(retrieval_result.chunks),
            )
            for name, sr in retrieval_result.per_strategy.items():
                logger.info("         ├─ %s: %d hits", name, len(sr.hits))
            trace.record_retrieval(question, cfg, retrieval_result)

            # 2. Generate
            t0 = time.perf_counter()
            model = cfg.model or self._config.default_model
            raw_answer = self._get_generator().generate(
                question, retrieval_result.chunks, cfg
            )
            t_generate = time.perf_counter() - t0
            logger.info(
                "  [2/4] Generate: %.2fs | model=%s, answer_len=%d",
                t_generate, model, len(raw_answer),
            )
            trace.record_generation(cfg, raw_answer)

            # 3. Citation
            t0 = time.perf_counter()
            citation_result = self._get_citation().process(raw_answer, retrieval_result.chunks)
            t_cite = time.perf_counter() - t0
            logger.info(
                "  [3/4] Citation: %.2fs | valid=%d, invalid=%d",
                t_cite,
                len(citation_result.valid_citations),
                len(citation_result.invalid_citations),
            )
            trace.record_citations(citation_result)

            # 4. Quality
            t0 = time.perf_counter()
            warnings = self._get_quality().check(retrieval_result, citation_result)
            t_quality = time.perf_counter() - t0
            logger.info(
                "  [4/4] Quality: %.2fs | %d warnings",
                t_quality, len(warnings),
            )

        finally:
            db.close()

        t_total = time.perf_counter() - t_start
        logger.info(
            "═══ RAG query done: %.2fs (retrieve=%.2f, generate=%.2f, cite=%.2f, quality=%.2f)",
            t_total, t_retrieve, t_generate, t_cite, t_quality,
        )

        return RAGResponse(
            answer=citation_result.cleaned_answer,
            sources=citation_result.sources,
            trace=trace.get_trace(),
            warnings=warnings,
            stats=retrieval_result.stats,
        )

    def query_stream(
        self, question: str, config: QueryConfig | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Execute RAG pipeline with streaming generation.

        Yields SSE-style event dicts:
          {"event": "retrieval_done", "data": {stats}}
          {"event": "token",         "data": {"t": "..."}}
          {"event": "done",          "data": {answer, sources, trace, warnings}}

        Retrieval runs synchronously (fast), then generation streams tokens.
        Citation processing happens after all tokens are collected.
        """
        cfg = config or QueryConfig()
        trace = self._get_trace()
        db = self._get_db()

        logger.info("═══ RAG stream query start: %s", question[:80])

        try:
            # 0. Resolve string book IDs → integer IDs
            cfg.filters.resolve_book_ids(db)

            # 1. Retrieve (non-streaming, fast)
            t0 = time.perf_counter()
            retrieval_result = self._get_retriever().retrieve(question, cfg, db)
            t_retrieve = time.perf_counter() - t0
            logger.info(
                "  [1/3] Retrieve: %.2fs | %d chunks",
                t_retrieve, len(retrieval_result.chunks),
            )
            trace.record_retrieval(question, cfg, retrieval_result)

            yield {
                "event": "retrieval_done",
                "data": {
                    "stats": retrieval_result.stats,
                    "chunk_count": len(retrieval_result.chunks),
                },
            }

            # 2. Stream generate tokens
            t0 = time.perf_counter()
            model = cfg.model or self._config.default_model
            token_parts: list[str] = []
            for token in self._get_generator().generate_stream(
                question, retrieval_result.chunks, cfg
            ):
                token_parts.append(token)
                yield {"event": "token", "data": {"t": token}}
            raw_answer = "".join(token_parts)
            t_generate = time.perf_counter() - t0
            logger.info(
                "  [2/3] Generate (stream): %.2fs | model=%s, answer_len=%d",
                t_generate, model, len(raw_answer),
            )
            trace.record_generation(cfg, raw_answer)

            # 3. Citation & Quality (post-generation)
            citation_result = self._get_citation().process(
                raw_answer, retrieval_result.chunks
            )
            warnings = self._get_quality().check(
                retrieval_result, citation_result
            )
            trace.record_citations(citation_result)

        finally:
            db.close()

        logger.info("═══ RAG stream query done")

        yield {
            "event": "done",
            "data": {
                "answer": citation_result.cleaned_answer,
                "sources": citation_result.sources,
                "trace": trace.get_trace(),
                "warnings": [
                    {"level": w.level, "code": w.code, "message": w.message}
                    for w in warnings
                ],
                "stats": retrieval_result.stats,
            },
        }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def list_strategies(self) -> list[dict]:
        """Return metadata for all registered strategies."""
        return self._get_retriever().registry.list_all()

