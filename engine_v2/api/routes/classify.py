"""classify routes — LLM-based book classification endpoint.

Endpoints:
    POST /engine/classify  — auto-classify book by title/filename

Ref: AQ-05 — LLM auto-classification for uploaded PDFs
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

# ============================================================
# Router
# ============================================================
router = APIRouter(tags=["classify"])

# ============================================================
# Classification prompt (open-ended — no fixed category list)
# ============================================================
CLASSIFY_PROMPT = """\
You are a librarian assistant. Given a document title (and optionally a filename),
classify it into a category and suggest a subcategory.

## Guidelines
- The **category** should be a short, broad label that groups similar documents.
  Examples: "textbook", "ecdev", "real_estate", "research_paper", "policy", \
"finance", "engineering", "medical", "legal", etc.
  Use lowercase_snake_case. Keep it to 1-2 words max.
- The **subcategory** should be a more specific tag within that category.
  Use **Title Case** (capitalize each word, separated by spaces).
  Examples: "Python", "Machine Learning", "Computer Vision", "Q4 2024 Report", \
"Market Analysis", "Reinforcement Learning", "Software Engineering", etc.
  Do NOT use snake_case for subcategory.
- The **confidence** should be a float 0.0–1.0 indicating your certainty.

## Hints for common patterns
- Academic/technical books (programming, math, CS, ML, etc.) → category "textbook"
- Economic development reports, market updates, quarterly reviews, fund updates, \
documents with "Ed Update" → category "ecdev"
- Real estate reports, property analysis, REIT materials → category "real_estate"
- But you are NOT limited to these — use whatever category fits best.

## Rules
1. Return ONLY valid JSON — no markdown, no explanation.
2. Keep category in lowercase_snake_case, max 2 words.
3. Keep subcategory in Title Case (e.g. "Machine Learning", NOT "machine_learning").

## Input
Title: {title}
Filename: {filename}

## Output format
{{"category": "...", "subcategory": "...", "confidence": 0.0}}
"""


# ============================================================
# Request / Response models
# ============================================================
class ClassifyRequest(BaseModel):
    title: str
    filename: str | None = None


class ClassifyResponse(BaseModel):
    category: str
    subcategory: str
    confidence: float


# ============================================================
# Endpoints
# ============================================================
@router.post("/classify", response_model=ClassifyResponse)
async def classify_book(req: ClassifyRequest):
    """Classify a book into category + subcategory using LLM.

    Open-ended classification — the LLM can suggest any category,
    not limited to a fixed list. The frontend shows the suggestion
    in a combobox where users can accept, modify, or pick from
    existing categories.
    """
    from llama_index.core.settings import Settings

    prompt = CLASSIFY_PROMPT.format(
        title=req.title,
        filename=req.filename or "(not provided)",
    )

    logger.info("Classifying: title='{}', filename='{}'", req.title, req.filename)

    raw_text = ""
    try:
        llm = Settings.llm
        response = llm.complete(prompt)
        raw_text = response.text.strip()

        # Strip markdown code fences if LLM wraps the JSON
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = [ln for ln in lines if not ln.startswith("```")]
            raw_text = "\n".join(lines).strip()

        result = json.loads(raw_text)

        category = str(result.get("category", "textbook")).lower().strip()
        subcategory = str(result.get("subcategory", "")).strip()
        confidence = float(result.get("confidence", 0.5))

        # Sanitize category to lowercase_snake_case
        category = category.replace(" ", "_").replace("-", "_")

        # Normalize subcategory to Title Case
        subcategory = _to_title_case(subcategory)

        logger.info(
            "Classification result: category={}, subcategory={}, confidence={:.2f}",
            category, subcategory, confidence,
        )

        return ClassifyResponse(
            category=category,
            subcategory=subcategory,
            confidence=confidence,
        )

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("LLM classification parse failed: {} — raw: {}", exc, raw_text)
        return _heuristic_classify(req.title, req.filename)

    except Exception as exc:
        logger.error("LLM classification failed: {}", exc)
        return _heuristic_classify(req.title, req.filename)


# ============================================================
# Subcategory normalizer
# ============================================================
def _to_title_case(s: str) -> str:
    """Convert snake_case or raw string to Title Case.

    'machine_vision'  → 'Machine Vision'
    'NLP'             → 'NLP'  (all-caps preserved)
    'q4 2024 report'  → 'Q4 2024 Report'
    """
    if not s:
        return s
    # Replace underscores/hyphens with spaces first
    normalized = s.replace("_", " ").replace("-", " ")
    # Title-case each word, but preserve fully uppercase tokens (e.g. NLP, API)
    words = []
    for w in normalized.split():
        if w.isupper() and len(w) > 1:
            words.append(w)          # keep acronyms as-is
        else:
            words.append(w.capitalize())
    return " ".join(words)


# ============================================================
# Heuristic fallback
# ============================================================
def _heuristic_classify(title: str, filename: str | None) -> ClassifyResponse:
    """Rule-based fallback when LLM is unavailable.

    Checks title keywords to determine category. Not perfect,
    but provides a reasonable default when the LLM call fails.
    """
    text = f"{title} {filename or ''}".lower()

    # EC Dev indicators
    ecdev_keywords = [
        "ed update", "market update", "quarterly", "q1", "q2", "q3", "q4",
        "fund", "investment", "economic", "oreb", "policy", "development report",
    ]
    if any(kw in text for kw in ecdev_keywords):
        return ClassifyResponse(category="ecdev", subcategory="Report", confidence=0.6)

    # Real estate indicators
    re_keywords = [
        "real estate", "property", "housing", "reit", "mortgage", "rental",
    ]
    if any(kw in text for kw in re_keywords):
        return ClassifyResponse(
            category="real_estate", subcategory="Market Analysis", confidence=0.6,
        )

    # Default: textbook
    return ClassifyResponse(category="textbook", subcategory="", confidence=0.4)
