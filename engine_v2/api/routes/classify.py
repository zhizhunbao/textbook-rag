"""classify routes — LLM-based book classification endpoint.

Endpoints:
    POST /engine/classify  — auto-classify book by title/filename

Ref: AQ-05 — LLM auto-classification for uploaded PDFs
Ref: llama_index.core.llms.llm.LLM.structured_predict — structured output
"""

from __future__ import annotations

from fastapi import APIRouter
from llama_index.core.prompts import PromptTemplate
from loguru import logger
from pydantic import BaseModel, Field, field_validator

# ============================================================
# Router
# ============================================================
router = APIRouter(tags=["classify"])

# ============================================================
# Classification prompt (PromptTemplate — structured_predict auto-appends schema)
# ============================================================
CLASSIFY_PROMPT_TMPL = PromptTemplate(
    "You are a librarian assistant. Given a document title (and optionally a filename), "
    "classify it into a category and suggest a subcategory.\n\n"
    "## Guidelines\n"
    "- The **category** should be a short, broad label that groups similar documents.\n"
    '  Examples: "textbook", "ecdev", "real_estate", "research_paper", "policy", '
    '"finance", "engineering", "medical", "legal", etc.\n'
    "  Use lowercase_snake_case. Keep it to 1-2 words max.\n"
    "- The **subcategory** should be a more specific tag within that category.\n"
    '  Use **Title Case** (capitalize each word, separated by spaces).\n'
    '  Examples: "Python", "Machine Learning", "Computer Vision", "Q4 2024 Report", '
    '"Market Analysis", "Reinforcement Learning", "Software Engineering", etc.\n'
    "  Do NOT use snake_case for subcategory.\n"
    "- The **confidence** should be a float 0.0\u20131.0 indicating your certainty.\n\n"
    "## Hints for common patterns\n"
    '- Academic/technical books (programming, math, CS, ML, etc.) \u2192 category "textbook"\n'
    "- Economic development reports, market updates, quarterly reviews, fund updates, "
    'documents with "Ed Update" \u2192 category "ecdev"\n'
    '- Real estate reports, property analysis, REIT materials \u2192 category "real_estate"\n'
    "- But you are NOT limited to these \u2014 use whatever category fits best.\n\n"
    "## Rules\n"
    "1. Keep category in lowercase_snake_case, max 2 words.\n"
    "2. Keep subcategory in Title Case.\n\n"
    "## Input\n"
    "Title: {title}\n"
    "Filename: {filename}"
)


# ============================================================
# Request / Response models
# ============================================================
class ClassifyRequest(BaseModel):
    title: str
    filename: str | None = None


class ClassifyResponse(BaseModel):
    """LLM classification result — also used as structured_predict output_cls."""

    category: str = Field(default="textbook", description="lowercase_snake_case category")
    subcategory: str = Field(default="", description="Title Case subcategory")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        """Sanitize to lowercase_snake_case."""
        return str(v).lower().strip().replace(" ", "_").replace("-", "_")

    @field_validator("subcategory", mode="before")
    @classmethod
    def normalize_subcategory(cls, v: str) -> str:
        """Normalize to Title Case, preserving acronyms."""
        return _to_title_case(str(v).strip())


# ============================================================
# Endpoints
# ============================================================
@router.post("/classify", response_model=ClassifyResponse)
async def classify_book(req: ClassifyRequest):
    """Classify a book into category + subcategory using LLM.

    Open-ended classification — the LLM can suggest any category,
    not limited to a fixed list. Uses structured_predict for robust,
    schema-validated output.
    """
    from llama_index.core.settings import Settings

    logger.info("Classifying: title='{}', filename='{}'", req.title, req.filename)

    try:
        result = Settings.llm.structured_predict(
            ClassifyResponse,
            CLASSIFY_PROMPT_TMPL,
            title=req.title,
            filename=req.filename or "(not provided)",
        )

        logger.info(
            "Classification result: category={}, subcategory={}, confidence={:.2f}",
            result.category, result.subcategory, result.confidence,
        )
        return result

    except Exception as exc:
        logger.warning("structured_predict classification failed: {}", exc)
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
