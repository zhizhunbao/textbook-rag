"""Quick stream test to verify retrieval is working."""
import sys
import json
import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

question = sys.argv[1] if len(sys.argv) > 1 else "What is PGWP?"

print(f"Question: {question}")
print(f"Endpoint: http://127.0.0.1:8001/engine/consulting/query/stream")
print()

with httpx.stream(
    "POST",
    "http://127.0.0.1:8001/engine/consulting/query/stream",
    json={"persona_slug": "live-study-immigration", "question": question, "top_k": 5},
    timeout=120,
) as resp:
    event_type = ""
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            data = json.loads(line[6:])
            if event_type == "retrieval_done":
                stats = data.get("stats", {})
                sources = data.get("sources", [])
                print(f"RETRIEVAL_DONE: {stats.get('source_count', 0)} sources")
                for s in sources[:5]:
                    origin = s.get("retrieval_origin", "?")
                    text = (s.get("text") or "")[:100]
                    vec = s.get("vector_score", 0)
                    bm25 = s.get("bm25_score", 0)
                    print(f"  - origin={origin} vec={vec:.4f} bm25={bm25:.4f}")
                    print(f"    {text}")
            elif event_type == "no_retrieval":
                print(f"NO_RETRIEVAL: {data.get('message')}")
            elif event_type == "warning":
                print(f"WARNING: {data.get('message')}")
            elif event_type == "error":
                print(f"ERROR: {data.get('message')}")
            elif event_type == "done":
                answer = data.get("answer", "")
                src_count = data.get("stats", {}).get("source_count", 0)
                print(f"\nDONE: {src_count} sources, answer length={len(answer)}")
                print(f"Answer preview: {answer[:200]}")
