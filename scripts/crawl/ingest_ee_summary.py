"""Ingest EE rounds summary — one chunk per year for optimal RAG retrieval.

Bypasses MinerUReader/SectionMerger to create proper-sized chunks
with full table data intact.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from engine_v2.settings import init_settings
init_settings()

from engine_v2.ingestion.pipeline import get_vector_store
from engine_v2.ingestion.transformations import BBoxNormalizer
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import Document
from llama_index.core.settings import Settings

SUMMARY_FILE = Path("data/mineru_output/federal-ircc/ee-rounds-summary/auto/ee-rounds-summary.md")
COLLECTION = "ca_federal"
BOOK_ID = "ee-rounds-summary"

# Step 0: Delete old chunks for this book_id
print("Step 0: Clean old chunks...")
vector_store = get_vector_store(collection_name=COLLECTION)
try:
    chroma_col = vector_store._collection
    existing = chroma_col.get(where={"book_id": BOOK_ID}, include=[])
    if existing["ids"]:
        chroma_col.delete(ids=existing["ids"])
        print(f"  Deleted {len(existing['ids'])} old chunks")
    else:
        print("  No old chunks found")
except Exception as e:
    print(f"  Clean skipped: {e}")

# Step 1: Split by year sections
print("\nStep 1: Split summary into year chunks...")
text = SUMMARY_FILE.read_text(encoding="utf-8")

# Split on "# Express Entry Rounds YYYY" headings
sections = re.split(r'\n(?=# Express Entry Rounds \d{4})', text)

documents = []
for section in sections:
    section = section.strip()
    if not section:
        continue
    
    # Extract year from heading
    year_match = re.search(r'Express Entry Rounds (\d{4})', section)
    if not year_match:
        # This is the intro/header section
        continue
    
    year = year_match.group(1)
    
    doc = Document(
        text=section,
        metadata={
            "book_id": BOOK_ID,
            "page_label": f"EE-Rounds-{year}",
            "source_url": "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_4_en.json",
            "category": "federal-ircc",
            "file_name": "ee-rounds-summary.md",
        },
        excluded_embed_metadata_keys=["book_id", "source_url", "category", "file_name"],
        excluded_llm_metadata_keys=["book_id", "source_url", "category", "file_name"],
    )
    documents.append(doc)
    print(f"  {year}: {len(section)} chars")

print(f"\nTotal: {len(documents)} year-chunks")

# Step 2: Ingest
print("\nStep 2: Ingesting into ChromaDB...")
pipeline = IngestionPipeline(
    transformations=[
        Settings.embed_model,
    ],
    vector_store=vector_store,
)
nodes = pipeline.run(documents=documents, show_progress=True)
print(f"  Ingested {len(nodes)} nodes")

# Step 3: Verify retrieval
print("\nStep 3: Verification query...")
from llama_index.core import VectorStoreIndex

index = VectorStoreIndex.from_vector_store(vector_store)
retriever = index.as_retriever(similarity_top_k=3)
results = retriever.retrieve("express entry CRS cutoff score 2026")
print(f"  Query: 'express entry CRS cutoff score 2026'")
print(f"  Results: {len(results)} chunks")
for r in results:
    year = r.metadata.get("page_label", "?")
    print(f"    [{year}] score={r.score:.3f} len={len(r.text)} : {r.text[:100]}...")

print("\nDone!")
