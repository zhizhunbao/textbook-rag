"""Check specific chunk that shows as TOC in citation panel."""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine_v2.settings import init_settings
init_settings()

import chromadb
from engine_v2.settings import CHROMA_PERSIST_DIR

client = chromadb.PersistentClient(str(CHROMA_PERSIST_DIR))
coll = client.get_collection("ca_federal")

# Get ALL chunks from the PAL document
results = coll.get(
    where_document={"$contains": "Study permit conditions"},
    limit=50,
    include=["documents", "metadatas"],
)

print(f"Found {len(results['ids'])} chunks containing 'Study permit conditions'")
for i, (doc_id, doc, meta) in enumerate(zip(results["ids"], results["documents"], results["metadatas"])):
    if "Sections" not in doc and "study-canada" not in str(meta.get("book_id", "")):
        continue
    page = meta.get("page_idx", "?")
    bid = meta.get("book_id", "?")
    ctype = meta.get("content_type", "?")
    print(f"\n--- Chunk {i+1} ---")
    print(f"  ID: {doc_id}")
    print(f"  Page: {page}, Type: {ctype}")
    print(f"  Book: .../{'/'.join(str(bid).split('/')[-3:])}")
    print(f"  Text ({len(doc)} chars):")
    print(f"  ===")
    print(repr(doc[:600]))
    print(f"  ===")
