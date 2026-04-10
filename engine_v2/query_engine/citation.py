"""citation — Textbook-specific CitationQueryEngine.

Follows LlamaIndex's CitationQueryEngine pattern: a custom QueryEngine
subclass that transforms retrieved nodes BEFORE synthesis, guaranteeing
a 1:1 mapping between Source N labels and response.source_nodes[N-1].

Key difference from LlamaIndex default:
    - Instead of sub-chunking large nodes, we MERGE chunks from the same
      (book_id, page_idx) to eliminate redundant citations from hybrid
      retrieval (BM25 + Vector fusion often returns multiple chunks per page).

Architecture:
    TextbookCitationQueryEngine
    ├── retrieve()  → HybridRetriever → BookFilterPostprocessor
    ├── _create_citation_nodes()  → merge same-page + add Source N labels
    └── synthesize() → CitationSynthesizer (COMPACT + citation prompts)

Ref: llama_index.core.query_engine.citation_query_engine
"""

from __future__ import annotations

import re
from collections import OrderedDict  # kept for potential future use
from typing import List, Optional, Sequence

from loguru import logger

from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.response_synthesizers import BaseSynthesizer
from llama_index.core.schema import (
    MetadataMode,
    NodeWithScore,
    QueryBundle,
    TextNode,
)
from llama_index.core.settings import Settings

from engine_v2.response_synthesizers.citation import get_citation_synthesizer
from engine_v2.retrievers.hybrid import get_hybrid_retriever
from engine_v2.schema import RAGResponse, build_source, normalize_scores
from engine_v2.settings import TOP_K


