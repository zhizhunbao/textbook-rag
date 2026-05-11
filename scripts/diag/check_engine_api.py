"""Test Engine API full pipeline (BM25 + Vector + Reranker).

Usage:
  uv run python scripts/diag/check_engine_api.py "Express Entry latest round CRS score"
  uv run python scripts/diag/check_engine_api.py "CRS age points" --pattern crs-criteria
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import argparse
import requests


def main():
    p = argparse.ArgumentParser()
    p.add_argument("query", help="Query to test")
    p.add_argument("--pattern", default="rounds-invitations", help="book_id pattern to highlight")
    p.add_argument("--persona", default="live-study-immigration")
    p.add_argument("--api-url", default="http://localhost:8001")
    p.add_argument("--top-k", type=int, default=10)
    args = p.parse_args()

    print(f"Engine API query: '{args.query}'")
    print(f"Highlight pattern: '{args.pattern}'")
    print()

    r = requests.post(
        f"{args.api_url}/engine/consulting/query",
        json={"persona_slug": args.persona, "question": args.query, "top_k": args.top_k},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()

    sources = data.get("sources", [])
    print(f"Sources returned: {len(sources)}")
    for i, s in enumerate(sources, 1):
        bid = s.get("book_id", "?")
        hit = args.pattern in bid
        mark = ">> HIT" if hit else "      "
        score = s.get("score", 0)
        snippet = s.get("snippet", "")[:80].replace("\n", " ")
        print(f"  {mark} [{i:>2}] score={score:.4f} book={bid[:90]}")
        print(f"              snippet: {snippet}")

    answer = data.get("answer", "")
    print(f"\nAnswer ({len(answer)} chars):")
    print(answer[:500])


if __name__ == "__main__":
    main()
