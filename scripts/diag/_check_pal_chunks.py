"""Check what chunks exist for the PAL document in ca_federal."""
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import chromadb
from engine_v2.settings import CHROMA_PERSIST_DIR

client = chromadb.PersistentClient(
    path=str(CHROMA_PERSIST_DIR),
    settings=chromadb.Settings(anonymized_telemetry=False),
)
coll = client.get_collection("ca_federal")

PAL_BOOK = (
    "en/immigration-refugees-citizenship/services/study-canada/"
    "study-permit/get-documents/provincial-attestation-letter/"
    "provincial-attestation-letter"
)

r = coll.get(where={"book_id": PAL_BOOK}, include=["documents", "metadatas"])
print(f"PAL doc chunks in ca_federal: {len(r['ids'])}")
print(f"book_id filter: {PAL_BOOK}")
print()

for i, (did, doc, meta) in enumerate(zip(r["ids"], r["documents"], r["metadatas"])):
    page = meta.get("page_idx", "?")
    ct = meta.get("content_type", "?")
    print(f"  [{i+1}] page={page}  type={ct}  len={len(doc or '')}  id={did[:50]}")
    print(f"      {(doc or '')[:250].replace(chr(10), ' ')}")
    print()
