"""prompts — Centralised report generation prompt templates.

All LLM prompt templates used by the report module are defined here.
ReportGenerator imports from this file to keep logic and prompts separated.

Groups:
    - Session Report    → SESSION_REPORT_*  (used by ReportGenerator._build_prompt)
    - Global Report     → GLOBAL_REPORT_*   (used by generate_global_report)
"""


# ============================================================
# Session Report — per-session research report generation
# ============================================================
SESSION_REPORT_SYSTEM = """\
You are a research report writer. Generate a professional Markdown research \
report based on the following chat session data and evaluation metrics."""

SESSION_REPORT_TEMPLATE = """\
## Session: {session_title}
## Documents referenced: {book_titles}

---

### Conversation Transcript (most recent):

{transcript}

---

### Evaluation Metrics:

{eval_summary}{per_q_detail}

---

### Source Citations:

{source_summary}

---

## Instructions:

Generate a structured Markdown report with EXACTLY these 5 sections:

# Research Report: {session_title}

## 1. Executive Summary
Write a concise overview of what was discussed, key topics explored, and the \
overall quality of the research session. Include the number of questions asked \
({message_count} user messages) and documents referenced.

## 2. Key Findings
Extract and synthesize the most important findings and insights from the \
assistant's responses. Present as numbered bullet points with specific data \
points and conclusions drawn from the source documents.

## 3. Quality Assessment
Summarize the evaluation metrics:
- Overall faithfulness and relevancy scores (use the average scores provided)
- Question depth analysis (distribution of surface/understanding/synthesis questions)
- Specific areas where the RAG system performed well or could improve
If no evaluation data is available, state that the session has not been evaluated yet.

## 4. Source Analysis
Analyze the citation patterns:
- Which documents were most frequently cited
- Coverage breadth (how many unique sources were referenced)
- Any gaps in source coverage

## 5. Methodology
Describe the research methodology:
- RAG (Retrieval-Augmented Generation) pipeline used
- LLM model(s) involved
- Evaluation framework (5-dimensional: faithfulness, relevancy, correctness, \
context relevancy, answer relevancy)
- Question depth classification system (surface → understanding → synthesis)

Write in a professional, analytical tone. Use Markdown formatting (headers, \
bullet points, bold for emphasis). Keep the total report between 800-1500 words."""


# ============================================================
# Global Report — cross-session quality report (EC-T3-04)
# ============================================================
GLOBAL_REPORT_TEMPLATE = """\
Generate a comprehensive Global Quality Report summarizing RAG system performance.
Total evaluations analysed: {eval_count}
Filter applied: {quality_filter}
Status distribution: {status_counts}
Average scores: {avg_scores}

Include sections:
1. Executive Summary
2. Score Distribution Analysis
3. Strengths and Weaknesses
4. Recommendations for Improvement
5. Appendix: Detailed Metrics

Use Markdown formatting with clear headings."""
