"""Test with retrieval_k=50 to find definition chunk."""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine_v2.settings import init_settings
init_settings()

from engine_v2.retrievers.hybrid import multi_collection_retrieve
from engine_v2.retrievers.book_filter import prefilter_book_ids
from llama_index.core.schema import QueryBundle as QB
from engine_v2.query_engine.citation import MinContentPostprocessor, RelevanceFilterPostprocessor

question = "What is a Provincial Attestation Letter (PAL)?"
book_ids = prefilter_book_ids(question, "ca_federal", max_books=15)

nodes = multi_collection_retrieve(
    question=question, collection_names=["ca_federal"],
    top_k=50, book_id_strings=book_ids,
)
print(f"Retrieved: {len(nodes)} nodes")

# Check definition
for i, n in enumerate(nodes):
    if "(PAL/TAL) is" in n.node.text[:300]:
        print(f"  DEFINITION at position {i+1}")
        break
else:
    print("  DEFINITION NOT IN CANDIDATES!")

# Filters
qb = QB(query_str=question)
nodes = MinContentPostprocessor(min_chars=50, min_single_line=120).postprocess_nodes(nodes, query_bundle=qb)
nodes = RelevanceFilterPostprocessor(min_vector_score=0.55, min_bm25_score=1.0).postprocess_nodes(nodes, query_bundle=qb)
print(f"After filters: {len(nodes)} nodes")

for i, n in enumerate(nodes):
    if "(PAL/TAL) is" in n.node.text[:300]:
        print(f"  DEFINITION at position {i+1}")
        break
else:
    print("  DEFINITION FILTERED OUT")

# Reranker
from llama_index.core.postprocessor import SentenceTransformerRerank
reranker = SentenceTransformerRerank(model="cross-encoder/ms-marco-MiniLM-L-12-v2", top_n=5, keep_retrieval_score=True)
nodes = reranker.postprocess_nodes(nodes, query_bundle=qb)
print(f"\nFinal {len(nodes)} nodes:")
for i, n in enumerate(nodes):
    txt = n.node.text[:120].replace("\n", " ")
    is_def = "(PAL/TAL) is" in n.node.text[:300]
    marker = " <<<< DEFINITION" if is_def else ""
    print(f"  [{i+1}] score={float(n.score or 0):.4f} {txt}{marker}")
