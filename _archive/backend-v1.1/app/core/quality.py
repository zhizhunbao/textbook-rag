"""QualityChecker — generates warnings based on retrieval and citation results."""

from __future__ import annotations

from backend.app.core.types import CitationResult, QualityWarning, RetrievalResult


# Warning codes
W_NO_FTS_HITS = "NO_FTS_HITS"
W_NO_VEC_HITS = "NO_VECTOR_HITS"
W_NO_TOC_HITS = "NO_TOC_HITS"
W_NO_PAGEINDEX_HITS = "NO_PAGEINDEX_HITS"
W_NO_CONTEXT = "NO_CONTEXT"
W_NO_VALID_CITATIONS = "NO_VALID_CITATIONS"
W_CITATIONS_REMOVED = "CITATIONS_REMOVED"


class QualityChecker:
    """Checks retrieval and citation quality; emits structured warnings."""

    def check(
        self,
        retrieval: RetrievalResult,
        citations: CitationResult,
    ) -> list[QualityWarning]:
        warnings: list[QualityWarning] = []

        # Per-strategy hit checks
        for name, result in retrieval.per_strategy.items():
            if not result.hits:
                code = {
                    "fts5_bm25": W_NO_FTS_HITS,
                    "vector": W_NO_VEC_HITS,
                    "toc_heading": W_NO_TOC_HITS,
                    "pageindex": W_NO_PAGEINDEX_HITS,
                }.get(name)
                if code:
                    warnings.append(QualityWarning(
                        level="warn",
                        code=code,
                        message=f"Strategy '{name}' returned 0 hits.",
                        suggestion=f"Try broadening the query or disabling the '{name}' strategy.",
                    ))

        # No context at all
        if not retrieval.chunks:
            warnings.append(QualityWarning(
                level="error",
                code=W_NO_CONTEXT,
                message="No chunks retrieved — answer is unsupported by any source.",
                suggestion="Try different keywords, or check that documents are ingested.",
            ))

        # No valid citations in answer
        if retrieval.chunks and not citations.valid_citations:
            warnings.append(QualityWarning(
                level="warn",
                code=W_NO_VALID_CITATIONS,
                message="Answer contains no valid citation markers.",
                suggestion="The model may have ignored context. Try a different prompt template.",
            ))

        # Citations were removed
        if citations.invalid_citations:
            warnings.append(QualityWarning(
                level="warn",
                code=W_CITATIONS_REMOVED,
                message=f"Removed {len(citations.invalid_citations)} invalid citation(s): "
                        f"{citations.invalid_citations}.",
                suggestion="Model hallucinated out-of-range citation indices.",
            ))

        return warnings
