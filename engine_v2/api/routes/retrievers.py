"""Retrievers route — POST /engine/retrievers/search (retrieve-only, no generation)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from engine_v2.retrievers.hybrid import get_hybrid_retriever

router = APIRouter(prefix="/retrievers", tags=["retrievers"])


class RetrieveRequest(BaseModel):
    question: str
    top_k: int = 5


@router.post("/search")
async def search(req: RetrieveRequest):
    """Retrieve chunks without generation — useful for debugging retrieval quality.

    Returns raw NodeWithScore results from the hybrid retriever
    (BM25 + Vector → RRF fusion).
    """
    retriever = get_hybrid_retriever(similarity_top_k=req.top_k)
    nodes = retriever.retrieve(req.question)

    return {
        "query": req.question,
        "results": [
            {
                "chunk_id": n.node.id_,
                "score": n.score,
                "book_id": n.node.metadata.get("book_id", ""),
                "page_idx": n.node.metadata.get("page_idx", 0),
                "content_type": n.node.metadata.get("content_type", "text"),
                "chapter_key": n.node.metadata.get("chapter_key"),
                "text": n.node.get_content()[:500],
            }
            for n in nodes
        ],
        "count": len(nodes),
    }
