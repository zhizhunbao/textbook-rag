"""suggestions — Rule-based improvement suggestions for evaluations.

Generates actionable recommendations based on evaluation dimension scores.
Pure rules — no LLM calls. Templates centralised in prompts registry.

Ref: Sprint EUX-T3-01 — Rule engine for low-score feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger


# ============================================================
# Data types
# ============================================================
@dataclass
class Suggestion:
    """A single improvement suggestion."""

    dimension: str
    severity: str  # 'high' | 'medium' | 'low' | 'info'
    message_en: str
    message_zh: str

    def to_dict(self) -> dict[str, str]:
        """Serialise for JSON persistence."""
        return {
            "dimension": self.dimension,
            "severity": self.severity,
            "message_en": self.message_en,
            "message_zh": self.message_zh,
        }


# ============================================================
# Severity ordering (for sort)
# ============================================================
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


# ============================================================
# Rule definitions
# ============================================================
# Each rule: (field, operator, threshold, severity, dimension, en, zh)
SUGGESTION_RULES: list[dict[str, Any]] = [
    {
        "field": "relevancy",
        "op": "<",
        "threshold": 0.3,
        "severity": "high",
        "dimension": "source_relevancy",
        "message_en": (
            "Retrieved sources don't match the question. "
            "Try more specific keywords or rephrase your query."
        ),
        "message_zh": (
            "检索来源与问题不匹配。"
            "建议：使用更具体的关键词或重新措辞问题。"
        ),
    },
    {
        "field": "faithfulness",
        "op": "<",
        "threshold": 0.5,
        "severity": "high",
        "dimension": "faithfulness",
        "message_en": (
            "Hallucination risk detected — the answer may contain "
            "information not grounded in sources. Narrow your question scope."
        ),
        "message_zh": (
            "检测到幻觉风险 — 回答可能包含来源中不存在的信息。"
            "建议：缩小提问范围，聚焦单一主题。"
        ),
    },
    {
        "field": "answerRelevancy",
        "op": "<",
        "threshold": 0.5,
        "severity": "medium",
        "dimension": "answer_relevancy",
        "message_en": (
            "The answer drifts from the question. "
            "Rephrase to focus on a single topic."
        ),
        "message_zh": (
            "回答偏离了问题。"
            "建议：重新措辞，聚焦单一主题。"
        ),
    },
    {
        "field": "contextRelevancy",
        "op": "<",
        "threshold": 0.3,
        "severity": "medium",
        "dimension": "context_relevancy",
        "message_en": (
            "Retrieved chunks aren't relevant. "
            "The knowledge base may lack coverage for this topic."
        ),
        "message_zh": (
            "检索到的文档与问题关联度低。"
            "可能文档库中缺少该主题的相关内容。"
        ),
    },
    {
        "field": "questionDepth",
        "op": "==",
        "threshold": "surface",
        "severity": "low",
        "dimension": "question_depth",
        "message_en": (
            "This is a surface-level question. "
            "Try deeper questions: compare, analyze, or evaluate."
        ),
        "message_zh": (
            "这是一个浅层记忆性问题。"
            "建议：尝试对比、分析或评价类的深层问题。"
        ),
    },
    {
        "field": "completeness",
        "op": "<",
        "threshold": 0.5,
        "severity": "medium",
        "dimension": "completeness",
        "message_en": (
            "The answer is incomplete. "
            "Try breaking your question into sub-questions."
        ),
        "message_zh": (
            "回答不够完整。"
            "建议：将问题拆分为多个子问题分别提问。"
        ),
    },
    {
        "field": "overallScore",
        "op": ">=",
        "threshold": 0.85,
        "severity": "info",
        "dimension": "overall",
        "message_en": (
            "High-quality answer! Consider adding this to your "
            "Golden Dataset for retrieval benchmarking."
        ),
        "message_zh": (
            "高质量回答！建议将此问答对加入 Golden Dataset，"
            "用于检索质量基准测试。"
        ),
    },
]


# ============================================================
# Rule engine
# ============================================================
MAX_SUGGESTIONS = 3


def _check_rule(rule: dict[str, Any], value: Any) -> bool:
    """Check if a single rule triggers for the given value."""
    if value is None:
        return False

    op = rule["op"]
    threshold = rule["threshold"]

    if op == "<":
        return float(value) < float(threshold)
    if op == "<=":
        return float(value) <= float(threshold)
    if op == ">":
        return float(value) > float(threshold)
    if op == ">=":
        return float(value) >= float(threshold)
    if op == "==":
        return str(value).lower() == str(threshold).lower()
    return False


def generate_suggestions(
    eval_data: dict[str, Any],
    max_count: int = MAX_SUGGESTIONS,
) -> list[Suggestion]:
    """Generate improvement suggestions from evaluation scores.

    Args:
        eval_data: Dictionary with evaluation field values
                   (keys: faithfulness, relevancy, contextRelevancy, etc.)
        max_count: Maximum suggestions to return (sorted by severity).

    Returns:
        List of Suggestion, sorted by severity (high first), capped at max_count.
    """
    triggered: list[Suggestion] = []

    for rule in SUGGESTION_RULES:
        field_name = rule["field"]
        value = eval_data.get(field_name)

        if _check_rule(rule, value):
            triggered.append(Suggestion(
                dimension=rule["dimension"],
                severity=rule["severity"],
                message_en=rule["message_en"],
                message_zh=rule["message_zh"],
            ))

    # Sort by severity (high → medium → low → info)
    triggered.sort(key=lambda s: _SEVERITY_ORDER.get(s.severity, 99))

    result = triggered[:max_count]
    if result:
        logger.debug(
            "Generated {} suggestions (top {}): {}",
            len(triggered), len(result),
            [s.dimension for s in result],
        )

    return result
