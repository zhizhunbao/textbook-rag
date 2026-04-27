"""generator — Generate and auto-score study questions from textbook chunks.

Responsibilities:
    - Sample chunks from ChromaDB with multi-book / category / chapter filtering
    - Build LLM prompts from sampled context
    - Use LlamaIndex structured_predict for robust, schema-validated LLM outputs
    - Auto-score each question via LLM-as-Judge (relevance, clarity, difficulty)

Ref: llama_index.core.evaluation.CorrectnessEvaluator — scoring pattern (1-5)
Ref: llama_index.core.llms.llm.LLM.structured_predict — structured output
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import chromadb
from llama_index.core.program.utils import create_list_model
from llama_index.core.settings import Settings
from loguru import logger
from pydantic import BaseModel, Field

from engine_v2.question_gen.prompts import GEN_PROMPT_TMPL, SCORE_PROMPT_TMPL
from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
)

# ============================================================
# Pydantic schemas for structured_predict
# Ref: llama_index.core.output_parsers.pydantic.PydanticOutputParser
# ============================================================
class QuestionItem(BaseModel):
    """Single generated study question (LLM output schema)."""

    question: str
    difficulty: str = "medium"
    type: str = "conceptual"
    question_category: str = ""


class QuestionScoreOutput(BaseModel):
    """LLM-as-Judge scoring result (LLM output schema)."""

    relevance: int = Field(default=1, ge=1, le=5)
    clarity: int = Field(default=1, ge=1, le=5)
    difficulty: int = Field(default=1, ge=1, le=5)
    reasoning: str = ""


# List wrapper for structured_predict (returns single Pydantic instance)
QuestionItemList = create_list_model(QuestionItem)


# ============================================================
# Data types
# ============================================================
@dataclass
class QuestionScores:
    """Auto-evaluation scores for a generated question."""

    relevance: int = 0
    clarity: int = 0
    difficulty: int = 0
    overall: float = 0.0
    reasoning: str = ""


@dataclass
class GeneratedQuestion:
    """A single generated question with optional scores."""

    question: str
    difficulty: str = "medium"
    question_type: str = "conceptual"
    question_category: str = ""
    source_chunk_id: str = ""
    book_id: str = ""
    book_title: str = ""
    source_page: int = 0
    scores: QuestionScores = field(default_factory=QuestionScores)


# ============================================================
# Generator
# ============================================================
class QuestionGenerator:
    """Generate and score study questions from textbook chunks using LLM.

    Uses Settings.llm (configured globally) for both generation and scoring.
    Samples chunks from ChromaDB for context.
    """

    def __init__(self, collection_name: str = CHROMA_COLLECTION) -> None:
        self._collection_name = collection_name

    def generate(
        self,
        book_ids: list[str] | None = None,
        book_id: str | None = None,
        category: str | None = None,
        page_start: int | None = None,
        page_end: int | None = None,
        count: int = 5,
        chunk_sample_size: int = 3,
        auto_score: bool = True,
    ) -> list[GeneratedQuestion]:
        """Generate questions from sampled textbook chunks.

        Args:
            book_ids: Filter to specific books (array).
            book_id: Legacy single book filter (converted to book_ids).
            category: Filter chunks by category metadata.
            page_start: Filter chunks with page_idx >= page_start (0-indexed).
            page_end: Filter chunks with page_idx < page_end (0-indexed, exclusive).
            count: Number of questions to generate.
            chunk_sample_size: Number of chunks to sample as context.
            auto_score: Whether to auto-score questions after generation.

        Returns:
            List of GeneratedQuestion with scores (if auto_score=True).
        """
        # Legacy compat: single book_id → book_ids list
        if book_id and not book_ids:
            book_ids = [book_id]

        chunks = self._sample_chunks(
            book_ids=book_ids,
            category=category,
            page_start=page_start,
            page_end=page_end,
            n=chunk_sample_size,
        )
        if not chunks:
            logger.warning("No chunks found for question generation")
            return []

        context = "\n\n---\n\n".join(
            f"[Chunk {i+1}] {c['document']}" for i, c in enumerate(chunks)
        )

        # structured_predict: auto-injects JSON schema + validates output
        try:
            result = Settings.llm.structured_predict(
                QuestionItemList,
                GEN_PROMPT_TMPL,
                count=str(count),
                context=context,
            )
            questions = self._map_items_to_questions(result.items, chunks)
        except Exception as e:
            logger.warning("structured_predict failed for generation: {}", e)
            questions = []

        logger.info("Generated {} questions", len(questions))

        # Auto-score each question against its source context
        if auto_score and questions:
            self._score_questions(questions, context)

        return questions[:count]

    # ============================================================
    # Auto-scoring (LLM-as-Judge)
    # ============================================================
    def _score_questions(
        self, questions: list[GeneratedQuestion], context: str
    ) -> None:
        """Score each generated question using LLM-as-Judge.

        Modifies questions in-place, adding scores.
        Uses structured_predict for robust, schema-validated output.
        """
        logger.info("Scoring {} questions via LLM-as-Judge...", len(questions))

        for i, q in enumerate(questions):
            try:
                parsed = Settings.llm.structured_predict(
                    QuestionScoreOutput,
                    SCORE_PROMPT_TMPL,
                    context=context,
                    question=q.question,
                )
                # Map Pydantic output → dataclass
                relevance = parsed.relevance
                clarity = parsed.clarity
                overall = (
                    round((relevance + clarity) / 2, 1)
                    if (relevance and clarity)
                    else 0.0
                )
                q.scores = QuestionScores(
                    relevance=relevance,
                    clarity=clarity,
                    difficulty=parsed.difficulty,
                    overall=overall,
                    reasoning=parsed.reasoning,
                )
                logger.debug(
                    "Q{}: relevance={}, clarity={}, difficulty={}, overall={}",
                    i + 1,
                    q.scores.relevance,
                    q.scores.clarity,
                    q.scores.difficulty,
                    q.scores.overall,
                )
            except Exception as e:
                logger.warning("Failed to score question {}: {}", i + 1, e)
                q.scores = QuestionScores()

    # ============================================================
    # ChromaDB sampling
    # ============================================================
    def _sample_chunks(
        self,
        book_ids: list[str] | None,
        category: str | None,
        page_start: int | None,
        page_end: int | None,
        n: int,
    ) -> list[dict[str, Any]]:
        """Sample random chunks from ChromaDB with page-range filtering."""
        client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name=self._collection_name)

        where = self._build_where(book_ids, category, page_start, page_end)
        logger.debug("ChromaDB where filter: {}", where)

        results = collection.get(
            where=where,
            limit=min(n * 5, 100),
            include=["documents", "metadatas"],
        )

        if not results["documents"]:
            return []

        indices = list(range(len(results["documents"])))
        sampled = random.sample(indices, min(n, len(indices)))

        return [
            {
                "id": results["ids"][i],
                "document": results["documents"][i],
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
            }
            for i in sampled
        ]

    @staticmethod
    def _build_where(
        book_ids: list[str] | None,
        category: str | None,
        page_start: int | None,
        page_end: int | None,
    ) -> dict[str, Any] | None:
        """Build ChromaDB where filter with page-range support."""
        conditions: list[dict[str, Any]] = []

        # Multi-book filter via $or
        if book_ids and len(book_ids) == 1:
            conditions.append({"book_id": book_ids[0]})
        elif book_ids and len(book_ids) > 1:
            conditions.append(
                {"$or": [{"book_id": bid} for bid in book_ids]}
            )

        if category:
            conditions.append({"category": category})

        # Page range filter (0-indexed, already stored in ChromaDB as page_idx)
        if page_start is not None:
            conditions.append({"page_idx": {"$gte": page_start}})
        if page_end is not None:
            conditions.append({"page_idx": {"$lt": page_end}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    # ============================================================
    # Structured output → dataclass mapping
    # ============================================================
    @staticmethod
    def _map_items_to_questions(
        items: list[QuestionItem], chunks: list[dict[str, Any]]
    ) -> list[GeneratedQuestion]:
        """Map Pydantic QuestionItem list → GeneratedQuestion dataclasses."""
        questions: list[GeneratedQuestion] = []
        for idx, item in enumerate(items):
            if not item.question:
                continue
            # Map each question to its source chunk (round-robin if more questions than chunks)
            chunk_idx = idx % len(chunks) if chunks else 0
            source = chunks[chunk_idx] if chunks else {}
            source_meta = source.get("metadata", {})
            questions.append(GeneratedQuestion(
                question=item.question,
                difficulty=item.difficulty,
                question_type=item.type,
                question_category=item.question_category,
                source_chunk_id=source.get("id", ""),
                book_id=source_meta.get("book_id", ""),
                book_title=source_meta.get("book_title", ""),
                source_page=source_meta.get("page_idx", 0),
            ))
        return questions
