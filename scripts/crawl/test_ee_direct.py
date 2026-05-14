"""Direct ChromaDB vector search test — bypasses engine API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

from engine_v2.settings import init_settings
init_settings()
from engine_v2.ingestion.pipeline import get_vector_store
from llama_index.core import VectorStoreIndex

vector_store = get_vector_store(collection_name="ca_federal")
index = VectorStoreIndex.from_vector_store(vector_store)
retriever = index.as_retriever(similarity_top_k=5)

queries = [
    "express entry CRS cutoff score 2026",
    "CEC Canadian Experience Class invitation rounds CRS 2026",
    "2026 express entry rounds table CRS invitations",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    results = retriever.retrieve(q)
    for i, r in enumerate(results):
        book = r.metadata.get("book_id", "?")
        page = r.metadata.get("page_label", "?")
        has_table = "| #" in r.text or "| 414" in r.text or "| 413" in r.text
        print(f"  [{i}] score={r.score:.3f} book={book[-30:]} page={page}")
        print(f"       {'✅ TABLE' if has_table else '  '} {r.text[:150].replace(chr(10), ' ')}")
