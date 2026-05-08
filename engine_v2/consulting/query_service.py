"""consulting.query_service — Unified consulting query execution.

Single pipeline for all consulting queries:
    1. Build collection list (persona + optional user_private + optional multi)
    2. Single collection → get_query_engine() (hybrid internally)
    3. Multiple collections → multi_collection_retrieve() + RRF (with collection
       boosts) → RelevanceFilter → CrossEncoder rerank → citation → synthesize

All paths use hybrid BM25+Vector retrieval with reranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from engine_v2.personas.registry import get_collection_count as _get_collection_count
from engine_v2.retrievers.hybrid import multi_collection_retrieve
from engine_v2.schema import build_source, normalize_scores
from engine_v2.user_docs.manager import user_collection_name as _user_collection_name


# ── CJK query translation helpers ───────────────────────────
import re as _re
import unicodedata as _ud


def _contains_cjk(text: str) -> bool:
    """Return True if text contains CJK (Chinese/Japanese/Korean) characters."""
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":  # CJK Unified Ideographs
            return True
        cat = _ud.category(ch)
        if cat.startswith("Lo"):  # Other Letter — covers CJK extension blocks
            try:
                name = _ud.name(ch, "")
                if "CJK" in name or "HANGUL" in name or "HIRAGANA" in name or "KATAKANA" in name:
                    return True
            except ValueError:
                pass
    return False


def _translate_to_english(text: str) -> str:
    """Translate CJK text → English using local Ollama for retrieval.

    Uses qwen3:1.7b with /no_think for minimal latency (~1-2s).
    Runs synchronously because the calling code path is sync.
    """
    try:
        from engine_v2.llms.resolver import resolve_llm
        llm = resolve_llm(model="qwen3:1.7b", provider="ollama")
        prompt = (
            "/no_think\n"
            "Translate the following text to English. "
            "Output ONLY the English translation, nothing else:\n\n"
            f"{text}"
        )
        # Sync complete (LlamaIndex Ollama supports sync .complete)
        response = llm.complete(prompt)
        translated = str(response)
        # Strip <think>...</think> if present
        translated = _re.sub(r"<think>.*?</think>\s*", "", translated, flags=_re.DOTALL).strip()
        if translated:
            logger.info("Query CJK→EN translation: '{}' → '{}'", text, translated)
            return translated
    except Exception as e:
        logger.warning("CJK→EN translation failed ({}), using original query", e)
    return text


def _condense_question(
    question: str,
    chat_history: list[dict[str, str]],
) -> str:
    """Rewrite a follow-up question into a standalone question using chat history.

    When the user asks '有效期是多久' after discussing study permits, this
    expands it to 'What is the validity period of a study permit?' so the
    retrieval system can find relevant documents.

    Uses the same lightweight qwen3:1.7b model for minimal latency.
    Returns the original question if rewriting fails or isn't needed.
    """
    if not chat_history:
        return question

    # Only use recent history (last 3 turns = 6 messages max)
    recent = chat_history[-6:]
    history_text = "\n".join(
        f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')[:300]}"
        for m in recent
    )

    try:
        from engine_v2.llms.resolver import resolve_llm
        llm = resolve_llm(model="qwen3:1.7b", provider="ollama")
        prompt = (
            "/no_think\n"
            "Given the following conversation history and a follow-up question, "
            "rewrite the follow-up question as a standalone question that "
            "includes all necessary context. If the question is already "
            "standalone, return it as-is. "
            "Output ONLY the rewritten question, nothing else.\n\n"
            f"Chat History:\n{history_text}\n\n"
            f"Follow-up Question: {question}\n"
            f"Standalone Question: "
        )
        response = llm.complete(prompt)
        condensed = str(response)
        condensed = _re.sub(r"<think>.*?</think>\s*", "", condensed, flags=_re.DOTALL).strip()
        if condensed:
            logger.info("Condensed question: '{}' → '{}'", question, condensed)
            return condensed
    except Exception as e:
        logger.warning("Question condensation failed ({}), using original", e)
    return question


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
    retrieval_question: str = ""  # English query used for retrieval (may differ from user input if CJK)


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
    chat_history: list[dict[str, str]] | None = None,
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

    # ── Step 0a: Condense follow-up questions using chat history ──
    effective_question = question
    if chat_history:
        effective_question = _condense_question(question, chat_history)

    # ── Step 0b: CJK query translation for retrieval ──
    # Knowledge base is English; translate CJK queries for better BM25/vector hits.
    retrieval_question = effective_question  # used for retrieval
    if _contains_cjk(effective_question):
        retrieval_question = _translate_to_english(effective_question)

    # ── Step 0c: Auto book_id pre-filter ──
    # When no explicit book_id_strings are provided, auto-match query keywords
    # against book_id paths to narrow retrieval scope (e.g. 23k → 50 chunks).
    if not book_id_strings:
        from engine_v2.retrievers.book_filter import prefilter_book_ids
        auto_book_ids = prefilter_book_ids(
            retrieval_question, collection_name, max_books=15,
        )
        if auto_book_ids:
            book_id_strings = auto_book_ids
            logger.info(
                "Auto book_id filter: {} books selected for query '{}'",
                len(auto_book_ids), retrieval_question[:60],
            )

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
        # CJK: use translated English for both retrieval and synthesis
        response = engine.query(retrieval_question)

        sources = []
        for i, nws in enumerate(response.source_nodes, start=1):
            sources.append(build_source(nws, i))
        normalize_scores(sources)

        # Defense-in-depth: hard filter sources by book_id_strings
        # MetadataFilters + BookFilterPostprocessor should have done this,
        # but this guarantees no leaked results from outside the book scope.
        if book_id_strings:
            allowed = set(book_id_strings)
            before = len(sources)
            sources = [s for s in sources if s.get("book_id", "") in allowed]
            if len(sources) < before:
                logger.info(
                    "Hard book_id filter: {} → {} sources (dropped {} out-of-scope)",
                    before, len(sources), before - len(sources),
                )

        return ConsultingQueryResult(
            sources=sources, response=response, kb_count=kb_count,
            retrieval_question=retrieval_question,
        )

    # ── Step 3: Multiple collections → hybrid retrieve each → RRF → rerank → synthesize ──
    from engine_v2.settings import (
        RERANKER_ENABLED,
        RERANKER_MODEL,
        RERANKER_TOP_N,
        SIMILARITY_CUTOFF,
    )

    # Over-fetch 3× from each collection to give reranker enough candidates.
    # With 300-500 char chunks, definition-type chunks may rank 10-15 in BM25
    # (low term frequency) but should be boosted by the CrossEncoder reranker.
    retrieval_k = top_k * 3 if RERANKER_ENABLED else top_k

    merged_nodes = multi_collection_retrieve(
        question=retrieval_question,
        collection_names=collection_names,
        top_k=retrieval_k,
        book_id_strings=book_id_strings,
    )

    # ── Post-processing: same layers as single-collection path ──
    from llama_index.core.schema import QueryBundle as QB
    # All answers in English — use retrieval_question (= English) for everything
    query_bundle = QB(query_str=retrieval_question)

    # Layer 1.5: MinContentFilter — drop headings/titles with no real content
    from engine_v2.query_engine.citation import MinContentPostprocessor, RelevanceFilterPostprocessor
    min_content_filter = MinContentPostprocessor(min_chars=50, min_single_line=120)
    merged_nodes = min_content_filter.postprocess_nodes(
        merged_nodes, query_bundle=query_bundle,
    )

    # Layer 2.5: RelevanceFilter — drop vector-only noise with K:0.00
    relevance_filter = RelevanceFilterPostprocessor(
        min_vector_score=0.55,
        min_bm25_score=1.0,
    )
    merged_nodes = relevance_filter.postprocess_nodes(
        merged_nodes, query_bundle=query_bundle,
    )

    # Layer 3: CrossEncoder reranker
    if RERANKER_ENABLED:
        reranker_top_n = min(RERANKER_TOP_N, top_k)
        try:
            from llama_index.core.postprocessor import SentenceTransformerRerank
            reranker = SentenceTransformerRerank(
                model=RERANKER_MODEL,
                top_n=reranker_top_n,
                keep_retrieval_score=True,
            )
            merged_nodes = reranker.postprocess_nodes(
                merged_nodes, query_bundle=query_bundle,
            )
            logger.info(
                "Multi-collection reranker applied: {} → {} nodes (model={})",
                retrieval_k, len(merged_nodes), RERANKER_MODEL,
            )
        except ImportError:
            logger.warning("SentenceTransformerRerank unavailable for multi-collection path")

    # Layer 4: Similarity cutoff
    # IMPORTANT: Skip when CrossEncoder reranker was applied above.
    # CrossEncoder scores are raw logits (range -∞ to +∞, negative is common),
    # NOT cosine similarity (0~1). Applying a positive cutoff like 0.05 would
    # drop every single node. The reranker's top_n already handles pruning.
    if SIMILARITY_CUTOFF > 0 and not RERANKER_ENABLED:
        try:
            from llama_index.core.postprocessor import SimilarityPostprocessor
            sim_filter = SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)
            merged_nodes = sim_filter.postprocess_nodes(
                merged_nodes, query_bundle=query_bundle,
            )
        except ImportError:
            pass

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
        query=QueryBundle(query_str=retrieval_question),
        nodes=citation_nodes,
    )
    return ConsultingQueryResult(
        sources=sources, response=response, kb_count=kb_count,
        retrieval_question=retrieval_question,
    )
