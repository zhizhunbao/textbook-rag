"""Multi-query test: verify auto pre-filter across different topics."""
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import time
import requests

ENGINE_URL = "http://127.0.0.1:8001"

QUERIES = [
    "How do I apply for a Post-Graduation Work Permit (PGWP)?",
    "What are the requirements for Express Entry?",
    "How much does a study permit cost?",
    "Can I work while studying in Canada?",
]

for qi, query in enumerate(QUERIES, 1):
    print(f"\n{'='*70}")
    print(f"  TEST {qi}/{len(QUERIES)}: {query}")
    print(f"{'='*70}")

    payload = {
        "persona_slug": "live-study-immigration",
        "question": query,
        "top_k": 5,
    }

    t0 = time.perf_counter()
    resp = requests.post(f"{ENGINE_URL}/engine/consulting/query", json=payload, timeout=120)
    elapsed = time.perf_counter() - t0
    data = resp.json()

    answer = data.get("answer", "")
    sources = data.get("sources", [])

    print(f"  Latency: {elapsed:.1f}s | Sources: {len(sources)} | Answer: {len(answer)} chars")
    print(f"  Answer preview: {answer[:200].replace(chr(10), ' ')}")
    print()

    for i, s in enumerate(sources):
        bid = s.get("book_id", "?")
        src = s.get("retrieval_source", "?")
        v = s.get("vector_score", 0)
        k = s.get("bm25_score", 0)
        short_bid = "/".join(bid.split("/")[-3:]) if "/" in bid else bid
        text = (s.get("full_content") or s.get("text", ""))[:100].replace("\n", " ")
        print(f"  [{i+1}] {src:6s} V:{v:.3f} K:{k:.3f}  .../{short_bid}")
        print(f"      {text}")

print(f"\n{'='*70}")
print("  ALL TESTS COMPLETE")
print(f"{'='*70}")
