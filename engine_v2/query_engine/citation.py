"""citation — Orchestrate retriever + synthesizer into a full query engine.

Responsibilities:
    - Build RetrieverQueryEngine from hybrid retriever + citation synthesizer
    - Execute RAG queries and convert results to RAGResponse schema
    - Pass book_id filters through to the retriever for scoped queries

Ref: llama_index — RetrieverQueryEngine
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

from llama_index.core.query_engine import RetrieverQueryEngine

from engine_v2.response_synthesizers.citation import get_citation_synthesizer
from engine_v2.retrievers.hybrid import get_hybrid_retriever
from engine_v2.schema import RAGResponse, build_source
from engine_v2.settings import TOP_K


# ============================================================
# Node postprocessors
# ============================================================
class CitationLabelPostprocessor(BaseNodePostprocessor):
    """Prepend 'Source N:' to each chunk's text before synthesis.

    Mirrors LlamaIndex's CitationQueryEngine behavior so the LLM uses
    integer [N] citation markers instead of inventing section numbers.
    """

    def _postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> list[NodeWithScore]:
        for i, nws in enumerate(nodes, start=1):
            original = nws.node.get_content()
            nws.node.set_content(f"Source {i}:\n{original}")
        return nodes


class BookFilterPostprocessor(BaseNodePostprocessor):
    """Post-filter nodes by book_id for BM25 results.

    BM25Retriever doesn't support native metadata filtering, so this
    postprocessor drops any nodes from books not in the allowed set.
    Only active when book_id_strings is provided.
    """

    book_id_strings: list[str] = []

    def _postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> list[NodeWithScore]:
        if not self.book_id_strings:
            return nodes

        allowed = set(self.book_id_strings)
        filtered = [
            nws for nws in nodes
            if nws.node.metadata.get("book_id", "") in allowed
        ]
        dropped = len(nodes) - len(filtered)
        if dropped > 0:
            logger.debug(
                "BookFilterPostprocessor dropped {} nodes outside book scope",
                dropped,
            )
        return filtered


# ============================================================
# Engine factory
# ============================================================
def get_query_engine(
    similarity_top_k: int = TOP_K,
    streaming: bool = False,
    book_id_strings: list[str] | None = None,
) -> RetrieverQueryEngine:
    """Build a RetrieverQueryEngine from hybrid retriever + citation synthesizer.

    Architecture:
        RetrieverQueryEngine
        ├── retriever  → QueryFusionRetriever (BM25 + Vector → RRF)
        ├── synthesizer → CitationSynthesizer (COMPACT + citation prompts)
        └── postprocessors:
            ├── BookFilterPostprocessor (filter BM25 results by book scope)
            └── CitationLabelPostprocessor (Source N: labels)

    Args:
        similarity_top_k: Number of chunks to retrieve.
        streaming: Whether to enable streaming generation.
        book_id_strings: Optional list of book directory names to scope
            retrieval to. When provided, only chunks from these books
            are included in the context.

    Returns:
        RetrieverQueryEngine ready for .query() / .aquery()
    """
    retriever = get_hybrid_retriever(
        similarity_top_k=similarity_top_k,
        book_id_strings=book_id_strings,
    )
    synthesizer = get_citation_synthesizer(streaming=streaming)

    # Build postprocessor chain
    postprocessors: list[BaseNodePostprocessor] = []

    # Book filter — drops BM25 results from out-of-scope books
    if book_id_strings:
        postprocessors.append(
            BookFilterPostprocessor(book_id_strings=book_id_strings)
        )

    # Citation labels — always last so Source N: numbering is correct
    postprocessors.append(CitationLabelPostprocessor())

    engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
        node_postprocessors=postprocessors,
    )

    filter_desc = f", books={book_id_strings}" if book_id_strings else ""
    logger.info("TextbookQueryEngine ready (top_k={}, streaming={}{})",
                similarity_top_k, streaming, filter_desc)
    return engine


# ============================================================
# Query convenience wrapper
# ============================================================

def query(
    question: str,
    engine: RetrieverQueryEngine | None = None,
    book_id_strings: list[str] | None = None,
) -> RAGResponse:
    """Execute a RAG query and return a structured response.

    Convenience wrapper that converts LlamaIndex's Response
    into our project-specific RAGResponse schema.

    Args:
        question: User question string.
        engine: Optional pre-built engine. If None, builds a new one.
        book_id_strings: Optional book filter (only used when engine is None).

    Returns:
        RAGResponse with answer, sources, warnings, stats.
    """
    if engine is None:
        engine = get_query_engine(book_id_strings=book_id_strings)

    response = engine.query(question)

    # Map source nodes to our source format
    sources = [
        build_source(nws, i)
        for i, nws in enumerate(response.source_nodes, start=1)
    ]

    # Warnings
    warnings: list[str] = []
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
