"""consulting.query_service — Unified consulting query execution.

Consolidates the 3-branch query logic (dual-collection / multi-collection /
single-collection) into a single function used by both sync and streaming
endpoints.

Architecture:
    _execute_consulting_query()
    ├── Branch 1: user_id present → dual_collection_query (persona + user private)
    ├── Branch 2: multiCollections → multi_collection_retrieve + RRF merge
    └── Branch 3: default → get_query_engine (single persona collection)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from engine_v2.personas.registry import get_collection_count as _get_collection_count
from engine_v2.retrievers.consulting import dual_collection_query, multi_collection_retrieve
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

    Unifies the 3 retrieval branches:
        1. user_id present → dual-collection (persona + user private)
        2. multiCollections defined → multi-collection RRF merge
        3. default → single collection via get_query_engine

    Returns:
        ConsultingQueryResult with sources, response, and kb_count.
    """
    from engine_v2.query_engine.citation import TextbookCitationQueryEngine, get_query_engine
    from engine_v2.response_synthesizers.citation import get_citation_synthesizer
    from llama_index.core.schema import QueryBundle

    multi_collections = persona.get("multiCollections") or []

    # Calculate KB size for warnings
    if multi_collections:
        kb_count = sum(_get_collection_count(c) for c in multi_collections)
    else:
        kb_count = _get_collection_count(collection_name)

    # ── Branch 1: Dual-collection (persona + user private) ──
    if user_id:
        user_coll = _user_collection_name(user_id, persona_slug, country)
        sources, response = dual_collection_query(
            question=question,
            persona_collection=collection_name,
            user_collection=user_coll,
            system_prompt=system_prompt,
            top_k=top_k,
            model=model,
            provider=provider,
            streaming=streaming,
        )
        return ConsultingQueryResult(
            sources=sources, response=response, kb_count=kb_count,
        )

    # ── Branch 2: Multi-collection RRF merge ──
    if multi_collections:
        merged_nodes = multi_collection_retrieve(
            question=question,
            collection_names=multi_collections,
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

    # ── Branch 3: Single collection (default) ──
    engine = get_query_engine(
        similarity_top_k=top_k,
        streaming=streaming,
        collection_name=collection_name,
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
