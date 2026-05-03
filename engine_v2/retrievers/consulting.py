"""consulting — Dual-collection retrieval for consulting personas.

Responsibilities:
    - Retrieve from persona and user-private ChromaDB collections.
    - Merge results with Reciprocal Rank Fusion.
    - Preserve source provenance for consulting citations.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger


from engine_v2.response_synthesizers.citation import get_citation_synthesizer
from engine_v2.schema import build_source, normalize_scores
from engine_v2.settings import CHROMA_PERSIST_DIR, TOP_K


RRF_K = 60


def _retrieve_from_collection(
    question: str,
    collection_name: str,
    origin_tag: str,
    top_k: int,
) -> list[NodeWithScore]:
    """Retrieve nodes from one ChromaDB collection and tag provenance."""
    try:
        client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        if collection.count() == 0:
            logger.debug("Collection {} is empty, skipping", collection_name)
            return []

        vector_store = ChromaVectorStore(chroma_collection=collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(question)

        for node_with_score in nodes:
            node_with_score.node.metadata["retrieval_origin"] = origin_tag

        logger.debug(
            "Retrieved {} nodes from {} ({})",
            len(nodes), collection_name, origin_tag,
        )
        return nodes
    except Exception as exc:
        logger.warning("Retrieval from {} failed: {}", collection_name, exc)
        return []


def _merge_with_rrf(
    persona_nodes: list[NodeWithScore],
    user_nodes: list[NodeWithScore],
    top_k: int,
) -> list[NodeWithScore]:
    """Merge two ranked node lists using Reciprocal Rank Fusion."""
    scored: dict[str, tuple[float, NodeWithScore]] = {}

    for rank, node_with_score in enumerate(persona_nodes, start=1):
        node_id = node_with_score.node.id_
        scored[node_id] = (1.0 / (RRF_K + rank), node_with_score)

    for rank, node_with_score in enumerate(user_nodes, start=1):
        node_id = node_with_score.node.id_
        rrf_score = 1.0 / (RRF_K + rank)
        if node_id in scored:
            existing_score, existing_node = scored[node_id]
            scored[node_id] = (existing_score + rrf_score, existing_node)
        else:
            scored[node_id] = (rrf_score, node_with_score)

    merged = sorted(scored.values(), key=lambda item: item[0], reverse=True)[:top_k]
    merged_nodes: list[NodeWithScore] = []
    for rrf_score, node_with_score in merged:
        node_with_score.score = rrf_score
        merged_nodes.append(node_with_score)
    return merged_nodes


def _source_type_from_origin(origin: str) -> str:
    """Map internal retrieval origin to public consulting source type."""
    return "user_doc" if origin == "user_private" else "persona"


def dual_collection_query(
    question: str,
    persona_collection: str,
    user_collection: str,
    system_prompt: str,
    top_k: int = TOP_K,
    model: str | None = None,
    provider: str | None = None,
    streaming: bool = False,
) -> tuple[list[dict[str, Any]], Any]:
    """Query persona and user-private collections, then synthesize an answer."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        persona_future = executor.submit(
            _retrieve_from_collection,
            question,
            persona_collection,
            "persona_kb",
            top_k,
        )
        user_future = executor.submit(
            _retrieve_from_collection,
            question,
            user_collection,
            "user_private",
            top_k,
        )
        persona_nodes = persona_future.result()
        user_nodes = user_future.result()

    merged_nodes = _merge_with_rrf(persona_nodes, user_nodes, top_k)
    logger.info(
        "Dual-collection RRF: {} persona + {} user → {} merged",
        len(persona_nodes), len(user_nodes), len(merged_nodes),
    )

    synthesizer = get_citation_synthesizer(
        streaming=streaming,
        model=model,
        provider=provider,
        custom_system_prompt=system_prompt,
    )
    # Lazy import to break circular dependency:
    # citation → retrievers.hybrid → retrievers.__init__ → consulting → citation
    from engine_v2.query_engine.citation import TextbookCitationQueryEngine

    engine = TextbookCitationQueryEngine(
        retriever=None,  # type: ignore[arg-type]
        response_synthesizer=synthesizer,
    )
    citation_nodes = engine._create_citation_nodes(merged_nodes)

    sources = []
    for index, node_with_score in enumerate(citation_nodes, start=1):
        source = build_source(node_with_score, index)
        origin = node_with_score.node.metadata.get("retrieval_origin", "unknown")
        source["retrieval_origin"] = origin
        source["source_type"] = _source_type_from_origin(origin)
        sources.append(source)
    normalize_scores(sources)

    response = synthesizer.synthesize(
        query=QueryBundle(query_str=question),
        nodes=citation_nodes,
    )
    return sources, response


# ============================================================
# Multi-collection retrieval (G7-10)
# ============================================================


def _merge_n_with_rrf(
    ranked_lists: list[list[NodeWithScore]],
    top_k: int,
) -> list[NodeWithScore]:
    """Merge N ranked node lists using Reciprocal Rank Fusion."""
    scored: dict[str, tuple[float, NodeWithScore]] = {}

    for nodes in ranked_lists:
        for rank, nws in enumerate(nodes, start=1):
            node_id = nws.node.id_
            rrf_score = 1.0 / (RRF_K + rank)
            if node_id in scored:
                existing_score, existing_node = scored[node_id]
                scored[node_id] = (existing_score + rrf_score, existing_node)
            else:
                scored[node_id] = (rrf_score, nws)

    merged = sorted(scored.values(), key=lambda item: item[0], reverse=True)[:top_k]
    result: list[NodeWithScore] = []
    for rrf_score, nws in merged:
        nws.score = rrf_score
        result.append(nws)
    return result


def multi_collection_retrieve(
    question: str,
    collection_names: list[str],
    top_k: int = TOP_K,
) -> list[NodeWithScore]:
    """Retrieve from multiple ChromaDB collections in parallel, merge via RRF.

    Each collection is tagged with its name as retrieval_origin so sources
    can be traced back to the originating knowledge base.

    Args:
        question: User query string.
        collection_names: List of ChromaDB collection names to search.
        top_k: Number of merged results to return.

    Returns:
        Merged and ranked list of NodeWithScore.
    """
    with ThreadPoolExecutor(max_workers=len(collection_names)) as executor:
        futures = [
            executor.submit(
                _retrieve_from_collection,
                question,
                coll_name,
                coll_name,  # use collection name as origin tag
                top_k,
            )
            for coll_name in collection_names
        ]
        ranked_lists = [f.result() for f in futures]

    merged = _merge_n_with_rrf(ranked_lists, top_k)
    counts = {name: len(nodes) for name, nodes in zip(collection_names, ranked_lists)}
    logger.info(
        "Multi-collection RRF: {} → {} merged",
        counts, len(merged),
    )
    return merged


