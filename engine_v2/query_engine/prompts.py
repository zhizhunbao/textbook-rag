"""prompts — Centralised query engine prompt data and templates.

All chat-intent data and response templates used by the intent
classifier are defined here.

Groups:
    - CHAT_EXACT       → exact-match chat phrases (greetings, etc.)
    - CHAT_PATTERNS    → regex patterns for meta-questions / small talk
    - CHAT_RESPONSE_*  → language-specific chat response templates
"""

from __future__ import annotations

import re


# ============================================================
# Chat exact-match phrases — greetings, small talk, reactions
# ============================================================
CHAT_EXACT: set[str] = {
    # Chinese greetings & small talk
    "你好", "您好", "嗨", "哈喽", "早上好", "下午好", "晚上好",
    "早安", "午安", "晚安", "在吗", "在不在", "谢谢", "感谢",
    "再见", "拜拜", "好的", "嗯", "嗯嗯", "哦", "ok", "好",
    # English greetings & small talk
    "hi", "hello", "hey", "yo", "sup", "thanks", "thank you",
    "good morning", "good afternoon", "good evening", "good night",
    "bye", "goodbye", "see you", "ok", "okay", "yes", "no",
    "nice", "cool", "great", "awesome",
}


# ============================================================
# Chat regex patterns — meta-questions, reactions, emoji-only
# ============================================================
CHAT_PATTERNS: list[re.Pattern] = [
    # Meta: asking about the bot itself
    re.compile(r"你是(什么|谁|啥|哪个)", re.IGNORECASE),
    re.compile(r"你(叫|叫什么|的名字)", re.IGNORECASE),
    re.compile(r"(什么|哪个)(模型|model|AI|机器人)", re.IGNORECASE),
    re.compile(r"^(who|what)\s+(are|r)\s+(you|u)", re.IGNORECASE),
    re.compile(r"^what\s+(model|ai|llm|bot)", re.IGNORECASE),
    re.compile(r"^(are\s+you|r\s+u)\s+(a|an)\s+", re.IGNORECASE),
    # Small talk
    re.compile(r"^(how\s+are\s+you|how\s+r\s+u|how're\s+you)", re.IGNORECASE),
    re.compile(r"^(你怎么样|你好吗|吃了吗|忙不忙)", re.IGNORECASE),
    # Compliments / reactions (not questions)
    re.compile(r"^(哈哈|呵呵|嘿嘿|lol|haha|lmao)", re.IGNORECASE),
    # Single emoji or punctuation only
    # NOTE: Python `re` doesn't support \p{Emoji}; use explicit Unicode ranges
    re.compile(
        r"^[\s"
        r"\U0001F300-\U0001F9FF"   # Misc Symbols, Emoticons, Dingbats, etc.
        r"\u2600-\u27BF"           # Misc Symbols & Dingbats
        r"\u2300-\u23FF"           # Misc Technical
        r"\u2B50-\u2B55"           # Stars, circles
        r"\uFE00-\uFE0F"          # Variation Selectors
        r"\u200D"                  # Zero-Width Joiner (emoji sequences)
        r"!?！？。，、…"
        r"]+$",
        re.UNICODE,
    ),
    # Test / debug queries
    re.compile(r"^(test|testing|测试)$", re.IGNORECASE),
]


# ============================================================
# Chat response templates — language-specific
# ============================================================
CHAT_RESPONSE_ZH = "你好！我是教科书研究助手，有关于教科书内容的问题随时可以问我。"
CHAT_RESPONSE_EN = (
    "Hello! I'm a textbook research assistant. "
    "If you have specific questions about the textbook content, "
    "feel free to ask."
)

# Fallback for legacy imports
CHAT_RESPONSE_TEXT = CHAT_RESPONSE_EN


# ============================================================
# Question indicator keywords — used by intent classifier
# ============================================================
QUESTION_INDICATORS: list[str] = [
    "什么", "如何", "怎么", "为什么", "哪", "多少", "几",
    "what", "how", "why", "when", "where", "which", "explain",
    "describe", "compare", "define", "list",
    "?", "？",
]
