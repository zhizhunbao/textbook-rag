"""ir — Pure-math Information Retrieval metrics (zero LLM calls).

Metrics:
    hit_rate   — at least one expected chunk in results
    mrr        — reciprocal rank of first relevant result
    precision  — fraction of top-K that are relevant
    recall     — fraction of relevant that appear in top-K
    ndcg       — normalized discounted cumulative gain
    aggregate  — compute all 5 metrics in one call
"""
