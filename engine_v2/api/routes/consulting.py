"""consulting routes — Persona knowledge base ingest + query + user private docs.

Endpoints (C2 — Persona Knowledge Base):
    POST   /engine/consulting/ingest        — ingest PDF into persona collection
    POST   /engine/consulting/query         — RAG query against persona collection
    POST   /engine/consulting/query/stream  — SSE streaming query against persona
    GET    /engine/consulting/personas      — list available personas (from Payload)
    GET    /engine/consulting/status/{slug}  — collection stats for a persona

Endpoints (C3 — User Private Documents):
    POST   /engine/consulting/user-doc/ingest   — ingest user PDF into private collection
    GET    /engine/consulting/user-doc/list      — list user's private documents
    DELETE /engine/consulting/user-doc/{doc_id}  — delete user doc + ChromaDB cleanup

C4 — Dual-Collection Retrieval:
    When user_id is provided in query requests, retrieves from BOTH the
    persona collection AND the user's private collection, merging results
    via Reciprocal Rank Fusion.

Reuses the existing MinerU → MinerUReader → IngestionPipeline chain.
Each persona writes to its own ChromaDB collection (persona_{slug}).
User private docs go to user_{userId}_{personaSlug} collections.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import chromadb
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from engine_v2.personas.registry import (
    fetch_persona as _fetch_persona,
    get_collection_count as _get_collection_count,
    get_collection_name as _get_persona_collection,
)
from engine_v2.user_docs.manager import (
    update_user_doc as _update_user_doc,
    user_collection_name as _user_collection_name,
)
from engine_v2.settings import (
    CHROMA_PERSIST_DIR,
    DATA_DIR,
    MINERU_OUTPUT_DIR,
    PAYLOAD_API_KEY,
    PAYLOAD_URL,
    TOP_K,
)

router = APIRouter(prefix="/consulting", tags=["consulting"])


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
    user_id: int | None = None  # C4: enables dual-collection retrieval


# ============================================================
# Helpers — persona data from engine_v2.personas.registry
# ============================================================
# _fetch_persona, _get_persona_collection, _get_collection_count
# are imported from engine_v2.personas.registry at the top of this file.


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
# C4 — Dual-Collection Retrieval (persona KB + user private)
# ============================================================


def _dual_collection_query(
    question: str,
    persona_collection: str,
    user_collection: str,
    system_prompt: str,
    top_k: int = TOP_K,
    model: str | None = None,
    provider: str | None = None,
    streaming: bool = False,
) -> tuple[list[dict], Any]:
    """Retrieve from both persona and user-private collections, merge via RRF.

    Strategy:
        1. Build two VectorIndexRetrievers (persona + user-private).
        2. Retrieve top_k from each.
        3. Merge via simple Reciprocal Rank Fusion (k=60).
        4. Tag each source with its origin (persona_kb / user_private).
        5. Synthesize response using persona system prompt.

    Returns:
        Tuple of (sources_list, response_object)
    """
    from llama_index.core import VectorStoreIndex
    from llama_index.core.schema import NodeWithScore
    from llama_index.vector_stores.chroma import ChromaVectorStore

    from engine_v2.response_synthesizers.citation import get_citation_synthesizer
    from engine_v2.schema import build_source, normalize_scores

    # ── Build retrievers for both collections ──
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    def _retrieve_from(col_name: str, origin_tag: str) -> list[NodeWithScore]:
        """Retrieve nodes from a single collection and tag origin."""
        try:
            col = client.get_or_create_collection(
                name=col_name,
                metadata={"hnsw:space": "cosine"},
            )
            if col.count() == 0:
                logger.debug("Collection {} is empty, skipping", col_name)
                return []

            vs = ChromaVectorStore(chroma_collection=col)
            index = VectorStoreIndex.from_vector_store(vs)
            retriever = index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(question)

            # Tag each node with its origin
            for nws in nodes:
                nws.node.metadata["retrieval_origin"] = origin_tag

            logger.debug(
                "Retrieved {} nodes from {} ({})", len(nodes), col_name, origin_tag,
            )
            return nodes
        except Exception as e:
            logger.warning("Retrieval from {} failed: {}", col_name, e)
            return []

    # ── Parallel retrieval (synchronous for simplicity) ──
    persona_nodes = _retrieve_from(persona_collection, "persona_kb")
    user_nodes = _retrieve_from(user_collection, "user_private")

    # ── RRF Merge (k=60, industry standard) ──
    RRF_K = 60
    scored: dict[str, tuple[float, NodeWithScore]] = {}

    for rank, nws in enumerate(persona_nodes, start=1):
        nid = nws.node.id_
        rrf_score = 1.0 / (RRF_K + rank)
        scored[nid] = (rrf_score, nws)

    for rank, nws in enumerate(user_nodes, start=1):
        nid = nws.node.id_
        rrf_score = 1.0 / (RRF_K + rank)
        if nid in scored:
            existing_score, existing_nws = scored[nid]
            scored[nid] = (existing_score + rrf_score, existing_nws)
        else:
            scored[nid] = (rrf_score, nws)

    # Sort by RRF score descending, take top_k
    merged = sorted(scored.values(), key=lambda x: x[0], reverse=True)[:top_k]

    # Update scores to RRF scores
    merged_nodes: list[NodeWithScore] = []
    for rrf_score, nws in merged:
        nws.score = rrf_score
        merged_nodes.append(nws)

    logger.info(
        "Dual-collection RRF: {} persona + {} user → {} merged",
        len(persona_nodes), len(user_nodes), len(merged_nodes),
    )

    # ── Build citation nodes and synthesize ──
    from engine_v2.query_engine.citation import TextbookCitationQueryEngine

    synthesizer = get_citation_synthesizer(
        streaming=streaming, model=model, provider=provider,
        custom_system_prompt=system_prompt,
    )

    # Use citation engine for dedup + Source N labeling
    engine = TextbookCitationQueryEngine(
        retriever=None,  # type: ignore — we won't use retrieve()
        response_synthesizer=synthesizer,
    )
    citation_nodes = engine._create_citation_nodes(merged_nodes)

    # Build sources list
    sources = []
    for i, nws in enumerate(citation_nodes, start=1):
        src = build_source(nws, i)
        src["retrieval_origin"] = nws.node.metadata.get("retrieval_origin", "unknown")
        sources.append(src)
    normalize_scores(sources)

    # Synthesize response
    from llama_index.core.schema import QueryBundle

    response = synthesizer.synthesize(
        query=QueryBundle(query_str=question),
        nodes=citation_nodes,
    )

    return sources, response


@router.post("/query")
async def consulting_query(req: PersonaQueryRequest):
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
    system_prompt = persona.get("systemPrompt", "")

    from engine_v2.query_engine.citation import get_query_engine
    from engine_v2.schema import build_source, normalize_scores

    # C4: Dual-collection retrieval
    if req.user_id:
        sources, response = _dual_collection_query(
            question=req.question,
            persona_collection=collection_name,
            user_collection=_user_collection_name(req.user_id, req.persona_slug),
            system_prompt=system_prompt,
            top_k=req.top_k,
            model=req.model,
            provider=req.provider,
            streaming=False,
        )
    else:
        engine = get_query_engine(
            similarity_top_k=req.top_k,
            streaming=False,
            collection_name=collection_name,
            custom_system_prompt=system_prompt,
            model=req.model,
            provider=req.provider,
        )
        response = engine.query(req.question)
        sources = []
        for i, nws in enumerate(response.source_nodes, start=1):
            sources.append(build_source(nws, i))
        normalize_scores(sources)

    return {
        "persona": {
            "name": persona.get("name"),
            "slug": persona.get("slug"),
        },
        "answer": str(response),
        "sources": sources,
        "stats": {"source_count": len(sources)},
    }


# ============================================================
# POST /engine/consulting/query/stream — SSE streaming query
# ============================================================


@router.post("/query/stream")
async def consulting_query_stream(req: PersonaQueryRequest):
    """SSE streaming RAG query against a persona's knowledge base."""
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
        system_prompt = persona.get("systemPrompt", "")

        from engine_v2.query_engine.citation import get_query_engine
        from engine_v2.schema import build_source, normalize_scores

        # C4: Dual-collection streaming
        if req.user_id:
            sources, response = _dual_collection_query(
                question=req.question,
                persona_collection=collection_name,
                user_collection=_user_collection_name(
                    req.user_id, req.persona_slug,
                ),
                system_prompt=system_prompt,
                top_k=req.top_k,
                model=req.model,
                provider=req.provider,
                streaming=True,
            )
        else:
            engine = get_query_engine(
                similarity_top_k=req.top_k,
                streaming=True,
                collection_name=collection_name,
                custom_system_prompt=system_prompt,
                model=req.model,
                provider=req.provider,
            )
            response = engine.query(req.question)
            sources = []
            for i, nws in enumerate(response.source_nodes, start=1):
                sources.append(build_source(nws, i))
            normalize_scores(sources)

        yield _sse("retrieval_done", {
            "stats": {"source_count": len(sources)},
            "sources": sources,
        })

        # Stream tokens
        full_answer = ""
        response_gen = response.response_gen
        if response_gen is not None:
            for token in response_gen:
                full_answer += token
                yield _sse("token", {"t": token})
        else:
            full_answer = str(response)

        yield _sse("done", {
            "persona": {
                "name": persona.get("name"),
                "slug": persona.get("slug"),
            },
            "answer": full_answer,
            "sources": sources,
            "stats": {"source_count": len(sources)},
        })

    except Exception as e:
        logger.exception("Consulting stream error: {}", e)
        yield _sse("error", {"message": str(e)})


