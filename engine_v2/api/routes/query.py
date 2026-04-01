"""Query route — POST /engine/query."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from engine_v2.api.deps import get_engine
from engine_v2.query_engine.citation import query as run_query

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


@router.post("/query")
async def query(req: QueryRequest, engine=Depends(get_engine)):
    """Execute a RAG query with citation support.

    Flow:
        query_engine/ (RetrieverQueryEngine)
        ├── retrievers/ (BM25 + Vector → RRF)
        ├── response_synthesizers/ (citation prompts)
        └── llms/ (Ollama or Azure OpenAI)
    """
    result = run_query(req.question, engine=engine)
    return {
        "answer": result.answer,
        "sources": result.sources,
        "warnings": result.warnings,
        "stats": result.stats,
    }
