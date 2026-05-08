"""book_filter — Auto-select relevant book_ids by matching query keywords to paths.

Pre-retrieval step that narrows the search scope from thousands of chunks
to a handful of relevant documents. Called before BM25/Vector retrieval.

Architecture:
    Query → extract_keywords() → match against cached book_id paths
    → return top N book_ids → passed to get_hybrid_retriever(book_id_strings=...)

The book_id paths are descriptive URL-like slugs, e.g.:
    en/immigration-refugees-citizenship/services/study-canada/
    study-permit/get-documents/provincial-attestation-letter/...

Simple keyword-in-path matching is highly effective because these paths
were generated from government website URLs with descriptive slugs.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any

import chromadb
from loguru import logger

from engine_v2.settings import CHROMA_PERSIST_DIR


# ============================================================
# Book ID cache (per-collection, thread-safe)
# ============================================================
_book_id_cache: dict[str, tuple[list[str], float]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 3600  # 1 hour


def _get_all_book_ids(collection_name: str) -> list[str]:
    """Fetch all unique book_ids from a ChromaDB collection (cached).

    Uses batched get() to handle large collections. Results are cached
    for 1 hour to avoid repeated full scans.

    Args:
        collection_name: ChromaDB collection name.

    Returns:
        Sorted list of unique book_id strings.
    """
    # Check cache
    with _cache_lock:
        entry = _book_id_cache.get(collection_name)
        if entry is not None:
            book_ids, ts = entry
            if time.monotonic() - ts < _CACHE_TTL:
                return book_ids

    # Cache miss — scan collection
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    try:
        coll = client.get_collection(collection_name)
    except Exception:
        logger.warning("book_filter: collection '{}' not found", collection_name)
        return []

    all_book_ids: set[str] = set()
    offset = 0
    batch_size = 5000

    while True:
        results = coll.get(
            limit=batch_size, offset=offset,
            include=["metadatas"],
        )
        if not results["ids"]:
            break
        for meta in results["metadatas"]:
            bid = meta.get("book_id", "")
            if bid:
                all_book_ids.add(bid)
        offset += len(results["ids"])
        if len(results["ids"]) < batch_size:
            break

    book_ids = sorted(all_book_ids)

    # Update cache
    with _cache_lock:
        _book_id_cache[collection_name] = (book_ids, time.monotonic())

    logger.info(
        "book_filter: cached {} unique book_ids for '{}'",
        len(book_ids), collection_name,
    )
    return book_ids


# ============================================================
# Keyword extraction
# ============================================================
_STOPWORDS = frozenset({
    "what", "is", "a", "an", "the", "how", "do", "i", "can", "to",
    "for", "in", "of", "and", "or", "my", "it", "if", "on", "at",
    "get", "need", "about", "does", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "will", "would", "could",
    "should", "may", "might", "must", "shall", "with", "from",
    "this", "that", "these", "those", "there", "here", "where",
    "when", "who", "which", "than", "then", "but", "not", "no",
    "all", "each", "every", "any", "some", "many", "much", "more",
    "most", "other", "new", "old", "after", "before", "between",
})


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a query string.

    Strips punctuation, stopwords, and short tokens.
    Returns lowercase tokens suitable for path matching.

    Args:
        query: Raw user query.

    Returns:
        List of keyword strings.
    """
    # Normalize: lowercase, remove parentheses and punctuation
    text = query.lower()
    text = re.sub(r"[()?\[\]{},.:;!\"']", " ", text)
    tokens = text.split()

    keywords = [
        t for t in tokens
        if t not in _STOPWORDS and len(t) > 2
    ]
    return keywords


# ============================================================
# Main: pre-filter book_ids by query
# ============================================================
def prefilter_book_ids(
    query: str,
    collection_name: str,
    *,
    max_books: int = 15,
    min_score: int = 1,
) -> list[str] | None:
    """Match query keywords against book_id paths to find relevant documents.

    Each book_id is scored by how many query keywords appear in its path
    (after normalizing hyphens/slashes to spaces).

    Args:
        query: User query string.
        collection_name: ChromaDB collection to search.
        max_books: Maximum number of book_ids to return.
        min_score: Minimum keyword match count to include a book.

    Returns:
        List of matching book_id strings, or None if no matches found
        (caller should fall back to unfiltered search).
    """
    all_book_ids = _get_all_book_ids(collection_name)
    if not all_book_ids:
        return None

    keywords = _extract_keywords(query)
    if not keywords:
        return None

    # Score each book_id by keyword overlap
    scored: list[tuple[int, str]] = []
    for bid in all_book_ids:
        # Normalize path separators to spaces for matching
        bid_text = bid.lower().replace("-", " ").replace("/", " ").replace("_", " ")
        score = sum(1 for kw in keywords if kw in bid_text)
        if score >= min_score:
            scored.append((score, bid))

    if not scored:
        logger.debug(
            "book_filter: no book_ids matched keywords {} in '{}'",
            keywords, collection_name,
        )
        return None

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [bid for _, bid in scored[:max_books]]

    logger.info(
        "book_filter: query='{}' → {} keywords → {} / {} books matched (top score={})",
        query[:60], len(keywords), len(selected), len(all_book_ids),
        scored[0][0] if scored else 0,
    )

    return selected
