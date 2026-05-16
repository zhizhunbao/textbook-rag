"""consulting routes — Persona knowledge base query + ingest + user private docs.

Thin routing shell that delegates to engine_v2.consulting.* sub-modules.

Endpoints (C2 — Persona Knowledge Base):
    POST   /engine/consulting/ingest        — ingest PDF into persona collection
    POST   /engine/consulting/query         — RAG query against persona collection
    POST   /engine/consulting/query/stream  — SSE streaming query against persona
    POST   /engine/consulting/retrieve      — lightweight BM25+Vector retrieval only
                                              (no rerank, no synthesis — for cite_rag.py)

Endpoints delegated to sub-routers:
    GET    /engine/consulting/personas      — (consulting.personas)
    GET    /engine/consulting/status/{slug}  — (consulting.personas)
    POST   /engine/consulting/user-doc/ingest   — (consulting.user_docs)
    GET    /engine/consulting/user-doc/list      — (consulting.user_docs)
    DELETE /engine/consulting/user-doc/{doc_id}  — (consulting.user_docs)

C4 — Dual-Collection Retrieval:
    When user_id is provided in query requests, retrieves from BOTH the
    persona collection AND the user's private collection, merging results
    via Reciprocal Rank Fusion.

Reuses the existing MinerU → MinerUReader → IngestionPipeline chain.
Each persona writes to its own ChromaDB collection (persona_{slug}).
User private docs go to user_{userId}_{personaSlug} collections.
"""

from __future__ import annotations

import threading
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from engine_v2.consulting.helpers import (
    _append_disclaimer,
    _generate_no_retrieval_reply,
    _generate_small_talk_reply,
    _normalize_citations,
    _sse,
    is_small_talk,
)
from engine_v2.consulting.prompts import build_system_prompt as _build_system_prompt
from engine_v2.consulting.query_service import execute_consulting_query
from engine_v2.consulting.keyword_extractor import extract_answer_keywords, extract_numeric_highlights, extract_source_numeric_highlights, extract_verified_keywords, _extract_numeric_values
from engine_v2.consulting.personas import router as personas_router
from engine_v2.consulting.user_docs import router as user_docs_router
from engine_v2.personas.registry import (
    fetch_persona as _fetch_persona,
    get_collection_name as _get_persona_collection,
)
from engine_v2.settings import (
    DATA_DIR,
    MINERU_OUTPUT_DIR,
    TOP_K,
)

router = APIRouter(prefix="/consulting", tags=["consulting"])

# Include sub-routers (personas + user-docs endpoints)
# They already have prefix="/consulting", so we strip it to avoid duplication
router.include_router(personas_router, prefix="")
router.include_router(user_docs_router, prefix="")


# ============================================================
# Request / Response models
# ============================================================


class PersonaIngestRequest(BaseModel):
    """Ingest a PDF into a persona's knowledge base."""

    persona_slug: str
    pdf_filename: str
    book_dir_name: str | None = None  # auto-derived from pdf_filename if omitted
    force_parse: bool = False


class PersonaQueryRequest(BaseModel):
    """Query a persona's knowledge base (C4: with optional dual-collection)."""

    persona_slug: str
    question: str
    top_k: int = TOP_K
    model: str | None = None
    provider: str | None = None
    country: str = "ca"  # ISO 3166-1 alpha-2
    response_language: str | None = None  # G1-07: language override
    # G8-02: Support textbook persona book_id filtering
    book_id_strings: list[str] | None = None
    # Chat history for follow-up question contextualization
    chat_history: list[dict[str, str]] | None = None
    # GO-MU-06: user_id removed from body — now extracted from JWT auth


class PersonaRetrieveRequest(BaseModel):
    """Retrieve raw chunks from a persona's knowledge base.

    Lightweight retrieval-only endpoint — no reranker, no LLM synthesis.
    Returns raw BM25+Vector hybrid results for external tools (cite_rag.py)
    where the Agent handles quality judgment instead of CrossEncoder.

    Two modes (mutually exclusive):
      1. persona_slug — resolve collections via Payload CMS persona config
      2. collection_names — direct collection access (bypasses persona lookup)
    """

    persona_slug: str | None = None
    collection_names: list[str] | None = None
    question: str
    top_k: int = 10


