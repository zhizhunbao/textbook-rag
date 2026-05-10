"""consulting.helpers — Shared utilities for consulting routes.

Provides:
    _append_disclaimer()          — re-export from consulting.prompts
    _normalize_citations()        — (Source N) → [N] bracket conversion
    _generate_no_retrieval_reply() — LLM fallback when no chunks retrieved
    _sse()                        — format Server-Sent Events

All prompt text is defined in consulting.prompts — this module only
contains runtime logic that uses those prompts.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from engine_v2.consulting.prompts import (
    append_disclaimer as _append_disclaimer,        # noqa: F401 — re-exported
    build_no_retrieval_prompt as _build_no_retrieval_prompt,
    build_small_talk_prompt as _build_small_talk_prompt,
)


# ── Small-talk / greeting patterns (skip RAG retrieval) ─────────────
_GREETING_EXACT: set[str] = {
    # Chinese
    "你好", "您好", "嗨", "哈喽", "早上好", "下午好", "晚上好",
    "你好呀", "在吗", "在不在", "你在吗", "早", "晚安",
    "谢谢", "谢谢你", "多谢", "感谢", "辛苦了", "好的",
    # English
    "hi", "hello", "hey", "yo", "sup", "hiya",
    "good morning", "good afternoon", "good evening", "good night",
    "thanks", "thank you", "thx", "ok", "okay", "bye", "goodbye",
    "how are you", "whats up", "what's up",
}


def is_small_talk(question: str) -> bool:
    """Return True if the question is a greeting / small-talk that should skip RAG.

    Only matches short, exact phrases — anything longer than 20 chars or
    containing question marks is assumed to be a real query.
    """
    q = question.strip().rstrip("!?！？。.~～").strip().lower()
    if len(q) > 30:
        return False
    return q in _GREETING_EXACT


def _normalize_citations(text: str) -> str:
    """Normalize parenthetical citation formats to [N] bracket format.

    LLMs sometimes ignore the bracket instruction and use:
        (Source 1)         → [1]
        (Sources 1, 2, 3) → [1] [2] [3]
        (Source 1, 3)      → [1] [3]

    This ensures the frontend answerBlocks parser (which only recognizes
    [N]) can always extract citation indices correctly.
    """
    if not text:
        return text

    def _expand_sources(m: re.Match) -> str:
        """Convert a (Source(s) N, M, ...) match to [N] [M] ..."""
        nums_str = m.group(1)
        nums = re.findall(r'\d+', nums_str)
        return ' '.join(f'[{n}]' for n in nums)

    # (Sources 1, 2, 3) or (Source 1, 3) — with optional "s" and comma-separated numbers
    text = re.sub(
        r'\(Sources?\s+([\d,\s]+)\)',
        _expand_sources,
        text,
        flags=re.IGNORECASE,
    )
    # Single (Source 1) without comma
    text = re.sub(
        r'\(Source\s+(\d+)\)',
        r'[\1]',
        text,
        flags=re.IGNORECASE,
    )
    return text


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
        return _strip_role_prefix(str(resp))
    except Exception as e:
        logger.warning("Failed to generate dynamic no-retrieval reply: {}", e)
        return (
            f"I couldn't find relevant information in the {persona_name} "
            "knowledge base for your question. "
            "Please try rephrasing or check if the relevant documents have been ingested."
        )


def _strip_role_prefix(text: str) -> str:
    """Strip 'assistant:' / 'Assistant:' prefix that some LLMs leak."""
    t = text.strip()
    if t.lower().startswith("assistant:"):
        t = t[len("assistant:"):].strip()
    return t


async def _generate_small_talk_reply(
    question: str,
    system_prompt: str,
    persona_name: str,
    model: str | None = None,
    provider: str | None = None,
) -> str:
    """Generate a natural greeting/small-talk response without RAG retrieval."""
    from engine_v2.llms import resolve_llm

    prompt = _build_small_talk_prompt(question, persona_name)
    try:
        llm = resolve_llm(model=model, provider=provider, streaming=False)
        from llama_index.core.llms import ChatMessage, MessageRole
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(ChatMessage(role=MessageRole.USER, content=prompt))
        resp = llm.chat(messages)
        return _strip_role_prefix(str(resp))
    except Exception as e:
        logger.warning("Failed to generate small-talk reply: {}", e)
        return "Hello! How can I help you today with questions about studying or immigrating to Canada?"


def _sse(event: str, data: dict[str, Any]) -> str:
    """Format SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
