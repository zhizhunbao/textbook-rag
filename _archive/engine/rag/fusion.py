"""Reciprocal Rank Fusion (RRF) — fuses multiple ranked hit lists."""

from __future__ import annotations

from engine.rag.types import ChunkHit


class RRFusion:
    """Stateless RRF implementation.

    Formula: score(d) = Σ_i  1 / (k + rank_i(d))
    where rank_i is 1-based position in strategy i's result list.

    Reference: Cormack, Clarke & Buettcher, SIGIR 2009.
    """

    @staticmethod
    def fuse(hit_lists: list[list[ChunkHit]], k: int = 60) -> list[ChunkHit]:
        """Fuse 2+ ranked hit lists into a single ranked list.

        Args:
            hit_lists: One list per strategy, hits ranked best-first.
            k:         RRF constant (default 60 matches v1.0 behaviour).

        Returns:
            Merged list ranked by descending RRF score.
        """
        scores: dict[int, float] = {}    # chunk.id → rrf_score
        hit_map: dict[int, ChunkHit] = {}  # chunk.id → ChunkHit

        for hits in hit_lists:
            for rank, hit in enumerate(hits, start=1):
                scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
                if hit.id not in hit_map:
                    hit_map[hit.id] = hit

        # Sort descending by RRF score
        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)

        result = []
        for fused_rank, cid in enumerate(sorted_ids, start=1):
            hit = hit_map[cid]
            hit.rrf_score = scores[cid]
            hit.fused_rank = fused_rank
            result.append(hit)

        return result
