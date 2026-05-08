"""Diagnose PAL retrieval: why "What is a Provincial Attestation Letter (PAL)?"
doesn't retrieve the right chunk from the PAL document.

Checks:
1. What chunks from the PAL doc exist in ChromaDB?
2. What does direct vector search return for the PAL query?
3. What does BM25 return?
4. What is the content/size of each PAL chunk?
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import chromadb
from engine_v2.settings import CHROMA_PERSIST_DIR

QUERY = "What is a Provincial Attestation Letter (PAL)?"

# ── Which collections might have PAL data? ──
# Federal IRCC data likely goes into a consulting collection
CANDIDATE_COLLECTIONS = [
    "textbook_chunks",
    "ca_federal",
    "persona_ca-immigration-consultant",
]


def main():
    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )

    # List all collections
    print("=" * 80)
    print("ALL COLLECTIONS IN CHROMADB")
    print("=" * 80)
    all_collections = client.list_collections()
    for c in all_collections:
        count = client.get_collection(c.name).count()
        print(f"  {c.name}: {count} documents")

    for coll_name in CANDIDATE_COLLECTIONS:
        try:
            collection = client.get_collection(coll_name)
        except Exception:
            print(f"\n⚠️  Collection '{coll_name}' does not exist, skipping.")
            continue

        total = collection.count()
        print(f"\n{'='*80}")
        print(f"COLLECTION: {coll_name} ({total} total docs)")
        print(f"{'='*80}")

        # ── 1. Find PAL chunks by book_id metadata ──
        # The PAL doc path is deeply nested; the book_dir_name used during
        # ingestion determines the book_id metadata value.
        # Try partial match on "attestation" in the document text
        pal_results = collection.get(
            where_document={"$contains": "attestation letter"},
            include=["documents", "metadatas"],
            limit=50,
        )

        pal_ids = pal_results["ids"]
        print(f"\n📄 Chunks containing 'attestation letter': {len(pal_ids)}")
        for i, (doc_id, text, meta) in enumerate(zip(
            pal_ids,
            pal_results["documents"],
            pal_results["metadatas"],
        )):
            book_id = meta.get("book_id", "?")
            page = meta.get("page_idx", "?")
            ct = meta.get("content_type", "?")
            text_preview = (text or "")[:120].replace("\n", " ")
            print(f"  [{i+1}] book_id={book_id}  page={page}  type={ct}")
            print(f"      text[:{len(text or '')}]: {text_preview}")

        # ── 2. Vector search for the PAL query ──
        print(f"\n🔍 Vector search: '{QUERY}'")

        # Need embedding model
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_emb = model.encode(QUERY).tolist()

        vec_results = collection.query(
            query_embeddings=[query_emb],
            n_results=10,
            include=["documents", "metadatas", "distances"],
        )

        for i in range(len(vec_results["ids"][0])):
            doc_id = vec_results["ids"][0][i]
            text = vec_results["documents"][0][i]
            meta = vec_results["metadatas"][0][i]
            dist = vec_results["distances"][0][i]
            # ChromaDB cosine distance = 1 - cosine_sim
            cos_sim = 1 - dist
            book_id = meta.get("book_id", "?")
            page = meta.get("page_idx", "?")
            text_preview = (text or "")[:120].replace("\n", " ")
            print(f"  [{i+1}] cos_sim={cos_sim:.4f}  book_id={book_id}  page={page}")
            print(f"      text[:{len(text or '')}]: {text_preview}")

        # ── 3. Check PAL chunk sizes (the root cause?) ──
        if pal_ids:
            print(f"\n📏 PAL chunk size analysis:")
            sizes = [len(t or "") for t in pal_results["documents"]]
            print(f"  Min: {min(sizes)} chars")
            print(f"  Max: {max(sizes)} chars")
            print(f"  Mean: {sum(sizes)/len(sizes):.0f} chars")
            print(f"  Chunks < 50 chars: {sum(1 for s in sizes if s < 50)}")
            print(f"  Chunks < 120 chars: {sum(1 for s in sizes if s < 120)}")
            print(f"  Chunks >= 200 chars: {sum(1 for s in sizes if s >= 200)}")

            # Show the top 5 largest chunks
            print(f"\n  🔝 Top 5 largest PAL chunks:")
            indexed = list(enumerate(zip(pal_ids, pal_results["documents"], pal_results["metadatas"])))
            indexed.sort(key=lambda x: len(x[1][1] or ""), reverse=True)
            for rank, (idx, (doc_id, text, meta)) in enumerate(indexed[:5], 1):
                print(f"  #{rank} ({len(text or '')} chars) page={meta.get('page_idx','?')}")
                print(f"      {(text or '')[:200].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
