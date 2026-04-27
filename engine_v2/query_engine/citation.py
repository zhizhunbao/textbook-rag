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
    ├── retrieve()  → HybridRetriever → BookFilterPostprocessor → Reranker
    ├── _create_citation_nodes()  → merge same-page + add Source N labels
    └── synthesize() → CitationSynthesizer (COMPACT + citation prompts)

Ref: llama_index.core.query_engine.citation_query_engine
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from loguru import logger

from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.response_synthesizers import BaseSynthesizer
from llama_index.core.schema import (
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
    reranker: str | None = None,
    custom_system_prompt: str | None = None,
) -> TextbookCitationQueryEngine:
    """Build a TextbookCitationQueryEngine with 4-layer retrieval defense.

    Architecture:
        TextbookCitationQueryEngine
        ├── retriever  → QueryFusionRetriever (BM25 + Vector → RRF)
        │                Over-fetches 2× to give reranker enough candidates
        ├── _create_citation_nodes  → dedup + Source N labels
        ├── synthesizer → CitationSynthesizer (COMPACT + citation prompts)
        └── postprocessors (4-layer defense):
            Layer 1: MetadataFilters on BM25 (in hybrid.py — corpus_weight_mask)
            Layer 2: BookFilterPostprocessor (post-filter BM25 by book scope)
            Layer 3: SentenceTransformerRerank (CrossEncoder semantic reranking)
            Layer 4: SimilarityPostprocessor (score cutoff for low-relevance)
            Layer 5: LLMRerank (optional — when user explicitly enables)

    Ref: llama_index.core.postprocessor.sbert_rerank.SentenceTransformerRerank
    Ref: llama_index.core.postprocessor.node.SimilarityPostprocessor
    Ref: llama_index.core.postprocessor.llm_rerank.LLMRerank
    """
    from engine_v2.settings import (
        RERANKER_ENABLED,
        RERANKER_MODEL,
        RERANKER_TOP_N,
        SIMILARITY_CUTOFF,
    )

    # Over-fetch 2× from retriever to give reranker enough candidates to filter
    # The reranker will trim back down to similarity_top_k
    retrieval_k = similarity_top_k * 2 if RERANKER_ENABLED else similarity_top_k

    retriever = get_hybrid_retriever(
        similarity_top_k=retrieval_k,
        book_id_strings=book_id_strings,
    )
    synthesizer = get_citation_synthesizer(
        streaming=streaming, model=model, provider=provider,
        custom_system_prompt=custom_system_prompt,
    )

    # ── Build postprocessor chain (order matters!) ──
    postprocessors: list[BaseNodePostprocessor] = []

    # Layer 2: BookFilterPostprocessor — post-filter BM25 results by book scope
    # (Layer 1 is MetadataFilters on BM25 in hybrid.py)
    if book_id_strings:
        postprocessors.append(
            BookFilterPostprocessor(book_id_strings=book_id_strings)
        )

    # Layer 3: SentenceTransformerRerank — CrossEncoder semantic reranking
    # Ref: llama_index.core.postprocessor.sbert_rerank.SentenceTransformerRerank
    # This is the key defense against BM25 cross-book noise:
    #   CrossEncoder scores (query, chunk) pairs by semantic relevance,
    #   so "Ottawa inflation rate" vs "Bayesian exercise with inflation variable"
    #   gets correctly distinguished.
    if RERANKER_ENABLED:
        reranker_top_n = min(RERANKER_TOP_N, similarity_top_k)
        try:
            from llama_index.core.postprocessor import SentenceTransformerRerank
            postprocessors.append(
                SentenceTransformerRerank(
                    model=RERANKER_MODEL,
                    top_n=reranker_top_n,
                    keep_retrieval_score=True,  # preserve original score in metadata
                )
            )
            logger.info(
                "SentenceTransformerRerank enabled (model={}, top_n={})",
                RERANKER_MODEL, reranker_top_n,
            )
        except ImportError:
            logger.warning(
                "SentenceTransformerRerank unavailable — "
                "install sentence-transformers: pip install sentence-transformers"
            )

    # Layer 4: SimilarityPostprocessor — drop chunks below score cutoff
    # Ref: llama_index.core.postprocessor.node.SimilarityPostprocessor
    if SIMILARITY_CUTOFF > 0:
        try:
            from llama_index.core.postprocessor import SimilarityPostprocessor
            postprocessors.append(
                SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)
            )
            logger.info("SimilarityPostprocessor enabled (cutoff={})", SIMILARITY_CUTOFF)
        except ImportError:
            logger.warning("SimilarityPostprocessor unavailable")

    # Layer 5 (optional): LLMRerank — LLM judges chunk relevance
    # Only activated when user explicitly requests via reranker parameter
    # Ref: llama_index.core.postprocessor.llm_rerank.LLMRerank
    if reranker:
        reranker_top_n = min(similarity_top_k, 5)
        try:
            from llama_index.core.postprocessor import LLMRerank
            postprocessors.append(LLMRerank(top_n=reranker_top_n))
            logger.info("LLMRerank enabled (top_n={})", reranker_top_n)
        except ImportError:
            logger.warning("LLMRerank unavailable — skipping")

    engine = TextbookCitationQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
        node_postprocessors=postprocessors,
    )

    filter_desc = f", books={book_id_strings}" if book_id_strings else ""
    reranker_desc = f", reranker={reranker}" if reranker else ""
    pp_names = [type(pp).__name__ for pp in postprocessors]
    logger.info(
        "TextbookCitationQueryEngine ready (top_k={}, retrieval_k={}, streaming={}, model={}{}{}, postprocessors={})",
        similarity_top_k, retrieval_k, streaming, model or 'default',
        filter_desc, reranker_desc, pp_names,
    )
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
