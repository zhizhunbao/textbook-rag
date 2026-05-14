"""Test RAG retrieval for EE rounds data via the engine API."""
import requests
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://localhost:8001"
PERSONA = "live-study-immigration"

queries = [
    "express entry CRS cutoff score 2026 rounds",
    "express entry invitation rounds 2025 2026 CRS minimum score",
    "CEC Canadian Experience Class CRS cutoff 2026",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    print(f"{'='*60}")
    try:
        resp = requests.post(
            f"{API_URL}/engine/consulting/retrieve",
            json={"persona_slug": PERSONA, "question": q, "top_k": 5},
            timeout=30,
        )
        resp.raise_for_status()
        chunks = resp.json().get("chunks", [])
        print(f"  Results: {len(chunks)} chunks")
        for i, c in enumerate(chunks):
            book = c.get("book_id", "?")
            page = c.get("page_number", "?")
            score = c.get("score", 0)
            content = c.get("full_content", c.get("snippet", ""))[:200].replace('\n', ' ')
            has_table = "| #" in content or "CRS" in content
            print(f"  [{i}] score={score:.3f} book={book[-40:]} page={page}")
            print(f"       {'✅ TABLE' if has_table else '  '} {content[:150]}")
    except Exception as e:
        print(f"  ERROR: {e}")
