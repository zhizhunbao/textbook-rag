"""GenerationEngine — builds prompts and calls Ollama.

Extracted and generalised from v1.0 generation_service.py.
Adds: prompt template support, custom system_prompt override.
"""

from __future__ import annotations

import json

import httpx

from engine.rag.config import (
    QueryConfig,
    RAGConfig,
)
from engine.rag.types import ChunkHit

# Templates have been moved to Payload CMS Database Seed
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
            header = " | ".join(header_parts)
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n---\n\n".join(parts)

    def _call_ollama(self, model: str, system: str, user: str) -> str:
        # 检测是否为"思考型"模型，如果是则禁用思考链以加速响应
        # Detect thinking-capable models and disable CoT for faster responses
        is_thinking_model = any(
            tag in model.lower()
            for tag in ("qwen3", "qwen3.5", "deepseek-r1", "qwq")
        )

        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }

        # 禁用思考链：放在请求顶层 / Disable CoT: must be at top level
        if is_thinking_model:
            payload["think"] = False

        url = f"{self._config.ollama_base_url}/api/chat"
        try:
            resp = httpx.post(url, json=payload, timeout=180.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            return f"[Generation error: {e}]"
        except (json.JSONDecodeError, KeyError):
            return "[Generation error: unexpected Ollama response format]"

