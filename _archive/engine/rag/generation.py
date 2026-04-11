"""GenerationEngine — builds prompts and calls LLM (Ollama / Azure OpenAI).

Extracted and generalised from v1.0 generation_service.py.
v2.1: 统一使用 llm_client，自动路由到 Ollama 或 Azure OpenAI。
"""

from __future__ import annotations

from engine.rag.config import (
    QueryConfig,
    RAGConfig,
)
from engine.rag.llm_client import chat as llm_chat
from engine.rag.llm_client import chat_stream as llm_chat_stream
from engine.rag.types import ChunkHit


class GenerationEngine:
    """Builds the prompt and calls LLM to generate an answer."""

    def __init__(self, config: RAGConfig) -> None:
        self._config = config

    def generate(
        self,
        question: str,
        chunks: list[ChunkHit],
        config: QueryConfig,
    ) -> str:
        """Generate an answer from retrieved chunks.

        Args:
            question: User question.
            chunks:   Top-k retrieved chunks (used as context).
            config:   Per-query config (model, prompt_template, custom_system_prompt).

        Returns:
            Raw answer string (may contain [N] citation markers).
        """
        system_prompt = self._resolve_system_prompt(config)
        context = self._build_context(chunks)
        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer (cite sources as [N]):"
        )

        model = config.model or self._config.default_model
        return llm_chat(
            model=model,
            system=system_prompt,
            user=user_prompt,
            provider=config.provider,
        )

    def generate_stream(
        self,
        question: str,
        chunks: list[ChunkHit],
        config: QueryConfig,
    ):
        """Yield tokens from LLM as a generator (streaming).

        Same prompt construction as generate(), but yields tokens
        as they arrive instead of blocking for the full response.
        """
        system_prompt = self._resolve_system_prompt(config)
        context = self._build_context(chunks)
        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer (cite sources as [N]):"
        )

        model = config.model or self._config.default_model
        yield from llm_chat_stream(
            model=model,
            system=system_prompt,
            user=user_prompt,
            provider=config.provider,
        )

    def _resolve_system_prompt(self, config: QueryConfig) -> str:
        """Return the system prompt: custom override → fallback default."""
        if config.custom_system_prompt:
            return config.custom_system_prompt
        return (
            "You are a knowledgeable assistant. Answer the user's question based ONLY on "
            "the provided context. Cite sources using [N] notation. "
            "If the context does not contain sufficient information, say so honestly."
        )

    def _build_context(self, chunks: list[ChunkHit]) -> str:
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            header_parts = [f"[{i}]"]
            if chunk.book_title:
                header_parts.append(chunk.book_title)
            if chunk.chapter_title:
                header_parts.append(chunk.chapter_title)
            if chunk.primary_page_number is not None:
                header_parts.append(f"p.{chunk.primary_page_number}")
            # Tag content type so LLM knows what kind of content this is
            if chunk.text_level == 1:
                header_parts.append("(heading)")
            elif chunk.content_type and chunk.content_type != "text":
                header_parts.append(f"({chunk.content_type})")
            header = " | ".join(header_parts)
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n---\n\n".join(parts)

