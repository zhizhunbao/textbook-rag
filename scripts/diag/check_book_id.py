"""Quick check: is a specific book_id in ChromaDB?

Usage:
  uv run python scripts/diag/check_book_id.py rounds-invitations
  uv run python scripts/diag/check_book_id.py rounds-invitations --collection ca_federal
"""
import argparse
import sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent.parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_persist"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pattern", help="book_id pattern to search for (substring match)")
    p.add_argument("--collection", default="ca_federal")
    p.add_argument("--query", help="Optional: test a vector query against matching chunks")
    args = p.parse_args()

    import chromadb
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )
    col = client.get_collection(args.collection)
    total = col.count()
    print(f"Collection: {args.collection} ({total} chunks)")

    # Scan for matching book_ids
    batch_size = 10000
    offset = 0
    matches: Counter = Counter()
    while offset < total:
        r = col.get(limit=batch_size, offset=offset, include=["metadatas"])
        if not r["ids"]:
            break
        for m in r["metadatas"]:
            bid = m.get("book_id", "")
            if args.pattern in bid:
                matches[bid] += 1
        offset += len(r["ids"])

    if matches:
        print(f"\n✅ Found {sum(matches.values())} chunks matching '{args.pattern}':")
        for bid, cnt in matches.most_common():
            print(f"  {cnt:>5} chunks: {bid}")
    else:
        print(f"\n❌ No book_id containing '{args.pattern}' found in {args.collection}")

    # Optional vector query test
    if args.query and matches:
        print(f"\nVector query: '{args.query}' (top 20)")
        r = col.query(query_texts=[args.query], n_results=20, include=["metadatas", "distances"])
        for i, (meta, dist) in enumerate(zip(r["metadatas"][0], r["distances"][0])):
            bid = meta.get("book_id", "?")
            hit = args.pattern in bid
            marker = "→ HIT" if hit else "     "
            print(f"  {marker} [{i+1:>2}] dist={dist:.4f} book={bid}")


if __name__ == "__main__":
    main()
