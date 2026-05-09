"""Diagnose multi-collection retrieval pipeline step by step."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine_v2.settings import init_settings
init_settings()

from engine_v2.retrievers.hybrid import multi_collection_retrieve
from engine_v2.query_engine.citation import RelevanceFilterPostprocessor
from llama_index.core.schema import QueryBundle

question = "Which is safer for PGWP and PR, a 1-year program or a 2-year program?"

colls = [
    "ca_federal", "ca_edu_algonquin", "ca_prov_ontario",
    "ca_prov_bc", "ca_prov_alberta", "ca_prov_manitoba",
    "ca_prov_saskatchewan", "ca_prov_nova_scotia",
    "ca_prov_new_brunswick", "ca_prov_nwt", "ca_prov_quebec",
]

print(f"Question: {question}")
print(f"Collections: {len(colls)}")
print()

# Step 1: Raw multi-collection retrieval
retrieval_k = 5 * 2  # top_k * 2 for reranker headroom
merged = multi_collection_retrieve(
    question=question, collection_names=colls, top_k=retrieval_k,
)
print(f"[Step 1] multi_collection_retrieve: {len(merged)} nodes")
for i, n in enumerate(merged[:5]):
    origin = n.node.metadata.get("retrieval_origin", "?")
    vec = n.node.metadata.get("vector_score", 0)
    bm25 = n.node.metadata.get("bm25_score", 0)
    print(f"  [{i+1}] rrf={float(n.score or 0):.6f} origin={origin} vec={vec:.4f} bm25={bm25:.4f}")
    print(f"       {n.node.text[:100]}")
print()

# Step 2: RelevanceFilter
query_bundle = QueryBundle(query_str=question)
rel_filter = RelevanceFilterPostprocessor(min_vector_score=0.55, min_bm25_score=1.0)
after_rel = rel_filter.postprocess_nodes(merged, query_bundle=query_bundle)
print(f"[Step 2] RelevanceFilter(vec>=0.55 OR bm25>=1.0): {len(merged)} → {len(after_rel)} nodes")
if len(after_rel) < len(merged):
    dropped_nodes = [n for n in merged if n not in after_rel]
    for n in dropped_nodes[:5]:
        vec = n.node.metadata.get("vector_score", 0)
        bm25 = n.node.metadata.get("bm25_score", 0)
        print(f"  DROPPED: vec={vec:.4f} bm25={bm25:.4f} {n.node.text[:80]}")
print()

# Step 3: CrossEncoder reranker
from engine_v2.settings import RERANKER_ENABLED, RERANKER_MODEL, RERANKER_TOP_N, SIMILARITY_CUTOFF
if RERANKER_ENABLED and after_rel:
    reranker_top_n = min(RERANKER_TOP_N, 5)
    from llama_index.core.postprocessor import SentenceTransformerRerank
    reranker = SentenceTransformerRerank(
        model=RERANKER_MODEL, top_n=reranker_top_n, keep_retrieval_score=True,
    )
    after_rerank = reranker.postprocess_nodes(after_rel, query_bundle=query_bundle)
    print(f"[Step 3] CrossEncoder rerank (top_n={reranker_top_n}): {len(after_rel)} → {len(after_rerank)} nodes")
    for i, n in enumerate(after_rerank):
        print(f"  [{i+1}] score={float(n.score or 0):.6f} {n.node.text[:100]}")
else:
    after_rerank = after_rel
    print(f"[Step 3] Reranker skipped (enabled={RERANKER_ENABLED}, nodes={len(after_rel)})")
print()

# Step 4: Similarity cutoff
if SIMILARITY_CUTOFF > 0 and after_rerank:
    from llama_index.core.postprocessor import SimilarityPostprocessor
    sim_filter = SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)
    after_sim = sim_filter.postprocess_nodes(after_rerank, query_bundle=query_bundle)
    print(f"[Step 4] SimilarityPostprocessor(cutoff={SIMILARITY_CUTOFF}): {len(after_rerank)} → {len(after_sim)} nodes")
    if len(after_sim) < len(after_rerank):
        for n in after_rerank:
            if n not in after_sim:
                print(f"  DROPPED: score={float(n.score or 0):.6f} {n.node.text[:80]}")
else:
    after_sim = after_rerank
    print(f"[Step 4] Similarity cutoff skipped")
print()

print(f"FINAL: {len(after_sim)} nodes survive the pipeline")
