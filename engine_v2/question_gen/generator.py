"""QuestionGenerator — generate study questions from textbook chunks.

Aligns with llama_index.core.question_gen pattern.
Uses Settings.llm for generation, samples chunks from ChromaDB.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from typing import Any

import chromadb
from llama_index.core.settings import Settings

from engine_v2.settings import (
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    PAYLOAD_API_KEY,
    PAYLOAD_URL,
)

logger = logging.getLogger(__name__)

QUESTION_GEN_PROMPT = """You are a textbook question generator. Given the following textbook excerpt, generate {count} study questions that test understanding of the key concepts.

Context:
{context}

Generate exactly {count} questions in JSON array format:
[
  {{"question": "...", "difficulty": "easy|medium|hard", "type": "factual|conceptual|analytical"}}
]

Questions:"""


@dataclass
class GeneratedQuestion:
    """A single generated question."""

    question: str
    difficulty: str = "medium"
    question_type: str = "conceptual"
    source_chunk_id: str = ""
    book_id: str = ""


class QuestionGenerator:
    """Generate study questions from textbook chunks using LLM.

    Uses Settings.llm (configured globally) for generation.
    Samples chunks from ChromaDB for context.
    """

    def __init__(self, collection_name: str = CHROMA_COLLECTION) -> None:
        self._collection_name = collection_name

    def generate(
        self,
        book_id: str | None = None,
        count: int = 5,
        chunk_sample_size: int = 3,
    ) -> list[GeneratedQuestion]:
        """Generate questions from sampled textbook chunks.

        Args:
            book_id: Optional filter to a specific book.
            count: Number of questions to generate.
            chunk_sample_size: Number of chunks to sample as context.

        Returns:
            List of GeneratedQuestion.
        """
        chunks = self._sample_chunks(book_id, chunk_sample_size)
        if not chunks:
            logger.warning("No chunks found for question generation")
            return []

        context = "\n\n---\n\n".join(
            f"[Chunk {i+1}] {c['document']}" for i, c in enumerate(chunks)
        )

        prompt = QUESTION_GEN_PROMPT.format(count=count, context=context)
        response = Settings.llm.complete(prompt)

        questions = self._parse_response(response.text, chunks)
        logger.info("Generated %d questions", len(questions))
        return questions[:count]

    def _sample_chunks(
        self, book_id: str | None, n: int
    ) -> list[dict[str, Any]]:
        """Sample random chunks from ChromaDB."""
        client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name=self._collection_name)

        where = {"book_id": book_id} if book_id else None
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
    def _parse_response(
        text: str, chunks: list[dict[str, Any]]
    ) -> list[GeneratedQuestion]:
        """Parse LLM response into GeneratedQuestion objects."""
        # Extract JSON array from response
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            logger.warning("Could not find JSON array in LLM response")
            return []

        try:
            items = json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response as JSON: %s", e)
            return []

        questions = []
        for item in items:
            if not isinstance(item, dict) or "question" not in item:
                continue
            source_id = chunks[0]["id"] if chunks else ""
            source_meta = chunks[0].get("metadata", {}) if chunks else {}
            questions.append(GeneratedQuestion(
                question=item["question"],
                difficulty=item.get("difficulty", "medium"),
                question_type=item.get("type", "conceptual"),
                source_chunk_id=source_id,
                book_id=source_meta.get("book_id", ""),
            ))
        return questions