# ============================================================
# Node postprocessors (pre-citation)
# ============================================================
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
# TextbookCitationQueryEngine
# ============================================================
class TextbookCitationQueryEngine(BaseQueryEngine):
    """Citation query engine with same-page chunk merging.

    Modeled after LlamaIndex's CitationQueryEngine but replaces
    sub-chunking with same-page merging to handle hybrid retrieval
    duplicates.

    The _create_citation_nodes() method:
        1. Groups retrieved nodes by (book_id, page_idx).
        2. Merges each group into a single node (text joined, best score kept).
        3. Prepends "Source N:" label to each merged node.

    This guarantees that response.source_nodes[i] corresponds exactly
    to Source {i+1} in the LLM's answer — no post-hoc rewriting needed.
    """

    def __init__(
        self,
        retriever: object,
        response_synthesizer: BaseSynthesizer,
        node_postprocessors: Optional[List[BaseNodePostprocessor]] = None,
    ) -> None:
        self._retriever = retriever
        self._response_synthesizer = response_synthesizer
        self._node_postprocessors = node_postprocessors or []

        callback_manager = Settings.callback_manager
        for pp in self._node_postprocessors:
            pp.callback_manager = callback_manager

        super().__init__(callback_manager=callback_manager)

    # ==========================================================
    # PromptMixin: expose synthesizer prompts for get/set
    # ==========================================================
    def _get_prompt_modules(self) -> dict:
        """Return prompt sub-modules (required by BaseQueryEngine / PromptMixin)."""
        return {"response_synthesizer": self._response_synthesizer}

    # ==========================================================
    # Core: deduplicate + add Source N labels (per-chunk)
    # ==========================================================
    def _create_citation_nodes(
        self, nodes: list[NodeWithScore]
    ) -> list[NodeWithScore]:
        """Deduplicate and label each chunk with Source N.

        Each retrieved chunk gets its own Source N citation label,
        providing granular references for the LLM to cite.
        Only exact-duplicate texts are removed.

        Returns:
            List of citation nodes, each with "Source N:\\n{text}" content.
            The list order determines the citation index (1-based).
        """
        citation_nodes: list[NodeWithScore] = []
        seen: set[str] = set()

        for nws in nodes:
            text = nws.node.get_content()
            # Strip any leftover "Source N:" prefix from previous runs
            text = re.sub(r"^Source \d+:\n", "", text)

            # Skip exact duplicates
            if not text or text in seen:
                continue
            seen.add(text)

            # Create a new node with Source N label
            new_node = NodeWithScore(
                node=TextNode.model_validate(nws.node.model_dump()),
                score=nws.score,
            )
            source_idx = len(citation_nodes) + 1
            new_node.node.set_content(f"Source {source_idx}:\n{text}")
            citation_nodes.append(new_node)

        if len(citation_nodes) < len(nodes):
            logger.info(
                "Citation nodes: {} raw → {} unique ({} duplicates removed)",
                len(nodes), len(citation_nodes), len(nodes) - len(citation_nodes),
            )

        return citation_nodes

    # ==========================================================
    # Retrieve — delegates to hybrid retriever + postprocessors
    # ==========================================================
    def retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """Retrieve and post-filter nodes (before citation labeling)."""
        nodes = self._retriever.retrieve(query_bundle)

        for postprocessor in self._node_postprocessors:
            nodes = postprocessor.postprocess_nodes(
                nodes, query_bundle=query_bundle
            )

        return nodes

    # ==========================================================
    # Synthesize — creates citation nodes, then calls synthesizer
    # ==========================================================
    def synthesize(
        self,
        query_bundle: QueryBundle,
        nodes: list[NodeWithScore],
        additional_source_nodes: Optional[Sequence[NodeWithScore]] = None,
    ) -> RESPONSE_TYPE:
        """Create citation nodes and synthesize response."""
        nodes = self._create_citation_nodes(nodes)
        return self._response_synthesizer.synthesize(
            query=query_bundle,
            nodes=nodes,
            additional_source_nodes=additional_source_nodes,
        )

    # ==========================================================
    # _query — the main query pipeline
    # ==========================================================
    def _query(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
        """Execute the full RAG pipeline: retrieve → merge → synthesize."""
        with self.callback_manager.event(
            CBEventType.QUERY,
            payload={EventPayload.QUERY_STR: query_bundle.query_str},
        ) as query_event:
            with self.callback_manager.event(
                CBEventType.RETRIEVE,
                payload={EventPayload.QUERY_STR: query_bundle.query_str},
            ) as retrieve_event:
                nodes = self.retrieve(query_bundle)
                nodes = self._create_citation_nodes(nodes)
                retrieve_event.on_end(payload={EventPayload.NODES: nodes})

            response = self._response_synthesizer.synthesize(
                query=query_bundle,
                nodes=nodes,
            )
            query_event.on_end(payload={EventPayload.RESPONSE: response})

        return response

    async def _aquery(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
        """Async version of _query."""
        with self.callback_manager.event(
            CBEventType.QUERY,
            payload={EventPayload.QUERY_STR: query_bundle.query_str},
        ) as query_event:
            with self.callback_manager.event(
                CBEventType.RETRIEVE,
                payload={EventPayload.QUERY_STR: query_bundle.query_str},
            ) as retrieve_event:
                nodes = self.retrieve(query_bundle)
                nodes = self._create_citation_nodes(nodes)
                retrieve_event.on_end(payload={EventPayload.NODES: nodes})

            response = await self._response_synthesizer.asynthesize(
                query=query_bundle,
                nodes=nodes,
            )
            query_event.on_end(payload={EventPayload.RESPONSE: response})

        return response


# ============================================================
# Engine factory
# ============================================================
def get_query_engine(
    similarity_top_k: int = TOP_K,
    streaming: bool = False,
    book_id_strings: list[str] | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> TextbookCitationQueryEngine:
    """Build a TextbookCitationQueryEngine.

    Architecture:
        TextbookCitationQueryEngine
        ├── retriever  → QueryFusionRetriever (BM25 + Vector → RRF)
        ├── _create_citation_nodes  → merge same-page + Source N labels
        ├── synthesizer → CitationSynthesizer (COMPACT + citation prompts)
        └── postprocessors:
            └── BookFilterPostprocessor (filter BM25 results by book scope)

    Args:
        similarity_top_k: Number of chunks to retrieve.
        streaming: Whether to enable streaming generation.
        book_id_strings: Optional list of book directory names to scope
            retrieval to. When provided, only chunks from these books
            are included in the context.
        model: Optional model name override for LLM selection.

    Returns:
        TextbookCitationQueryEngine ready for .query() / .aquery()
    """
    retriever = get_hybrid_retriever(
        similarity_top_k=similarity_top_k,
        book_id_strings=book_id_strings,
    )
    synthesizer = get_citation_synthesizer(streaming=streaming, model=model, provider=provider)

    # Book filter — drops BM25 results from out-of-scope books
    postprocessors: list[BaseNodePostprocessor] = []
    if book_id_strings:
        postprocessors.append(
            BookFilterPostprocessor(book_id_strings=book_id_strings)
        )

    engine = TextbookCitationQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
        node_postprocessors=postprocessors,
    )

    filter_desc = f", books={book_id_strings}" if book_id_strings else ""
    logger.info("TextbookCitationQueryEngine ready (top_k={}, streaming={}, model={}{})",
                similarity_top_k, streaming, model or 'default', filter_desc)
    return engine


# ============================================================
# Query convenience wrapper
# ============================================================
def query(
    question: str,
    engine: TextbookCitationQueryEngine | None = None,
    book_id_strings: list[str] | None = None,
    model: str | None = None,
) -> RAGResponse:
    """Execute a RAG query and return a structured response.

    Convenience wrapper that converts LlamaIndex's Response
    into our project-specific RAGResponse schema.

    Args:
        question: User question string.
        engine: Optional pre-built engine. If None, builds a new one.
        book_id_strings: Optional book filter (only used when engine is None).
        model: Optional model name override for LLM selection.

    Returns:
        RAGResponse with answer, sources, warnings, stats.
    """
    if engine is None:
        engine = get_query_engine(book_id_strings=book_id_strings, model=model)

    response = engine.query(question)

    # source_nodes are already citation nodes (merged + labeled)
    # Source N label maps 1:1 to source_nodes[N-1] — no dedup needed
    sources = [
        build_source(nws, i)
        for i, nws in enumerate(response.source_nodes, start=1)
    ]
    normalize_scores(sources)

    answer = str(response)

    # Warnings
    warnings: list[str] = []
    if not response.source_nodes:
        warnings.append("No chunks retrieved — answer is unsupported by any source.")

    return RAGResponse(
        answer=answer,
        sources=sources,
        warnings=warnings,
        stats={
            "source_count": len(response.source_nodes),
        },
    )
