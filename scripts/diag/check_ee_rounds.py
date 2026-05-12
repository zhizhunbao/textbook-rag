"""Compare ca_federal_data vs ca_federal collections."""
import sys
sys.path.insert(0, ".")
import chromadb

client = chromadb.PersistentClient(path="data/chroma_persist")

for name in ["ca_federal_data", "ca_federal"]:
    col = client.get_collection(name)
    count = col.count()
    
    # Sample some entries
    sample = col.get(limit=5, include=["metadatas", "documents"])
    
    print(f"\n{'='*60}")
    print(f"{name}: {count} vectors")
    print(f"{'='*60}")
    
    books = set()
    for meta in sample["metadatas"]:
        books.add(meta.get("book_id", "?")[:50])
    print(f"Sample book_ids: {books}")
    
    for i in range(min(3, len(sample["documents"]))):
        doc = sample["documents"][i][:120].replace("\n", " ").encode("ascii", "replace").decode()
        meta = sample["metadatas"][i]
        cat = meta.get("category", "?")
        book = meta.get("book_id", "?")[:40]
        print(f"  [{i}] cat={cat} book={book}")
        print(f"      {doc}")
