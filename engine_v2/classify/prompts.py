"""classify.prompts — Centralised classification prompt templates.

All LLM prompt templates used by the classify route are defined here.
The route imports from this file to keep logic and prompts separated.
"""

from llama_index.core.prompts import PromptTemplate


# ============================================================
# Book classification prompt
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
