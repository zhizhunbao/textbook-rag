"""consulting.helpers — Shared utilities for consulting routes.

Provides:
    _append_disclaimer()          — re-export from consulting.prompts
    _generate_no_retrieval_reply() — LLM fallback when no chunks retrieved
    _sse()                        — format Server-Sent Events

All prompt text is defined in consulting.prompts — this module only
contains runtime logic that uses those prompts.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from engine_v2.consulting.prompts import (
    append_disclaimer as _append_disclaimer,        # noqa: F401 — re-exported
    build_no_retrieval_prompt as _build_no_retrieval_prompt,
)


async def _generate_no_retrieval_reply(
    question: str,
    system_prompt: str,
    persona_name: str,
    model: str | None = None,
    provider: str | None = None,
) -> str:
    """Use the persona's LLM to dynamically generate a 'no results' message.

    Instead of hardcoding a static English fallback, we ask the LLM to produce
    a contextual reply that matches the persona's language, tone, and scope.
    Falls back to a minimal static string only if the LLM call itself fails.
    """
    from engine_v2.llms import resolve_llm

    no_retrieval_prompt = _build_no_retrieval_prompt(question, persona_name)
    try:
        llm = resolve_llm(model=model, provider=provider, streaming=False)
        from llama_index.core.llms import ChatMessage, MessageRole
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(ChatMessage(role=MessageRole.USER, content=no_retrieval_prompt))
        resp = llm.chat(messages)
        return str(resp).strip()
    except Exception as e:
        logger.warning("Failed to generate dynamic no-retrieval reply: {}", e)
        return (
            f"I couldn't find relevant information in the {persona_name} "
            "knowledge base for your question. "
            "Please try rephrasing or check if the relevant documents have been ingested."
        )


def _sse(event: str, data: dict[str, Any]) -> str:
    """Format SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