# ============================================================
# POST /engine/consulting/ingest — PDF → persona collection
# ============================================================


@router.post("/ingest")
async def consulting_ingest(req: PersonaIngestRequest):
    """Ingest a PDF into a persona's ChromaDB collection.

    Reuses the full MinerU → MinerUReader → IngestionPipeline chain.
    The only difference from textbook ingest is the target collection.

    PDF is expected at: data/raw_pdfs/consulting/{persona_slug}/{pdf_filename}
    MinerU output goes to: data/mineru_output/consulting/{book_dir_name}/
    """
    from engine_v2.api.routes.ingest import _run_mineru_parse
    from engine_v2.ingestion.pipeline import ingest_book

    # Derive book_dir_name from pdf_filename if not provided
    book_dir_name = req.book_dir_name
    if not book_dir_name:
        stem = Path(req.pdf_filename).stem
        safe = stem.lower().replace(" ", "_").replace("-", "_")
        book_dir_name = safe

    collection_name = _get_persona_collection(req.persona_slug)
    category = "consulting"

    # Locate PDF
    pdf_dir = DATA_DIR / "raw_pdfs" / "consulting" / req.persona_slug
    pdf_path = pdf_dir / req.pdf_filename
    if not pdf_path.exists():
        # Fallback: check directly under consulting/
        pdf_path = DATA_DIR / "raw_pdfs" / "consulting" / req.pdf_filename
    if not pdf_path.exists():
        return {
            "status": "error",
            "message": f"PDF not found: {req.pdf_filename}. "
            f"Expected at: {pdf_dir / req.pdf_filename}",
        }

    # Check existing MinerU output
    auto_dir = (
        MINERU_OUTPUT_DIR / category / book_dir_name / book_dir_name / "auto"
    )
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"

    def _run():
        try:
            # Step 1: MinerU parse (if not already done)
            if req.force_parse or not content_list_path.exists():
                logger.info(
                    "Parsing PDF for persona {}: {}",
                    req.persona_slug, pdf_path,
                )
                _run_mineru_parse(pdf_path, book_dir_name, category)
            else:
                logger.info(
                    "MinerU output exists for {}, skipping parse",
                    book_dir_name,
                )

            # Step 2: Ingest into persona collection
            # book_id=0 because consulting docs don't map to Payload books
            result = ingest_book(
                book_id=0,
                book_dir_name=book_dir_name,
                category=category,
                collection_name=collection_name,
            )
            logger.info(
                "Consulting ingest complete: persona={}, collection={}, chunks={}",
                req.persona_slug,
                collection_name,
                result.get("chunk_count", 0),
            )
        except Exception as e:
            logger.exception(
                "Consulting ingest failed: persona={}, error={}",
                req.persona_slug, e,
            )

    # Run in background thread
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "status": "accepted",
        "persona_slug": req.persona_slug,
        "collection_name": collection_name,
        "book_dir_name": book_dir_name,
        "pdf_path": str(pdf_path),
    }


# ============================================================
# POST /engine/consulting/query — sync RAG query
# ============================================================


