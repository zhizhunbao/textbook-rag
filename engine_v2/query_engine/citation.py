"""TextbookQueryEngine — orchestrates retriever + synthesizer.

Aligns with llama_index.core.query_engine.
Composes:
    - retrievers/hybrid.py       → QueryFusionRetriever
    - response_synthesizers/     → CitationSynthesizer
Into a RetrieverQueryEngine that handles the full query flow.
"""

from __future__ import annotations

import logging

from llama_index.core.query_engine import RetrieverQueryEngine

from engine_v2.response_synthesizers.citation import get_citation_synthesizer
from engine_v2.retrievers.hybrid import get_hybrid_retriever
from engine_v2.schema import RAGResponse
from engine_v2.settings import TOP_K

logger = logging.getLogger(__name__)


def get_query_engine(
    similarity_top_k: int = TOP_K,
    streaming: bool = False,
) -> RetrieverQueryEngine:
    """Build a RetrieverQueryEngine from hybrid retriever + citation synthesizer.

    Architecture:
        RetrieverQueryEngine
        ├── retriever  → QueryFusionRetriever (BM25 + Vector → RRF)
        └── synthesizer → CitationSynthesizer (COMPACT + citation prompts)

    Args:
        similarity_top_k: Number of chunks to retrieve.
        streaming: Whether to enable streaming generation.

    Returns:
        RetrieverQueryEngine ready for .query() / .aquery()
    """
    retriever = get_hybrid_retriever(similarity_top_k=similarity_top_k)
    synthesizer = get_citation_synthesizer(streaming=streaming)

    engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
    )

    logger.info("TextbookQueryEngine ready (top_k=%d, streaming=%s)",
                similarity_top_k, streaming)
    return engine


def query(
    question: str,
    engine: RetrieverQueryEngine | None = None,
) -> RAGResponse:
    """Execute a RAG query and return a structured response.

    Convenience wrapper that converts LlamaIndex's Response
    into our project-specific RAGResponse schema.

    Args:
        question: User question string.
        engine: Optional pre-built engine. If None, builds a new one.

    Returns:
        RAGResponse with answer, sources, warnings, stats.
    """
    if engine is None:
        engine = get_query_engine()

    response = engine.query(question)

    # Map source nodes to our source format
    sources = []
    for i, node_with_score in enumerate(response.source_nodes, start=1):
        node = node_with_score.node
        meta = node.metadata
        bbox = meta.get("bbox", [0, 0, 0, 0])
        page_idx = meta.get("page_idx", 0)

        sources.append({
            "citation_index": i,
            "chunk_id": node.id_,
            "book_id": meta.get("book_id", ""),
            "page_number": page_idx + 1,
            "content_type": meta.get("content_type", "text"),
            "chapter_key": meta.get("chapter_key"),
            "category": meta.get("category", "textbook"),
            "snippet": node.get_content()[:300],
            "score": node_with_score.score,
            "bbox": {
                "x0": bbox[0], "y0": bbox[1],
                "x1": bbox[2], "y1": bbox[3],
                "page": page_idx,
            } if bbox and any(v != 0 for v in bbox) else None,
        })

    # Warnings
    warnings = []
    if not response.source_nodes:
        warnings.append("No chunks retrieved — answer is unsupported by any source.")

    return RAGResponse(
        answer=str(response),
        sources=sources,
        warnings=warnings,
        stats={
            "source_count": len(response.source_nodes),
        },
    )
