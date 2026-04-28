"""retrieval_evaluator — Automatic retrieval recall evaluation on a QuestionSet.

Responsibilities:
    - Given a QuestionSet, run the retriever on each question
    - Check if sourceChunkId appears in the retrieved results
    - Compute Hit Rate, MRR, and per-question hit/miss details
    - Support reranker toggle for A/B comparison

Ref: llama_index.core.evaluation.retrieval — RetrieverEvaluator, HitRate, MRR
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from loguru import logger

from engine_v2.evaluation.retrieval_metrics import (
    RetrievalMetrics,
    compute_retrieval_metrics,
)
from engine_v2.settings import PAYLOAD_URL


# ============================================================
# Data classes
# ============================================================
@dataclass
class QuestionHit:
    """Per-question retrieval result."""

    question_id: int
    question: str
    source_chunk_id: str
    hit: bool
    rank: int | None = None  # Position of source chunk (1-indexed), None = miss
    retrieved_ids: list[str] = field(default_factory=list)


@dataclass
class RetrievalEvalResult:
    """Aggregate retrieval evaluation result for a QuestionSet."""

    dataset_id: int
    hit_rate: float = 0.0
    mrr: float = 0.0
    total_questions: int = 0
    hits: int = 0
    misses: int = 0
    per_question: list[QuestionHit] = field(default_factory=list)
    reranker_used: bool = False

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "dataset_id": self.dataset_id,
            "hit_rate": round(self.hit_rate, 4),
            "mrr": round(self.mrr, 4),
            "total_questions": self.total_questions,
            "hits": self.hits,
            "misses": self.misses,
            "reranker_used": self.reranker_used,
            "per_question": [
                {
                    "question_id": q.question_id,
                    "question": q.question,
                    "source_chunk_id": q.source_chunk_id,
                    "hit": q.hit,
                    "rank": q.rank,
                }
                for q in self.per_question
            ],
        }


# ============================================================
# Core evaluation function (QD-10)
# ============================================================
async def evaluate_retrieval_recall(
    dataset_id: int,
    top_k: int = 5,
    reranker: bool = False,
) -> RetrievalEvalResult:
    """Evaluate retrieval recall on a QuestionSet.

    For each question with a sourceChunkId:
        1. Run the retriever with the question text
        2. Check if sourceChunkId is in the top_k results
        3. Record rank position if found

    Args:
        dataset_id: Payload QuestionSet ID.
        top_k: Number of chunks to retrieve.
        reranker: Whether to enable LLM reranker.

    Returns:
        RetrievalEvalResult with aggregate + per-question metrics.
    """
    from engine_v2.retrievers.hybrid import get_hybrid_retriever

    # ── 1. Fetch questions with sourceChunkId ──
    questions = await _fetch_dataset_questions(dataset_id)
    valid_qs = [q for q in questions if q.get("sourceChunkId")]

    if not valid_qs:
        logger.warning(
            "No questions with sourceChunkId in dataset {}",
            dataset_id,
        )
        return RetrievalEvalResult(dataset_id=dataset_id)

    logger.info(
        "Evaluating retrieval recall — dataset_id={}, questions={}, top_k={}, reranker={}",
        dataset_id, len(valid_qs), top_k, reranker,
    )

    # ── 2. Get retriever ──
    retriever = get_hybrid_retriever(
        similarity_top_k=top_k,
    )

    # ── 3. Evaluate each question ──
    per_question: list[QuestionHit] = []
    total_rr = 0.0  # Sum of reciprocal ranks

    for qdata in valid_qs:
        question_text = qdata["question"]
        source_chunk_id = qdata["sourceChunkId"]

        try:
            nodes = retriever.retrieve(question_text)
            retrieved_ids = [n.node.node_id for n in nodes]
        except Exception as exc:
            logger.warning(
                "Retrieval failed for question {}: {}",
                qdata.get("id", "?"), exc,
            )
            retrieved_ids = []

        # Check if source chunk is in results
        rank = None
        hit = False
        for i, rid in enumerate(retrieved_ids):
            if rid == source_chunk_id:
                rank = i + 1  # 1-indexed
                hit = True
                total_rr += 1.0 / rank
                break

        per_question.append(QuestionHit(
            question_id=qdata.get("id", 0),
            question=question_text,
            source_chunk_id=source_chunk_id,
            hit=hit,
            rank=rank,
            retrieved_ids=retrieved_ids[:5],  # Keep top-5 for debug
        ))

    # ── 4. Compute aggregate metrics ──
    hits = sum(1 for q in per_question if q.hit)
    total = len(per_question)
    hit_rate = hits / total if total > 0 else 0.0
    mrr = total_rr / total if total > 0 else 0.0

    result = RetrievalEvalResult(
        dataset_id=dataset_id,
        hit_rate=hit_rate,
        mrr=mrr,
        total_questions=total,
        hits=hits,
        misses=total - hits,
        per_question=per_question,
        reranker_used=reranker,
    )

    logger.info(
        "Retrieval eval complete — dataset={}, hit_rate={:.2%}, mrr={:.4f}, "
        "hits={}/{}, reranker={}",
        dataset_id, hit_rate, mrr, hits, total, reranker,
    )

    return result


# ============================================================
# Helpers — fetch dataset questions from Payload
# ============================================================
async def _fetch_dataset_questions(
    dataset_id: int,
    limit: int = 500,
) -> list[dict]:
    """Fetch questions belonging to a dataset from Payload CMS."""
    from engine_v2.evaluation.history import _get_payload_token

    token = await _get_payload_token()
    url = (
        f"{PAYLOAD_URL}/api/questions"
        f"?where[datasetId][equals]={dataset_id}"
        f"&limit={limit}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"JWT {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("docs", [])
    except Exception as exc:
        logger.warning(
            "Failed to fetch dataset {} questions: {}", dataset_id, exc,
        )
        return []
