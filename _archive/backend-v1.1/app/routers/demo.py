"""Demo router that returns a fixed FastAPI dependency-injection walkthrough."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.query import (
    GenerationTrace,
    QueryFilters,
    QueryResponse,
    QueryTrace,
    RetrievalStats,
    RetrievalTrace,
    SourceInfo,
    TraceChunkHit,
)

router = APIRouter(prefix="/api/v1", tags=["demo"])

_DEMO_BOOK_TITLE = "FastAPI: Modern Python Web Development"
_DEMO_QUESTION = "How does FastAPI's dependency injection work and why is it useful?"

_DEMO_ANSWER = (
    "**The book presents dependency injection as one of FastAPI's key design features, "
    "and says it is useful at many levels** [1].\n\n"
    "For a web service, the dependency-related work often includes gathering request "
    "parameters, validating input, checking authentication and authorization, looking up "
    "data, and emitting metrics or logs [2].\n\n"
    "The problem with doing that work inline is duplication: if a dependency is common, "
    "you can end up repeating the same lookup code in multiple functions [3].\n\n"
    "**FastAPI's mechanism is to define dependencies as function arguments, then call "
    "them automatically and pass in the returned values** [4].\n\n"
    "The same mechanism can be scoped to a single path function, a group of paths, or "
    "the whole application [5]."
)

_PAGE_DIM = {"width": 504.0, "height": 661.0}

_DEMO_SOURCES: list[dict] = [
    {
        "source_id": "lubanovic_fastapi_modern_web_000835",
        "book_id": 36,
        "book_title": _DEMO_BOOK_TITLE,
        "chapter_title": "Dependencies",
        "page_number": 95,
        "snippet": (
            "One of the very nice design features of FastAPI is a technique called "
            "dependency injection. This term sounds technical and esoteric, but it's a "
            "key aspect of FastAPI and is surprisingly useful at many levels."
        ),
        "bbox": {"x0": 140.0, "y0": 402.0, "x1": 859.0, "y1": 479.0},
        "page_dim": _PAGE_DIM,
        "confidence": 1.0,
    },
    {
        "source_id": "lubanovic_fastapi_modern_web_000839",
        "book_id": 36,
        "book_title": _DEMO_BOOK_TITLE,
        "chapter_title": "Dependencies",
        "page_number": 95,
        "snippet": (
            "Gather input parameters from the HTTP request. Validate inputs. Check user "
            "authentication and authorization for some endpoints. Look up data from a "
            "data source, often a database. Emit metrics, logs, or tracking information."
        ),
        "bbox": {"x0": 156.0, "y0": 615.0, "x1": 718.0, "y1": 736.0},
        "page_dim": _PAGE_DIM,
        "confidence": 1.0,
    },
    {
        "source_id": "lubanovic_fastapi_modern_web_000848",
        "book_id": 36,
        "book_title": _DEMO_BOOK_TITLE,
        "chapter_title": "Dependencies",
        "page_number": 96,
        "snippet": (
            "If your dependency is a common one, like looking up a user in a database "
            "or combining values from an HTTP request, you might duplicate the lookup "
            "code in multiple functions."
        ),
        "bbox": {"x0": 174.0, "y0": 340.0, "x1": 859.0, "y1": 394.0},
        "page_dim": _PAGE_DIM,
        "confidence": 1.0,
    },
    {
        "source_id": "lubanovic_fastapi_modern_web_000854",
        "book_id": 36,
        "book_title": _DEMO_BOOK_TITLE,
        "chapter_title": "Dependencies",
        "page_number": 96,
        "snippet": (
            "FastAPI goes one step more: you can define dependencies as arguments to "
            "your function, and they are automatically called by FastAPI and pass in "
            "the values that they return."
        ),
        "bbox": {"x0": 140.0, "y0": 635.0, "x1": 859.0, "y1": 748.0},
        "page_dim": _PAGE_DIM,
        "confidence": 1.0,
    },
    {
        "source_id": "lubanovic_fastapi_modern_web_000872",
        "book_id": 36,
        "book_title": _DEMO_BOOK_TITLE,
        "chapter_title": "Dependencies",
        "page_number": 98,
        "snippet": (
            "You can define dependencies to cover a single path function, a group of "
            "them, or the whole web application."
        ),
        "bbox": {"x0": 140.0, "y0": 287.0, "x1": 857.0, "y1": 325.0},
        "page_dim": _PAGE_DIM,
        "confidence": 1.0,
    },
]

_DEMO_TRACE = QueryTrace(
    question=_DEMO_QUESTION,
    top_k=5,
    filters=QueryFilters(book_ids=[36]),
    active_book_title=_DEMO_BOOK_TITLE,
    retrieval=RetrievalTrace(
        fetch_k=15,
        fts_query="fastapi dependency injection work useful",
        fts_results=[
            TraceChunkHit(
                strategy="fts",
                rank=1,
                chunk_id="lubanovic_fastapi_modern_web_000835",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=95,
                score=8.42,
                snippet=_DEMO_SOURCES[0]["snippet"],
            ),
            TraceChunkHit(
                strategy="fts",
                rank=2,
                chunk_id="lubanovic_fastapi_modern_web_000854",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=96,
                score=7.18,
                snippet=_DEMO_SOURCES[3]["snippet"],
            ),
            TraceChunkHit(
                strategy="fts",
                rank=3,
                chunk_id="lubanovic_fastapi_modern_web_000848",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=96,
                score=6.55,
                snippet=_DEMO_SOURCES[2]["snippet"],
            ),
            TraceChunkHit(
                strategy="fts",
                rank=4,
                chunk_id="lubanovic_fastapi_modern_web_000872",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=98,
                score=5.91,
                snippet=_DEMO_SOURCES[4]["snippet"],
            ),
            TraceChunkHit(
                strategy="fts",
                rank=5,
                chunk_id="lubanovic_fastapi_modern_web_000839",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=95,
                score=4.73,
                snippet=_DEMO_SOURCES[1]["snippet"],
            ),
        ],
        vector_results=[
            TraceChunkHit(
                strategy="vector",
                rank=1,
                chunk_id="lubanovic_fastapi_modern_web_000835",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=95,
                score=0.312,
                snippet=_DEMO_SOURCES[0]["snippet"],
            ),
            TraceChunkHit(
                strategy="vector",
                rank=2,
                chunk_id="lubanovic_fastapi_modern_web_000854",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=96,
                score=0.387,
                snippet=_DEMO_SOURCES[3]["snippet"],
            ),
            TraceChunkHit(
                strategy="vector",
                rank=3,
                chunk_id="lubanovic_fastapi_modern_web_000872",
                book_title=_DEMO_BOOK_TITLE,
                chapter_title="Dependencies",
                page_number=98,
                score=0.425,
                snippet=_DEMO_SOURCES[4]["snippet"],
            ),
        ],
        pageindex_results=[],
        metadata_results=[],
        fused_results=[
            TraceChunkHit(
                strategy="fused",
                rank=idx + 1,
                chunk_id=source["source_id"],
                book_title=source["book_title"],
                chapter_title=source["chapter_title"],
                page_number=source["page_number"],
                score=round(1.0 / (60 + idx + 1) + 1.0 / (60 + idx + 1), 4)
                if idx < 3
                else round(1.0 / (60 + idx + 1), 4),
                snippet=source["snippet"],
            )
            for idx, source in enumerate(_DEMO_SOURCES)
        ],
    ),
    generation=GenerationTrace(
        model="demo:fastapi-dependency-injection",
        system_prompt="Hardcoded demo response. No model call was made.",
        user_prompt="Hardcoded demo response. No model call was made.",
    ),
)


@router.get("/demo", response_model=QueryResponse)
def get_demo() -> QueryResponse:
    """Return a fixed response for screenshot and citation-jump demos."""
    return QueryResponse(
        answer=_DEMO_ANSWER,
        sources=[SourceInfo(**source) for source in _DEMO_SOURCES],
        retrieval_stats=RetrievalStats(
            fts_hits=5,
            vector_hits=3,
            pageindex_hits=0,
            metadata_hits=0,
            fused_count=5,
        ),
        trace=_DEMO_TRACE,
    )
