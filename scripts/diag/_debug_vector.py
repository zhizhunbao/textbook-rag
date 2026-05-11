"""Quick debug: check what book_ids the MISS queries actually hit."""
import chromadb

client = chromadb.PersistentClient(
    path="data/chroma_persist",
    settings=chromadb.Settings(anonymized_telemetry=False),
)

# Phase 2 MISS queries
miss_queries = [
    ("ca_federal", "CRS score breakdown maximum points each category", "check-score/crs-criteria"),
    ("ca_federal", "Comprehensive Ranking System core human capital factors", "check-score/crs-criteria"),
    ("ca_federal_data", "Express Entry round invitations CRS lowest score date", "ee_rounds_123_en"),
    ("ca_federal", "Express Entry rounds of invitations", "express-entry-rounds"),
]

for col_name, query, target in miss_queries:
    col = client.get_collection(col_name)
    r = col.query(query_texts=[query], n_results=5, include=["metadatas", "distances"])
    print(f"\nQ: {query}")
    print(f"  Target: {target}")
    for i, (m, d) in enumerate(zip(r["metadatas"][0], r["distances"][0])):
        bid = m.get("book_id", "?")
        hit = "✅" if target in bid else "  "
        print(f"  {hit} [{i+1}] dist={d:.4f} book={bid}")