@router.post("/query")
async def consulting_query(req: PersonaQueryRequest, request: Request):
    """Execute a RAG query against a persona's knowledge base.

    C4 Dual-Collection: When user_id is provided, retrieves from BOTH
    the persona collection AND the user's private collection, then merges
    results via RRF before synthesis.

    Uses the persona's systemPrompt as the QA template.
    """
    persona = _fetch_persona(req.persona_slug)
    if not persona:
        return {"status": "error", "message": f"Persona not found: {req.persona_slug}"}

    collection_name = persona.get("chromaCollection", f"persona_{req.persona_slug}")
    system_prompt = _build_system_prompt(persona, req.response_language)

    # G7-03: Skip RAG for greetings / small-talk
    if is_small_talk(req.question):
        reply = await _generate_small_talk_reply(
            question=req.question,
            system_prompt=system_prompt,
            persona_name=persona.get("name", req.persona_slug),
            model=req.model,
            provider=req.provider,
        )
        return {
            "persona": {"name": persona.get("name"), "slug": persona.get("slug")},
            "answer": reply,
            "sources": [],
            "stats": {"source_count": 0},
            "highlight_keywords": [],
            "numeric_highlights": [],
            "answer_highlight_keywords": [],
        }

    # GO-MU-06: user_id from JWT auth
    user_data = getattr(request.state, "user", None)
    user_id = user_data.get("id") if user_data else None

    result = execute_consulting_query(
        question=req.question,
        persona=persona,
        collection_name=collection_name,
        system_prompt=system_prompt,
        top_k=req.top_k,
        model=req.model,
        provider=req.provider,
        streaming=False,
        user_id=user_id,
        country=req.country,
        persona_slug=req.persona_slug,
        book_id_strings=req.book_id_strings,
        chat_history=req.chat_history,
    )

    # G3: Guard against empty retrieval / "Empty Response"
    answer = str(result.response)
    if not result.sources or not answer or answer.strip().lower() == "empty response":
        answer = await _generate_no_retrieval_reply(
            question=req.question,
            system_prompt=system_prompt,
            persona_name=persona.get("name", req.persona_slug),
            model=req.model,
            provider=req.provider,
        )

    # G4-03: Auto-append disclaimer
    answer = _append_disclaimer(answer, req.question)

    # Normalize (Source N) → [N] bracket format for frontend parser
    answer = _normalize_citations(answer)

    # ── Extract cross-referenced highlight keywords ──
    q_for_keywords = result.retrieval_question or req.question
    source_texts = [s.get("full_content") or s.get("text", "") for s in result.sources]
    highlight_keywords = extract_verified_keywords(q_for_keywords, source_texts)
    numeric_highlights = extract_numeric_highlights(answer, source_texts)
    answer_keywords = extract_answer_keywords(answer, source_texts, highlight_keywords)

    # ── Enrich each source with per-source numeric highlights ──
    answer_numbers = _extract_numeric_values(answer)
    for src in result.sources:
        src_text = src.get("full_content") or src.get("text", "")
        src["numeric_highlights"] = extract_source_numeric_highlights(src_text, answer_numbers)

    return {
        "persona": {
            "name": persona.get("name"),
            "slug": persona.get("slug"),
        },
        "answer": answer,
        "sources": result.sources,
        "stats": {"source_count": len(result.sources)},
        "highlight_keywords": highlight_keywords,
        "numeric_highlights": numeric_highlights,
        "answer_highlight_keywords": answer_keywords,
    }


# ============================================================
# POST /engine/consulting/retrieve — lightweight chunk retrieval
# ============================================================
# No reranker, no LLM synthesis. Returns raw BM25+Vector chunks.
# Designed for external tools (cite_rag.py) where the Agent does
# quality judgment instead of CrossEncoder + GPT.


@router.post("/retrieve")
async def consulting_retrieve(req: PersonaRetrieveRequest):
    """Retrieve raw chunks from a persona's knowledge base.

    Lightweight endpoint that only runs BM25+Vector hybrid retrieval
    (no CrossEncoder rerank, no LLM synthesis). Returns raw chunks with
    metadata for external tools where the calling Agent handles judgment.

    Two modes:
      1. collection_names — direct collection access (preferred for cite_rag.py)
      2. persona_slug — resolve collections via Payload CMS persona config

    Cost: ~50ms (vs ~3s for /query with rerank + synthesis).
    """
    from engine_v2.retrievers.hybrid import multi_collection_retrieve
    from engine_v2.schema import build_source

    # ── Resolve collection names ──
    if req.collection_names:
        # Direct mode: use provided collection names as-is
        collection_names = list(req.collection_names)
    elif req.persona_slug:
        # Persona mode: resolve via Payload CMS
        persona = _fetch_persona(req.persona_slug)
        if not persona:
            return {"status": "error", "message": f"Persona not found: {req.persona_slug}"}
        multi_collections = persona.get("multiCollections") or []
        if multi_collections:
            collection_names = list(multi_collections)
        else:
            collection_name = persona.get("chromaCollection", f"persona_{req.persona_slug}")
            collection_names = [collection_name]
    else:
        return {"status": "error", "message": "Must provide either collection_names or persona_slug"}

    # Pure BM25+Vector retrieval — no rerank, no synthesis
    merged_nodes = multi_collection_retrieve(
        question=req.question,
        collection_names=collection_names,
        top_k=req.top_k,
    )

    # Convert to source dicts (minimal fields for cite_rag.py)
    chunks = []
    for i, nws in enumerate(merged_nodes, start=1):
        node = nws.node
        meta = node.metadata
        page_idx = meta.get("page_idx", 0)

        # Strip "Source N:" prefix if present
        import re
        content = node.get_content()
        content = re.sub(r"^Source \d+:\n", "", content)

        chunks.append({
            "rank": i,
            "book_id": meta.get("book_id", ""),
            "category": meta.get("category", ""),
            "page_number": page_idx + 1,
            "snippet": content[:300],
            "full_content": content[:2000],
            "score": round(float(nws.score), 6) if nws.score is not None else 0.0,
            "vector_score": round(float(meta.get("vector_score", 0)), 4),
            "bm25_score": round(float(meta.get("bm25_score", 0)), 4),
            "retrieval_source": meta.get("retrieval_source", "vector"),
        })

    logger.info(
        "[Retrieve] Q: {}... → {} chunks from {}",
        req.question[:60], len(chunks), collection_names,
    )

    return {
        "question": req.question,
        "total": len(chunks),
        "chunks": chunks,
    }


