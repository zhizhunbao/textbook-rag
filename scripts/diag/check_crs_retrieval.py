"""Quick diagnostic: test ChromaDB retrieval for CRS-related queries."""
import chromadb

c = chromadb.PersistentClient(
    path="data/chroma_persist",
    settings=chromadb.Settings(anonymized_telemetry=False),
)
col = c.get_collection("ca_federal")
print(f"Total docs: {col.count()}")

# Test 1: Direct filter for crs-criteria book
print("\n--- Test 1: crs-criteria chunks ---")
r = col.get(
    where={"book_id": "en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score/crs-criteria/crs-criteria"},
    limit=5,
    include=["documents", "metadatas"],
)
print(f"Found: {len(r['ids'])} chunks")
for i, doc in enumerate(r["documents"][:3]):
    print(f"  [{i}] {doc[:150]}")

# Test 2: Vector query - Chinese
print("\n--- Test 2: Vector query (Chinese) ---")
r = col.query(
    query_texts=["CRS分项上限和计算方式"],
    n_results=5,
    include=["metadatas", "distances"],
)
for d, m in zip(r["distances"][0], r["metadatas"][0]):
    bid = m.get("book_id", "?")
    page = m.get("page_number", "?")
    print(f"  dist={d:.4f} book={bid[:70]} page={page}")

# Test 3: Vector query - English
print("\n--- Test 3: Vector query (English) ---")
r = col.query(
    query_texts=["CRS score breakdown maximum points each category"],
    n_results=5,
    include=["metadatas", "distances"],
)
for d, m in zip(r["distances"][0], r["metadatas"][0]):
    bid = m.get("book_id", "?")
    page = m.get("page_number", "?")
    print(f"  dist={d:.4f} book={bid[:70]} page={page}")

# Test 4: Check ee_rounds_4_en
print("\n--- Test 4: ee_rounds_4_en chunks ---")
r = col.get(
    where={"book_id": "content/dam/ircc/documents/json/ee_rounds_4_en/ee_rounds_4_en"},
    limit=3,
    include=["documents"],
)
print(f"Found: {len(r['ids'])} chunks")
for i, doc in enumerate(r["documents"][:2]):
    print(f"  [{i}] {doc[:150]}")
