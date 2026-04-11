"""Retrievers route — POST /engine/retrievers/search (retrieve-only, no generation).

Endpoints:
    POST   /engine/retrievers/search   — retrieve chunks without generation
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from engine_v2.retrievers.hybrid import get_hybrid_retriever
from engine_v2.query_engine.citation import BookFilterPostprocessor
from llama_index.core.schema import QueryBundle

router = APIRouter(prefix="/retrievers", tags=["retrievers"])


class RetrieveRequest(BaseModel):
    question: str
    top_k: int = 5
    book_id_strings: list[str] = Field(default_factory=list)
    reranker: str | None = None  # truthy = enable LLMRerank


@router.post("/search")
async def search(req: RetrieveRequest):
    """Retrieve chunks without generation — useful for debugging retrieval quality.

    Returns raw NodeWithScore results from the hybrid retriever
    (BM25 + Vector → RRF fusion), optionally filtered by book scope
    and re-ranked by LLMRerank.
    """
    retriever = get_hybrid_retriever(
        similarity_top_k=req.top_k,
        book_id_strings=req.book_id_strings or None,
    )
    nodes = retriever.retrieve(req.question)
    query_bundle = QueryBundle(query_str=req.question)

    # Post-filter by book scope (BM25 doesn't support native filtering)
    if req.book_id_strings:
        pp = BookFilterPostprocessor(book_id_strings=req.book_id_strings)
        nodes = pp.postprocess_nodes(nodes, query_bundle=query_bundle)

    # Optional LLMRerank
    if req.reranker:
        try:
            from llama_index.core.postprocessor import LLMRerank
            reranker_top_n = min(req.top_k, 5)
            reranker = LLMRerank(top_n=reranker_top_n)
            nodes = reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
            logger.info("Retriever search: LLMRerank applied (top_n={})", reranker_top_n)
        except ImportError:
            logger.warning("LLMRerank unavailable — skipping reranker")

    return {
        "query": req.question,
        "results": [
            {
                "chunk_id": n.node.id_,
                "score": n.score,
                "book_id": n.node.metadata.get("book_id", ""),
                "book_title": n.node.metadata.get("book_title", ""),
                "page_idx": n.node.metadata.get("page_idx", 0),
                "content_type": n.node.metadata.get("content_type", "text"),
                "chapter_key": n.node.metadata.get("chapter_key"),
                "text": n.node.get_content()[:500],
            }
            for n in nodes
        ],
        "count": len(nodes),
        "reranked": bool(req.reranker),
    }
