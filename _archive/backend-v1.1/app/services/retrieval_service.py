"""Retrieval service — hybrid search: FTS5 keyword + ChromaDB vector → RRF fusion."""

from __future__ import annotations

import sqlite3

from backend.app.repositories import chunk_repo, vector_repo


def retrieve(
    db: sqlite3.Connection,
    question: str,
    filters: dict | None = None,
    top_k: int = 5,
) -> tuple[list[dict], dict, dict]:
    """Run hybrid retrieval and return ``(ranked_chunks, stats)``.

    Each chunk dict is enriched with ``source_locators`` and book/chapter
    metadata.  ``stats`` has keys ``fts_hits``, ``vector_hits``,
    ``fused_count``.
    """
    fetch_k = top_k * 3  # over-fetch for better fusion

    # --- FTS5 keyword search ---
    fts_query = chunk_repo._sanitise_fts(question)
    fts_results = chunk_repo.search_fts(db, question, filters=filters, limit=fetch_k)
    for rank, chunk in enumerate(fts_results, start=1):
        chunk["_fts_rank"] = rank

    # --- ChromaDB vector search ---
    vec_results = vector_repo.search(question, top_k=fetch_k, filters=filters)

    # Map chroma_ids back to chunk rows
    chroma_ids = [v["chroma_id"] for v in vec_results]
    vec_chunks = chunk_repo.get_chunks_by_chroma_ids(db, chroma_ids)
    chroma_to_chunk = {c["chroma_document_id"]: c for c in vec_chunks}
    vector_ranked_chunks: list[dict] = []
    # Attach distance scores
    for rank, v in enumerate(vec_results, start=1):
        c = chroma_to_chunk.get(v["chroma_id"])
        if c:
            c["_vec_distance"] = v["distance"]
            c["_vec_rank"] = rank
            vector_ranked_chunks.append(c)

    # --- Reciprocal Rank Fusion ---
    fused = _rrf_fuse(fts_results, vector_ranked_chunks, k=60)
    top = fused[:top_k]

    # Enrich with source locators + metadata
    trace_chunks = _collect_unique_chunks(fts_results, vector_ranked_chunks, top)
    chunk_ids = [c["id"] for c in trace_chunks]
    locators = chunk_repo.get_source_locators(db, chunk_ids)
    loc_map: dict[int, list[dict]] = {}
    for loc in locators:
        loc_map.setdefault(loc["chunk_id"], []).append(loc)

    # Attach book/chapter names
    _enrich_metadata(db, trace_chunks)

    for c in trace_chunks:
        c["source_locators"] = loc_map.get(c["id"], [])

    stats = {
        "fts_hits": len(fts_results),
        "vector_hits": len(vec_results),
        "fused_count": len(top),
    }
    trace = {
        "fetch_k": fetch_k,
        "fts_query": fts_query,
        "fts_results": [_to_trace_hit(chunk, "fts") for chunk in fts_results[:top_k]],
        "vector_results": [
            _to_trace_hit(chunk, "vector") for chunk in vector_ranked_chunks[:top_k]
        ],
        "fused_results": [_to_trace_hit(chunk, "fused") for chunk in top],
    }
    return top, stats, trace


def _rrf_fuse(
    fts_results: list[dict],
    vec_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion over two ranked lists.

    Score = sum( 1/(k + rank_i) ) for each list the document appears in.
    """
    scores: dict[int, float] = {}
    doc_map: dict[int, dict] = {}

    for rank, doc in enumerate(fts_results):
        cid = doc["id"]
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        doc_map[cid] = doc

    for rank, doc in enumerate(vec_results):
        cid = doc["id"]
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        if cid not in doc_map:
            doc_map[cid] = doc

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    ranked_docs = [doc_map[cid] for cid in ranked_ids]
    for rank, doc in enumerate(ranked_docs, start=1):
        doc["_rrf_score"] = scores[doc["id"]]
        doc["_fused_rank"] = rank
    return ranked_docs


def _enrich_metadata(db: sqlite3.Connection, chunks: list[dict]) -> None:
    """Attach ``book_title`` and ``chapter_title`` to each chunk dict."""
    book_ids = {c["book_id"] for c in chunks}
    chapter_ids = {c["chapter_id"] for c in chunks if c.get("chapter_id")}
    page_ids = {c["primary_page_id"] for c in chunks if c.get("primary_page_id")}

    book_map: dict[int, str] = {}
    if book_ids:
        ph = ",".join("?" for _ in book_ids)
        rows = db.execute(
            f"SELECT id, title FROM books WHERE id IN ({ph})", list(book_ids)
        ).fetchall()
        book_map = {r["id"]: r["title"] for r in rows}

    chapter_map: dict[int, str] = {}
    if chapter_ids:
        ph = ",".join("?" for _ in chapter_ids)
        rows = db.execute(
            f"SELECT id, title FROM chapters WHERE id IN ({ph})", list(chapter_ids)
        ).fetchall()
        chapter_map = {r["id"]: r["title"] for r in rows}

    page_map: dict[int, int] = {}
    if page_ids:
        ph = ",".join("?" for _ in page_ids)
        rows = db.execute(
            f"SELECT id, page_number FROM pages WHERE id IN ({ph})", list(page_ids)
        ).fetchall()
        page_map = {r["id"]: r["page_number"] for r in rows}

    for c in chunks:
        c["book_title"] = book_map.get(c["book_id"], "")
        c["chapter_title"] = chapter_map.get(c.get("chapter_id"), "")  # type: ignore[arg-type]
        primary_page_id = c.get("primary_page_id")
        c["primary_page_number"] = (
            page_map.get(primary_page_id, -1) + 1 if primary_page_id in page_map else None
        )


def _collect_unique_chunks(*groups: list[dict]) -> list[dict]:
    seen: dict[int, dict] = {}
    for group in groups:
        for chunk in group:
            seen.setdefault(chunk["id"], chunk)
    return list(seen.values())


def _to_trace_hit(chunk: dict, strategy: str) -> dict:
    if strategy == "fts":
        rank = chunk.get("_fts_rank")
        raw = chunk.get("rank")
        score = -raw if raw is not None else None
    elif strategy == "vector":
        rank = chunk.get("_vec_rank")
        score = chunk.get("_vec_distance")
    else:
        rank = chunk.get("_fused_rank")
        score = chunk.get("_rrf_score")

    return {
        "strategy": strategy,
        "rank": int(rank or 0),
        "chunk_id": chunk.get("chunk_id", ""),
        "book_title": chunk.get("book_title", ""),
        "chapter_title": chunk.get("chapter_title") or None,
        "page_number": chunk.get("primary_page_number"),
        "score": float(score) if score is not None else None,
        "snippet": (chunk.get("text") or "")[:220],
    }
