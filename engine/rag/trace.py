"""TraceCollector — records the full RAG pipeline audit trail per query."""

from __future__ import annotations

from engine.rag.config import QueryConfig
from engine.rag.types import CitationResult, RetrievalResult


class TraceCollector:
    """Collects trace data as the pipeline executes.

    One instance per query (not shared across requests).
    Call record_*() methods in pipeline order, then get_trace() at the end.
    """

    def __init__(self) -> None:
        self._retrieval: dict = {}
        self._generation: dict = {}
        self._citations: dict = {}

    def record_retrieval(
        self,
        question: str,
        config: QueryConfig,
        result: RetrievalResult,
    ) -> None:
        per_strategy = {}
        for name, sr in result.per_strategy.items():
            per_strategy[name] = {
                "query_used": sr.query_used,
                "hit_count": len(sr.hits),
                "error": sr.error,
                "hits": [
                    {
                        "rank": i + 1,
                        "chunk_id": h.chunk_id,
                        "score": h.fts_score or h.vec_distance or h.toc_score or h.pageindex_score,
                        "snippet": h.text[:200],
                    }
                    for i, h in enumerate(sr.hits[:10])
                ],
            }

        self._retrieval = {
            "question": question,
            "top_k": config.top_k,
            "fetch_k": config.effective_fetch_k,
            "enabled_strategies": config.effective_strategies,
            "rrf_k": config.rrf_k,
            "filters": config.filters.as_dict(),
            "per_strategy": per_strategy,
            "fused_count": len(result.chunks),
            "stats": result.stats,
        }

    def record_generation(self, config: QueryConfig, raw_answer: str) -> None:
        self._generation = {
            "model": config.model,
            "prompt_template": config.prompt_template,
            "custom_system_prompt": config.custom_system_prompt,
            "raw_answer_length": len(raw_answer),
        }

    def record_citations(self, result: CitationResult) -> None:
        self._citations = {
            "valid": result.valid_citations,
            "invalid": result.invalid_citations,
            "removed_count": len(result.invalid_citations),
        }

    def get_trace(self) -> dict:
        return {
            "retrieval": self._retrieval,
            "generation": self._generation,
            "citations": self._citations,
        }
