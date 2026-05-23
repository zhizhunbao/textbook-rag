"""Check if EE reform consultation was ingested into ChromaDB."""
import sys
sys.path.insert(0, ".")
from engine_v2.settings import init_settings
init_settings()
from engine_v2.ingestion.pipeline import get_vector_store

vs = get_vector_store("ca_federal")
col = vs._collection

# 1. Exact match
book_id = "en/immigration-refugees-citizenship/corporate/transparency/consultations/2026-consultation-express-entry-reforms"
r = col.get(where={"book_id": book_id}, limit=5, include=["metadatas"])
print(f"Exact match for book_id: {len(r['ids'])} docs")

if not r["ids"]:
    # 2. Search all book_ids for consultation
    print("Searching all book_ids...")
    r2 = col.get(limit=23500, include=["metadatas"])
    bids = set(m.get("book_id", "") for m in r2["metadatas"])
    print(f"Total unique book_ids: {len(bids)}")
    
    matches = [b for b in sorted(bids) if "consult" in b.lower()]
    print(f"\nConsultation book_ids ({len(matches)}):")
    for b in matches:
        print(f"  {b}")
    
    matches2 = [b for b in sorted(bids) if "2026" in b]
    print(f"\n2026 book_ids ({len(matches2)}):")
    for b in matches2:
        print(f"  {b}")
