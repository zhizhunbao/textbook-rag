"""Check where the PAL definition chunk ranks in BM25 and Vector."""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine_v2.settings import init_settings
init_settings()

from engine_v2.retrievers.hybrid import get_hybrid_retriever

question = "What is a Provincial Attestation Letter (PAL)?"
book_filter = ["en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents/provincial-attestation-letter/provincial-attestation-letter"]

retriever = get_hybrid_retriever(
    similarity_top_k=20,
    collection_name="ca_federal",
    book_id_strings=book_filter,
)
nodes = retriever.retrieve(question)

print(f"Total retrieved: {len(nodes)}")
print()
for i, n in enumerate(nodes):
    text = n.node.text[:150].replace("\n", " ")
    src = n.node.metadata.get("retrieval_source", "?")
    v = n.node.metadata.get("vector_score", 0)
    k = n.node.metadata.get("bm25_score", 0)
    is_def = "PAL/TAL) is" in n.node.text[:100]
    marker = " <<<< DEFINITION" if is_def else ""
    print(f"[{i+1:2d}] rrf={float(n.score or 0):.5f} {src:6s} V:{v:.3f} K:{k:.3f}{marker}")
    print(f"     {text}")
    print()
