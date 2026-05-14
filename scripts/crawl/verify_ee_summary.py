"""Quick check: verify ee-rounds-summary chunks in ChromaDB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from engine_v2.settings import init_settings
init_settings()

from engine_v2.ingestion.pipeline import get_vector_store

COLLECTION = "ca_federal"
BOOK_ID = "ee-rounds-summary"

vector_store = get_vector_store(collection_name=COLLECTION)
chroma_col = vector_store._collection

result = chroma_col.get(
    where={"book_id": BOOK_ID},
    include=["documents", "metadatas"],
)
print(f"Chunks with book_id='{BOOK_ID}': {len(result['ids'])}")
for i in range(min(len(result['ids']), 12)):
    meta = result['metadatas'][i]
    doc = result['documents'][i][:120].replace('\n', ' ')
    print(f"  [{i}] page={meta.get('page_label','?')} len={len(result['documents'][i])} : {doc}")

# Also try a direct query on just this book
print("\n--- Querying with book_id filter ---")
qresult = chroma_col.query(
    query_texts=["express entry CRS cutoff score 2026"],
    where={"book_id": BOOK_ID},
    n_results=3,
    include=["documents", "metadatas", "distances"],
)
for i, (doc, meta, dist) in enumerate(zip(
    qresult["documents"][0], qresult["metadatas"][0], qresult["distances"][0]
)):
    print(f"  [{i}] dist={dist:.3f} page={meta.get('page_label','?')} : {doc[:120]}")