# ============================================================
# POST /engine/consulting/query/stream — SSE streaming query
# ============================================================


@router.post("/query/stream")
async def consulting_query_stream(req: PersonaQueryRequest, request: Request):
    """SSE streaming RAG query against a persona's knowledge base."""
    # GO-MU-06: Extract user_id from auth, attach to req for generator
    user_data = getattr(request.state, "user", None)
    req._auth_user_id = user_data.get("id") if user_data else None  # type: ignore[attr-defined]
    return StreamingResponse(
        _consulting_stream_generator(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _consulting_stream_generator(req: PersonaQueryRequest):
    """Async generator for consulting SSE streaming (C4: dual-collection)."""
    try:
        persona = _fetch_persona(req.persona_slug)
        if not persona:
            yield _sse("error", {"message": f"Persona not found: {req.persona_slug}"})
            return

        collection_name = persona.get(
            "chromaCollection", f"persona_{req.persona_slug}"
        )
        system_prompt = _build_system_prompt(persona, req.response_language)

        # G7-03: Skip RAG for greetings / small-talk
        if is_small_talk(req.question):
            logger.info("Small-talk detected, skipping RAG: {!r}", req.question)
            reply = await _generate_small_talk_reply(
                question=req.question,
                system_prompt=system_prompt,
                persona_name=persona.get("name", req.persona_slug),
                model=req.model,
                provider=req.provider,
            )
            yield _sse("retrieval_done", {
                "stats": {"source_count": 0},
                "sources": [],
                "highlight_keywords": [],
            })
            yield _sse("token", {"t": reply})
            yield _sse("done", {
                "persona": {"name": persona.get("name"), "slug": persona.get("slug")},
                "answer": reply,
                "sources": [],
                "stats": {"source_count": 0},
                "highlight_keywords": [],
                "numeric_highlights": [],
                "answer_highlight_keywords": [],
                "telemetry": {
                    "llm_calls": 1,
                    "input_tokens": len(req.question.split()) * 2,
                    "output_tokens": len(reply.split()),
                },
            })
            return

        # GO-MU-06: user_id from JWT auth
        user_id = getattr(req, "_auth_user_id", None)

        result = execute_consulting_query(
            question=req.question,
            persona=persona,
            collection_name=collection_name,
            system_prompt=system_prompt,
            top_k=req.top_k,
            model=req.model,
            provider=req.provider,
            streaming=True,
            user_id=user_id,
            country=req.country,
            persona_slug=req.persona_slug,
            book_id_strings=req.book_id_strings,
            chat_history=req.chat_history,
        )

        # G2: Warn if persona knowledge base is empty
        if result.kb_count == 0:
            yield _sse("warning", {
                "code": "empty_knowledge_base",
                "message": (
                    f"This advisor ({persona.get('name', req.persona_slug)}) "
                    "does not have a knowledge base yet. "
                    "Responses will not be grounded in domain-specific documents."
                ),
            })

        # Use English retrieval_question for keyword extraction (sources are in English)
        q_for_keywords = result.retrieval_question or req.question

        yield _sse("retrieval_done", {
            "stats": {"source_count": len(result.sources)},
            "sources": result.sources,
            "highlight_keywords": extract_verified_keywords(
                q_for_keywords,
                [s.get("full_content") or s.get("text", "") for s in result.sources],
            ),
        })

        # G3: If no chunks were retrieved, use a lightweight LLM call with
        # the persona's system prompt to generate a contextual "no results"
        # message — never hardcode static text.
        if len(result.sources) == 0:
            yield _sse("no_retrieval", {
                "message": "No relevant documents found for this question.",
            })
            fallback = await _generate_no_retrieval_reply(
                question=req.question,
                system_prompt=system_prompt,
                persona_name=persona.get("name", req.persona_slug),
                model=req.model,
                provider=req.provider,
            )
            # G4-03: Auto-append disclaimer to no-retrieval fallback
            fallback = _append_disclaimer(fallback, req.question)
            yield _sse("token", {"t": fallback})
            yield _sse("done", {
                "persona": {
                    "name": persona.get("name"),
                    "slug": persona.get("slug"),
                },
                "answer": fallback,
                "sources": [],
                "stats": {"source_count": 0},
                "telemetry": {
                    "llm_calls": 1,
                    "input_tokens": len(fallback.split()),
                    "output_tokens": len(fallback.split()),
                },
            })
            return

        # Stream tokens
        full_answer = ""
        output_token_count = 0
        response_gen = result.response.response_gen
        if response_gen is not None:
            for token in response_gen:
                full_answer += token
                output_token_count += 1
                yield _sse("token", {"t": token})
        else:
            full_answer = str(result.response)
            output_token_count = len(full_answer.split())

        # G3: Guard against LlamaIndex returning "Empty Response" when
        # synthesis produces no content despite having source nodes.
        if not full_answer or full_answer.strip().lower() == "empty response":
            full_answer = await _generate_no_retrieval_reply(
                question=req.question,
                system_prompt=system_prompt,
                persona_name=persona.get("name", req.persona_slug),
                model=req.model,
                provider=req.provider,
            )
            output_token_count = len(full_answer.split())

        # G4-03: Auto-append disclaimer
        full_answer = _append_disclaimer(full_answer, req.question)

        # Normalize (Source N) → [N] bracket format for frontend parser
        full_answer = _normalize_citations(full_answer)

        # Estimate input tokens: question + source chunks
        context_text = " ".join(s.get("full_content", "") or "" for s in result.sources)
        input_token_estimate = int(
            (len(req.question.split()) + len(context_text.split())) / 0.75
        )

        done_source_texts = [s.get("full_content") or s.get("text", "") for s in result.sources]
        done_q_keywords = extract_verified_keywords(q_for_keywords, done_source_texts)
        done_answer_keywords = extract_answer_keywords(full_answer, done_source_texts, done_q_keywords)

        # Enrich each source with per-source numeric highlights
        answer_numbers = _extract_numeric_values(full_answer)
        for src in result.sources:
            src_text = src.get("full_content") or src.get("text", "")
            src["numeric_highlights"] = extract_source_numeric_highlights(src_text, answer_numbers)

        yield _sse("done", {
            "persona": {
                "name": persona.get("name"),
                "slug": persona.get("slug"),
            },
            "answer": full_answer,
            "sources": result.sources,
            "stats": {"source_count": len(result.sources)},
            "highlight_keywords": done_q_keywords,
            "numeric_highlights": extract_numeric_highlights(
                full_answer, done_source_texts,
            ),
            "answer_highlight_keywords": done_answer_keywords,
            "telemetry": {
                "llm_calls": 1,
                "input_tokens": input_token_estimate,
                "output_tokens": output_token_count,
            },
        })

    except Exception as e:
        logger.exception("Consulting stream error: {}", e)
        yield _sse("error", {"message": str(e)})


# _build_system_prompt is imported from engine_v2.consulting.prompts
