"""generator — Generate and auto-score study questions from textbook chunks.

Responsibilities:
    - Sample chunks from ChromaDB with multi-book / category / chapter filtering
    - Build LLM prompts from sampled context
    - Parse structured JSON responses into GeneratedQuestion dataclasses
    - Auto-score each question via LLM-as-Judge (relevance, clarity, difficulty)

Ref: llama_index.core.evaluation.CorrectnessEvaluator — scoring pattern (1-5)
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

import chromadb
from llama_index.core.settings import Settings
from loguru import logger

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
)

# ============================================================
# Prompt templates
# ============================================================
QUESTION_GEN_PROMPT = """You are a textbook question generator. Given the following textbook excerpt, generate {count} study questions that test understanding of the key concepts.

Context:
{context}

Generate exactly {count} questions in JSON array format.
For each question, also provide a short "question_category" label that describes the topic/domain the question belongs to (e.g. "Labour Market", "Housing Starts", "Inflation & CPI", "Resale Market", "Commercial Vacancy", "Construction & Permits", "Policy & Highlights", "Population", or any other relevant topic label).
[
  {{"question": "...", "difficulty": "easy|medium|hard", "type": "factual|conceptual|analytical", "question_category": "..." }}
]

Questions:"""


QUESTION_SCORE_PROMPT = """You are an expert evaluator for study questions generated from textbook content.

Given a question and the source textbook excerpt it was generated from, evaluate the question on three dimensions.

## Source Context
{context}

## Question to Evaluate
{question}

## Scoring Criteria (1-5 each)

**Relevance**: Can this question be answered using ONLY the source context?
- 5: Directly answerable from the context
- 3: Partially answerable; requires some outside knowledge
- 1: Cannot be answered from the context at all (hallucination)

**Clarity**: Is the question clearly written and unambiguous?
- 5: Crystal clear, single interpretation
- 3: Understandable but slightly vague
- 1: Confusing, ambiguous, or grammatically broken

**Difficulty**: Is the difficulty appropriate for a study question?
- 5: Excellent difficulty — requires understanding, not just recall
- 3: Average — simple recall or overly broad
- 1: Trivial or impossibly hard

Return your evaluation as a JSON object:
{{"relevance": <1-5>, "clarity": <1-5>, "difficulty": <1-5>, "reasoning": "<brief explanation>"}}

Evaluation:"""


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

        prompt = QUESTION_GEN_PROMPT.format(count=count, context=context)
        response = Settings.llm.complete(prompt)

        questions = self._parse_response(response.text, chunks)
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
        Uses the same Settings.llm for evaluation.
        """
        logger.info("Scoring {} questions via LLM-as-Judge...", len(questions))

        for i, q in enumerate(questions):
            try:
                prompt = QUESTION_SCORE_PROMPT.format(
                    context=context, question=q.question
                )
                response = Settings.llm.complete(prompt)
                scores = self._parse_scores(response.text)
                q.scores = scores
                logger.debug(
                    "Q{}: relevance={}, clarity={}, difficulty={}, overall={}",
                    i + 1,
                    scores.relevance,
                    scores.clarity,
                    scores.difficulty,
                    scores.overall,
                )
            except Exception as e:
                logger.warning("Failed to score question {}: {}", i + 1, e)
                q.scores = QuestionScores()

    @staticmethod
    def _parse_scores(text: str) -> QuestionScores:
        """Parse LLM scoring response into QuestionScores."""
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("No JSON found in score response")
            return QuestionScores()

        try:
            data = json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse score JSON: {}", e)
            return QuestionScores()

        relevance = int(data.get("relevance", 0))
        clarity = int(data.get("clarity", 0))
        difficulty = int(data.get("difficulty", 0))
        # Overall = average of relevance + clarity (difficulty is informational)
        overall = round((relevance + clarity) / 2, 1) if (relevance and clarity) else 0.0

        return QuestionScores(
            relevance=relevance,
            clarity=clarity,
            difficulty=difficulty,
            overall=overall,
            reasoning=data.get("reasoning", ""),
        )

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
    # Response parsing
    # ============================================================
    @staticmethod
    def _parse_response(
        text: str, chunks: list[dict[str, Any]]
    ) -> list[GeneratedQuestion]:
        """Parse LLM response into GeneratedQuestion objects."""
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            logger.warning("Could not find JSON array in LLM response")
            return []

        try:
            items = json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response as JSON: {}", e)
            return []

        questions: list[GeneratedQuestion] = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict) or "question" not in item:
                continue
            # Map each question to its source chunk (round-robin if more questions than chunks)
            chunk_idx = idx % len(chunks) if chunks else 0
            source = chunks[chunk_idx] if chunks else {}
            source_meta = source.get("metadata", {})
            questions.append(GeneratedQuestion(
                question=item["question"],
                difficulty=item.get("difficulty", "medium"),
                question_type=item.get("type", "conceptual"),
                question_category=item.get("question_category", ""),
                source_chunk_id=source.get("id", ""),
                book_id=source_meta.get("book_id", ""),
                book_title=source_meta.get("book_title", ""),
                source_page=source_meta.get("page_idx", 0),
            ))
        return questions