def _sse(event: str, data: dict[str, Any]) -> str:
    """Format SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============================================================
# GET /engine/consulting/personas — list personas
# ============================================================


@router.get("/personas")
async def list_personas():
    """List all enabled consulting personas with collection stats."""
    import httpx

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"

    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/consulting-personas",
            params={
                "where[isEnabled][equals]": "true",
                "sort": "sortOrder",
                "limit": "20",
            },
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        personas = resp.json().get("docs", [])
    except Exception as e:
        logger.warning("Failed to fetch personas: {}", e)
        return {"personas": [], "error": str(e)}

    # Enrich with collection stats
    result = []
    for p in personas:
        collection_name = p.get("chromaCollection", f"persona_{p['slug']}")
        chunk_count = _get_collection_count(collection_name)
        result.append({
            "name": p.get("name"),
            "slug": p.get("slug"),
            "icon": p.get("icon"),
            "description": p.get("description"),
            "chromaCollection": collection_name,
            "chunkCount": chunk_count,
        })

    return {"personas": result}


# ============================================================
# GET /engine/consulting/status/{slug} — collection stats
# ============================================================


@router.get("/status/{slug}")
async def persona_status(slug: str):
    """Return ChromaDB collection stats for a persona."""
    collection_name = _get_persona_collection(slug)
    count = _get_collection_count(collection_name)

    return {
        "slug": slug,
        "collection_name": collection_name,
        "chunk_count": count,
        "has_data": count > 0,
    }


# _get_collection_count is imported from engine_v2.personas.registry


# ============================================================
# C3 — User Private Document Endpoints
# ============================================================


# _user_collection_name is imported from engine_v2.user_docs.manager


class UserDocIngestRequest(BaseModel):
    """Ingest a user-uploaded PDF into their private collection."""

    user_id: int
    persona_slug: str
    doc_id: int  # Payload UserDocuments record ID
    pdf_filename: str  # filename in data/raw_pdfs/user_private/
    force_parse: bool = False


@router.post("/user-doc/ingest")
async def user_doc_ingest(req: UserDocIngestRequest):
    """Ingest a user-uploaded PDF into their private ChromaDB collection.

    Flow:
        1. MinerU parse (if not cached)
        2. MinerUReader → IngestionPipeline → user_{userId}_{personaSlug}
        3. Update UserDocuments record: status=indexed, chunkCount=N

    PDF is expected at: data/raw_pdfs/user_private/{pdf_filename}
    (Payload PdfUploads/UserDocuments stores files there via staticDir)
    """
    from engine_v2.api.routes.ingest import _run_mineru_parse
    from engine_v2.ingestion.pipeline import ingest_book

    collection_name = _user_collection_name(req.user_id, req.persona_slug)

    # Derive book_dir_name from filename
    stem = Path(req.pdf_filename).stem
    book_dir_name = stem.lower().replace(" ", "_").replace("-", "_")
    category = "user_private"

    # Locate PDF — Payload stores uploads in data/raw_pdfs/user_private/
    pdf_base = DATA_DIR / "raw_pdfs" / "user_private"
    pdf_path = pdf_base / req.pdf_filename
    if not pdf_path.exists():
        # Payload may store with subdirectory structure
        for candidate in pdf_base.rglob(req.pdf_filename):
            pdf_path = candidate
            break
    if not pdf_path.exists():
        _update_user_doc(req.doc_id, status="error",
                         error=f"PDF not found: {req.pdf_filename}")
        return {
            "status": "error",
            "message": f"PDF not found at {pdf_base / req.pdf_filename}",
        }

    # MinerU output path
    auto_dir = (
        MINERU_OUTPUT_DIR / category / book_dir_name / book_dir_name / "auto"
    )
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"

    def _run():
        try:
            # Mark as processing
            _update_user_doc(req.doc_id, status="processing",
                             chroma_collection=collection_name)

            # Step 1: MinerU parse
            if req.force_parse or not content_list_path.exists():
                logger.info(
                    "Parsing user PDF: user={}, persona={}, file={}",
                    req.user_id, req.persona_slug, pdf_path,
                )
                _run_mineru_parse(pdf_path, book_dir_name, category)
            else:
                logger.info(
                    "MinerU output exists for user doc {}, skipping parse",
                    book_dir_name,
                )

            # Step 2: Ingest into user-private collection
            result = ingest_book(
                book_id=0,  # no Payload book record
                book_dir_name=book_dir_name,
                category=category,
                collection_name=collection_name,
            )

            chunk_count = result.get("chunk_count", 0)
            _update_user_doc(
                req.doc_id,
                status="indexed",
                chunk_count=chunk_count,
                chroma_collection=collection_name,
            )
            logger.info(
                "User doc ingest complete: user={}, persona={}, chunks={}",
                req.user_id, req.persona_slug, chunk_count,
            )

        except Exception as e:
            logger.exception(
                "User doc ingest failed: user={}, doc={}, error={}",
                req.user_id, req.doc_id, e,
            )
            _update_user_doc(req.doc_id, status="error", error=str(e))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "status": "accepted",
        "doc_id": req.doc_id,
        "collection_name": collection_name,
        "book_dir_name": book_dir_name,
    }


@router.get("/user-doc/list")
async def user_doc_list(user_id: int, persona_slug: str | None = None):
    """List a user's private documents with collection stats.

    Args:
        user_id: Payload user ID.
        persona_slug: Optional filter by persona.
    """
    import httpx

    headers = _payload_headers()
    params: dict[str, str] = {
        "where[user][equals]": str(user_id),
        "sort": "-createdAt",
        "limit": "50",
    }
    if persona_slug:
        # Filter by persona relationship — need to resolve persona ID first
        persona = _fetch_persona(persona_slug)
        if persona:
            params["where[persona][equals]"] = str(persona.get("id", ""))

    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/user-documents",
            params=params,
            headers=headers,
            timeout=10.0,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except Exception as e:
        logger.warning("Failed to fetch user docs: {}", e)
        return {"docs": [], "error": str(e)}

    # Enrich with live ChromaDB stats
    result = []
    for doc in docs:
        collection = doc.get("chromaCollection", "")
        live_count = _get_collection_count(collection) if collection else 0
        result.append({
            "id": doc.get("id"),
            "filename": doc.get("filename"),
            "status": doc.get("status"),
            "chunkCount": doc.get("chunkCount", 0),
            "liveChunkCount": live_count,
            "chromaCollection": collection,
            "persona": doc.get("persona"),
            "createdAt": doc.get("createdAt"),
            "description": doc.get("description"),
        })

    return {"docs": result}


@router.delete("/user-doc/{doc_id}")
async def user_doc_delete(doc_id: int, delete_vectors: bool = True):
    """Delete a user document and optionally clean up its ChromaDB data.

    Args:
        doc_id: Payload UserDocuments record ID.
        delete_vectors: If True, also delete the ChromaDB collection.
    """
    import httpx

    headers = _payload_headers()

    # Fetch the doc to get collection name before deleting
    collection_name = ""
    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/user-documents/{doc_id}",
            headers=headers,
            timeout=10.0,
        )
        if resp.is_success:
            doc_data = resp.json()
            collection_name = doc_data.get("chromaCollection", "")
    except Exception:
        pass

    # Delete from Payload
    deleted = False
    try:
        resp = httpx.delete(
            f"{PAYLOAD_URL}/api/user-documents/{doc_id}",
            headers=headers,
            timeout=10.0,
        )
        deleted = resp.is_success
    except Exception as e:
        logger.warning("Failed to delete user doc {}: {}", doc_id, e)

    # Clean up ChromaDB collection
    vectors_deleted = False
    if delete_vectors and collection_name:
        try:
            client = chromadb.PersistentClient(
                path=str(CHROMA_PERSIST_DIR),
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            client.delete_collection(collection_name)
            vectors_deleted = True
            logger.info(
                "Deleted ChromaDB collection: {}", collection_name,
            )
        except Exception as e:
            logger.warning(
                "Failed to delete ChromaDB collection {}: {}",
                collection_name, e,
            )

    return {
        "doc_id": doc_id,
        "deleted": deleted,
        "vectors_deleted": vectors_deleted,
        "collection_name": collection_name,
    }


# _payload_headers + _update_user_doc are imported from engine_v2.user_docs.manager


def _payload_headers() -> dict[str, str]:
    """Get auth headers for Payload CMS."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
    return headers

