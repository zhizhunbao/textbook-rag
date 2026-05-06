"""consulting.query_service — Unified consulting query execution.

Single pipeline for all consulting queries:
    1. Build collection list (persona + optional user_private + optional multi)
    2. Single collection → get_query_engine() (hybrid internally)
    3. Multiple collections → multi_collection_retrieve() + RRF → citation → synthesize

All paths use hybrid BM25+Vector retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from engine_v2.personas.registry import get_collection_count as _get_collection_count
from engine_v2.retrievers.hybrid import multi_collection_retrieve
from engine_v2.schema import build_source, normalize_scores
from engine_v2.user_docs.manager import user_collection_name as _user_collection_name


@dataclass
class ConsultingQueryResult:
    """Result of a consulting query execution.

    Attributes:
        sources: List of source dicts for citation display.
        response: LlamaIndex response object (supports .response_gen for streaming).
        kb_count: Total chunk count in the persona's knowledge base(s).
    """

    sources: list[dict[str, Any]] = field(default_factory=list)
    response: Any = None
    kb_count: int = 0


def execute_consulting_query(
    *,
    question: str,
    persona: dict[str, Any],
    collection_name: str,
    system_prompt: str,
    top_k: int,
    model: str | None = None,
    provider: str | None = None,
    streaming: bool = False,
    user_id: int | str | None = None,
    country: str = "ca",
    persona_slug: str = "",
    book_id_strings: list[str] | None = None,
) -> ConsultingQueryResult:
    """Execute a RAG query against a persona's knowledge base.

    Unified pipeline:
        1. Build collection list from persona config + user context
        2. Single collection → get_query_engine (hybrid BM25+Vector internally)
        3. Multiple collections → multi_collection_retrieve → RRF → synthesize
    """
    from engine_v2.query_engine.citation import TextbookCitationQueryEngine, get_query_engine
    from engine_v2.query_engine.synthesizer import get_citation_synthesizer
    from llama_index.core.schema import QueryBundle

    # ── Step 1: Build collection list ──
    multi_collections = persona.get("multiCollections") or []

    if multi_collections:
        # Persona has explicit multi-collection config
        collection_names = list(multi_collections)
    else:
        # Start with persona's single collection
        collection_names = [collection_name]

    # Add user-private collection if user has uploaded docs
    if user_id:
        user_coll = _user_collection_name(user_id, persona_slug, country)
        if user_coll not in collection_names:
            collection_names.append(user_coll)

    # Calculate KB size
    kb_count = sum(_get_collection_count(c) for c in collection_names)

    # ── Step 2: Single collection → get_query_engine (already hybrid) ──
    if len(collection_names) == 1:
        engine = get_query_engine(
            similarity_top_k=top_k,
            streaming=streaming,
            collection_name=collection_names[0],
            custom_system_prompt=system_prompt,
            model=model,
            provider=provider,
            book_id_strings=book_id_strings,
        )
        response = engine.query(question)

        sources = []
        for i, nws in enumerate(response.source_nodes, start=1):
            sources.append(build_source(nws, i))
        normalize_scores(sources)

        return ConsultingQueryResult(
            sources=sources, response=response, kb_count=kb_count,
        )

    # ── Step 3: Multiple collections → hybrid retrieve each → RRF → synthesize ──
    merged_nodes = multi_collection_retrieve(
        question=question,
        collection_names=collection_names,
        top_k=top_k,
    )
    synthesizer = get_citation_synthesizer(
        streaming=streaming,
        model=model,
        provider=provider,
        custom_system_prompt=system_prompt,
    )
    engine = TextbookCitationQueryEngine(
        retriever=None,  # type: ignore[arg-type]
        response_synthesizer=synthesizer,
    )
    citation_nodes = engine._create_citation_nodes(merged_nodes)

    sources = []
    for i, nws in enumerate(citation_nodes, start=1):
        source = build_source(nws, i)
        origin = nws.node.metadata.get("retrieval_origin", "unknown")
        source["retrieval_origin"] = origin
        sources.append(source)
    normalize_scores(sources)

    response = synthesizer.synthesize(
        query=QueryBundle(query_str=question),
        nodes=citation_nodes,
    )
    return ConsultingQueryResult(
        sources=sources, response=response, kb_count=kb_count,
    )
