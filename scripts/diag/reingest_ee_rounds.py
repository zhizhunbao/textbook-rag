"""Re-ingest ee_rounds files with merge_sections=True.

Deletes old chunks for these book_ids, then re-ingests with the
improved heading classifier + section merger.
"""
import sys
sys.path.insert(0, ".")

from pathlib import Path
from engine_v2.settings import init_settings
init_settings()

from engine_v2.ingestion.pipeline import get_vector_store
from engine_v2.readers.mineru_reader import MinerUReader
from engine_v2.ingestion.transformations import BBoxNormalizer
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.settings import Settings

MINERU_DIR = Path("data/mineru_output")
COLLECTION = "ca_federal_data"

BOOK_IDS = [
    "content/dam/ircc/documents/json/ee_rounds_4_en",
    "content/dam/ircc/documents/json/ee_rounds_123_en",
]

# Step 1: Delete old chunks for these book_ids
print("=" * 60)
print("Step 1: Delete old chunks")
print("=" * 60)

import chromadb
client = chromadb.PersistentClient(path="data/chroma_db")
try:
    collection = client.get_collection(COLLECTION)
    for book_id in BOOK_IDS:
        # Get IDs of existing chunks for this book_id
        existing = collection.get(
            where={"book_id": book_id},
            include=[],
        )
        if existing["ids"]:
            print(f"  Deleting {len(existing['ids'])} old chunks for {book_id}")
            collection.delete(ids=existing["ids"])
        else:
            print(f"  No old chunks for {book_id}")
except Exception as e:
    print(f"  Collection issue (may not exist yet): {e}")

# Step 2: Re-ingest with merge_sections=True
print(f"\n{'=' * 60}")
print("Step 2: Re-ingest with merge_sections=True")
print("=" * 60)

reader = MinerUReader(MINERU_DIR, merge_sections=True)
vector_store = get_vector_store(collection_name=COLLECTION)
pipeline = IngestionPipeline(
    transformations=[
        BBoxNormalizer(),
        Settings.embed_model,
    ],
    vector_store=vector_store,
)

for book_id in BOOK_IDS:
    print(f"\n  Processing: {book_id}")
    documents = reader.load_data(book_dir_name=book_id, category="federal-ircc")
    if not documents:
        print(f"  [FAIL] No documents found")
        continue
    print(f"  [DOCS] {len(documents)} documents loaded")
    
    nodes = pipeline.run(documents=documents, show_progress=True)
    print(f"  [OK] Ingested {len(nodes)} nodes")

# Step 3: Verify
print(f"\n{'=' * 60}")
print("Step 3: Verify")
print("=" * 60)
collection = client.get_collection(COLLECTION)
for book_id in BOOK_IDS:
    result = collection.get(
        where={"book_id": book_id},
        include=["metadatas"],
    )
    print(f"  {book_id}: {len(result['ids'])} chunks in ChromaDB")

print("\nDone!")
