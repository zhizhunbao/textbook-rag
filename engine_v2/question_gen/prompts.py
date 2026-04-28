"""prompts — Centralised question generation prompt templates.

All LLM prompt templates used by the question generation module
are defined here. The generator imports from this file to keep
logic and prompts separated.

Groups:
    - GEN_PROMPT_TMPL   → question generation from textbook chunks
    - SCORE_PROMPT_TMPL → LLM-as-Judge scoring (relevance, clarity, difficulty)
"""

from llama_index.core.prompts import PromptTemplate


# ============================================================
# Question generation prompt
# ============================================================
GEN_PROMPT_TMPL = PromptTemplate(
    "You are a textbook question generator. Given the following textbook excerpt, "
    "generate {count} study questions that test understanding of the key concepts.\n\n"
    "Context:\n{context}\n\n"
    "Generate exactly {count} questions.\n"
    'For each question, also provide a short "question_category" label that describes '
    "the topic/domain the question belongs to (e.g. Labour Market, Housing Starts, "
    "Inflation, Resale Market, or any other relevant topic label).\n\n"
    "Questions:"
)



# ============================================================
# Reference answer generation prompt (QD-05)
# ============================================================
REFANSWER_PROMPT_TMPL = PromptTemplate(
    "You are a textbook study assistant. Given the following textbook excerpt "
    "and a study question, provide a concise, accurate reference answer using "
    "ONLY information from the excerpt.\n\n"
    "## Source Context\n{context}\n\n"
    "## Question\n{question}\n\n"
    "Write a clear, factual answer in 2-4 sentences. Cite specific data when available.\n\n"
    "Answer:"
)


# ============================================================
# Question scoring prompt (LLM-as-Judge)
# ============================================================
SCORE_PROMPT_TMPL = PromptTemplate(
    "You are an expert evaluator for study questions generated from textbook content.\n\n"
    "Given a question and the source textbook excerpt it was generated from, "
    "evaluate the question on three dimensions.\n\n"
    "## Source Context\n{context}\n\n"
    "## Question to Evaluate\n{question}\n\n"
    "## Scoring Criteria (1-5 each)\n\n"
    "**Relevance**: Can this question be answered using ONLY the source context?\n"
    "- 5: Directly answerable from the context\n"
    "- 3: Partially answerable; requires some outside knowledge\n"
    "- 1: Cannot be answered from the context at all (hallucination)\n\n"
    "**Clarity**: Is the question clearly written and unambiguous?\n"
    "- 5: Crystal clear, single interpretation\n"
    "- 3: Understandable but slightly vague\n"
    "- 1: Confusing, ambiguous, or grammatically broken\n\n"
    "**Difficulty**: Is the difficulty appropriate for a study question?\n"
    "- 5: Excellent difficulty — requires understanding, not just recall\n"
    "- 3: Average — simple recall or overly broad\n"
    "- 1: Trivial or impossibly hard\n\n"
    "Evaluation:"
)
