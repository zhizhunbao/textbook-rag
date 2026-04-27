"""intent — Lightweight intent classifier for query routing.

Classifies user queries into two categories:
    - CHAT: casual greetings, meta-questions, or off-topic chat
    - RAG:  knowledge questions that should go through retrieval + synthesis

Uses keyword matching + heuristics (no LLM call) for near-zero latency.
Called by api/routes/query.py BEFORE the RAG pipeline.

Ref: Intent classification — rule-based approach for low-latency routing
"""

from __future__ import annotations

import re

from loguru import logger

from engine_v2.query_engine.prompts import (
    CHAT_EXACT,
    CHAT_PATTERNS,
    CHAT_RESPONSE_EN,
    CHAT_RESPONSE_ZH,
    QUESTION_INDICATORS,
)


# ============================================================
# Classifier
# ============================================================
def is_chat_query(question: str) -> bool:
    """Classify whether a query is casual chat (True) or a RAG question (False).

    Heuristics:
        1. Exact match against known chat phrases.
        2. Regex match against meta-question / small-talk patterns.
        3. Very short queries (≤ 3 chars) with no question indicators → chat.

    Returns:
        True if the query should bypass RAG and get a direct chat response.
        False if the query should go through the full RAG pipeline.
    """
    # Normalize: strip whitespace + common punctuation
    q = question.strip()
    q_clean = re.sub(r"[!?！？。，、~～\s]+$", "", q).strip()
    q_lower = q_clean.lower()

    # 1. Exact match
    if q_lower in CHAT_EXACT:
        logger.info("Intent: CHAT (exact match: '{}')", q_lower)
        return True

    # 2. Regex patterns
    for pattern in CHAT_PATTERNS:
        if pattern.search(q_clean):
            logger.info("Intent: CHAT (pattern match: '{}')", q_clean[:40])
            return True

    # 3. Very short query without question words → likely chat
    # But if it contains textbook/tech keywords, let it through
    if len(q_clean) <= 3 and not _has_question_indicator(q_clean):
        logger.info("Intent: CHAT (too short: '{}')", q_clean)
        return True

    logger.debug("Intent: RAG ('{}')", q[:50])
    return False


def _has_question_indicator(text: str) -> bool:
    """Check if text contains question indicators suggesting a knowledge query."""
    text_lower = text.lower()
    return any(ind in text_lower for ind in QUESTION_INDICATORS)


# ============================================================
# Chat response — language-aware
# ============================================================
def _is_chinese(text: str) -> bool:
    """Return True if the majority of non-space chars are CJK."""
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    return cjk > len(text.strip()) * 0.3


def get_chat_response(question: str) -> str:
    """Return a chat greeting in the same language as the user's query."""
    return CHAT_RESPONSE_ZH if _is_chinese(question) else CHAT_RESPONSE_EN


# Keep a default for any legacy imports
CHAT_RESPONSE_TEXT = CHAT_RESPONSE_EN

