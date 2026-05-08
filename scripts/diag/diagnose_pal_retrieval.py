"""Diagnose PAL retrieval via the backend consulting API.

Tests two modes:
1. No book_id filter (current behavior — searches all 23k chunks)
2. With book_id pre-filter (narrows to PAL-related documents first)

The pre-filter simulates a book_id selection step: given the query,
match keywords against known book_id paths to find relevant documents.
"""
from __future__ import annotations

import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

ENGINE_URL = os.getenv("ENGINE_URL", "http://127.0.0.1:8001")
QUERY = "What is a Provincial Attestation Letter (PAL)?"
PERSONA_SLUG = "live-study-immigration"


# ── Step 1: Fetch all book_ids from ca_federal via ChromaDB ──
def get_all_book_ids(collection_name: str = "ca_federal") -> list[str]:
    """Get unique book_ids from ChromaDB collection."""
    import chromadb
    from engine_v2.settings import CHROMA_PERSIST_DIR

    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    coll = client.get_collection(collection_name)

    # Fetch all metadatas to extract unique book_ids
    # Use batched approach to handle large collections
    all_book_ids = set()
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

    return sorted(all_book_ids)


# ── Step 2: Pre-filter book_ids by query keywords ──
def prefilter_book_ids(query: str, all_book_ids: list[str], max_books: int = 10) -> list[str]:
    """Match query keywords against book_id paths to find relevant documents.

    Simple keyword-in-path matching. Each book_id path is like:
        en/immigration-refugees-citizenship/services/study-canada/
        study-permit/get-documents/provincial-attestation-letter/...

    Scores each book_id by how many query keywords appear in the path.
    """
    # Extract meaningful keywords from query (lowercase, skip stopwords)
    stopwords = {
        "what", "is", "a", "an", "the", "how", "do", "i", "can", "to",
        "for", "in", "of", "and", "or", "my", "it", "if", "on", "at",
        "get", "need", "about",
    }
    raw_words = query.lower().replace("(", " ").replace(")", " ").replace("?", " ").split()
    keywords = [w for w in raw_words if w not in stopwords and len(w) > 2]

    # Score each book_id
    scored = []
    for bid in all_book_ids:
        bid_lower = bid.lower().replace("-", " ").replace("/", " ").replace("_", " ")
        score = sum(1 for kw in keywords if kw in bid_lower)
        if score > 0:
            scored.append((score, bid))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [bid for _, bid in scored[:max_books]]
    return selected


# ── Step 3: Query the API ──
def query_api(book_id_strings: list[str] | None = None) -> dict:
    """Query the consulting API with optional book_id filter."""
    url = f"{ENGINE_URL}/engine/consulting/query"
    payload = {
        "persona_slug": PERSONA_SLUG,
        "question": QUERY,
        "top_k": 5,
    }
    if book_id_strings:
        payload["book_id_strings"] = book_id_strings

    resp = requests.post(url, json=payload, timeout=120)
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "answer": "", "sources": []}
    return resp.json()


# ── Step 4: Print results ──
def print_results(label: str, data: dict, elapsed: float):
    answer = data.get("answer", "")
    sources = data.get("sources", [])

    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")
    print(f"  Latency: {elapsed:.1f}s")
    print(f"  Sources: {len(sources)}")
    print()

    # Answer preview
    print(f"  Answer ({len(answer)} chars):")
    for line in answer[:500].split("\n"):
        print(f"    {line}")
    if len(answer) > 500:
        print(f"    ... ({len(answer)} chars total)")
    print()

    # Sources
    pal_found = False
    for i, s in enumerate(sources):
        book_id = s.get("book_id", "?")
        source_type = s.get("retrieval_source", "?")
        vec_score = s.get("vector_score", 0)
        bm25_score = s.get("bm25_score", 0)
        text = s.get("full_content") or s.get("text", "")
        has_pal = "attestation letter" in text.lower() or "PAL/TAL" in text
        marker = " << PAL" if has_pal else ""
        if has_pal:
            pal_found = True

        print(f"  [{i+1}] {source_type:6s}  V:{vec_score:.4f}  K:{bm25_score:.4f}{marker}")
        # Show last 2 segments of book_id for readability
        short_bid = "/".join(book_id.split("/")[-3:]) if "/" in book_id else book_id
        print(f"      .../{short_bid}")
        print(f"      {text[:120].replace(chr(10), ' ')}")
        print()

    if pal_found:
        print(f"  >> PAL content found in sources!")
    else:
        print(f"  >> NO PAL content in sources!")

    return pal_found


def main():
    print("=" * 80)
    print("  PAL RETRIEVAL DIAGNOSTIC")
    print(f"  Query: {QUERY}")
    print(f"  Engine: {ENGINE_URL}")
    print("=" * 80)

    # ── Test 1: Without book_id filter ──
    print("\n[1/3] Querying WITHOUT book_id filter...")
    t0 = time.perf_counter()
    data_no_filter = query_api()
    elapsed1 = time.perf_counter() - t0
    found1 = print_results("TEST 1: No Filter (all 23k chunks)", data_no_filter, elapsed1)

    # ── Pre-filter: find relevant book_ids ──
    print("\n[2/3] Pre-filtering book_ids by query keywords...")
    all_book_ids = get_all_book_ids()
    print(f"  Total unique book_ids in ca_federal: {len(all_book_ids)}")

    selected = prefilter_book_ids(QUERY, all_book_ids)
    print(f"  Selected {len(selected)} book_ids matching query keywords:")
    for bid in selected:
        short = "/".join(bid.split("/")[-3:]) if "/" in bid else bid
        print(f"    .../{short}")

    # ── Test 2: With book_id filter ──
    print(f"\n[3/3] Querying WITH book_id filter ({len(selected)} books)...")
    t0 = time.perf_counter()
    data_filtered = query_api(book_id_strings=selected)
    elapsed2 = time.perf_counter() - t0
    found2 = print_results(f"TEST 2: Pre-filtered ({len(selected)} books)", data_filtered, elapsed2)

    # ── Summary ──
    print("\n" + "=" * 80)
    print("  COMPARISON")
    print("=" * 80)
    print(f"  {'Metric':<25} {'No Filter':>15} {'Pre-filtered':>15}")
    print(f"  {'-'*25} {'-'*15} {'-'*15}")
    print(f"  {'PAL found?':<25} {'YES' if found1 else 'NO':>15} {'YES' if found2 else 'NO':>15}")
    print(f"  {'Sources':<25} {len(data_no_filter.get('sources',[])):>15} {len(data_filtered.get('sources',[])):>15}")
    print(f"  {'Latency':<25} {elapsed1:>14.1f}s {elapsed2:>14.1f}s")
    print(f"  {'Answer length':<25} {len(data_no_filter.get('answer','')):>15} {len(data_filtered.get('answer','')):>15}")
    print("=" * 80)


if __name__ == "__main__":
    main()
