"""GenerationEngine — builds prompts and calls Ollama.

Extracted and generalised from v1.0 generation_service.py.
Adds: prompt template support, custom system_prompt override.
"""

from __future__ import annotations

import json

import httpx

from backend.app.core.config import (
    PROMPT_ACADEMIC,
    PROMPT_CONCISE,
    PROMPT_DEFAULT,
    PROMPT_DETAILED,
    QueryConfig,
    RAGConfig,
)
from backend.app.core.types import ChunkHit

# ---------------------------------------------------------------------------
# Built-in prompt templates
# ---------------------------------------------------------------------------
_TEMPLATES: dict[str, str] = {
    PROMPT_DEFAULT: (
        "You are a knowledgeable assistant. Answer the user's question based ONLY on "
        "the provided context. Cite sources using [N] notation. "
        "If the context does not contain sufficient information, say so honestly."
    ),
    PROMPT_CONCISE: (
        "You are a concise assistant. Give a short, direct answer using ONLY the provided "
        "context. Use [N] to cite sources. Maximum 3 sentences."
    ),
    PROMPT_DETAILED: (
        "You are a thorough assistant. Provide a comprehensive answer with examples where "
        "applicable, using ONLY the provided context. Cite every claim with [N] notation. "
        "Structure your response with clear paragraphs."
    ),
    PROMPT_ACADEMIC: (
        "You are an academic writing assistant. Answer in formal academic style using ONLY "
        "the provided context. Cite sources as [N]. Avoid personal pronouns. "
        "Maintain a neutral, objective tone."
    ),
}

BUILTIN_TEMPLATES = [
    {"id": k, "name": k.capitalize(), "description": v[:80] + "..."}
    for k, v in _TEMPLATES.items()
]


class GenerationEngine:
    """Builds the prompt and calls Ollama to generate an answer."""

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
        response = self._call_ollama(model, system_prompt, user_prompt)
        return response

    def _resolve_system_prompt(self, config: QueryConfig) -> str:
        """Return the system prompt: custom override → template → default."""
        if config.custom_system_prompt:
            return config.custom_system_prompt
        return _TEMPLATES.get(config.prompt_template, _TEMPLATES[PROMPT_DEFAULT])

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
            header = " | ".join(header_parts)
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n---\n\n".join(parts)

    def _call_ollama(self, model: str, system: str, user: str) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        url = f"{self._config.ollama_base_url}/api/chat"
        try:
            resp = httpx.post(url, json=payload, timeout=120.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            return f"[Generation error: {e}]"
        except (json.JSONDecodeError, KeyError):
            return "[Generation error: unexpected Ollama response format]"

    @staticmethod
    def list_templates() -> list[dict]:
        return BUILTIN_TEMPLATES
