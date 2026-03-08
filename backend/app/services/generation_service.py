"""Generation service — call Ollama to produce an answer from retrieved context."""

from __future__ import annotations

import ollama as _ollama

from backend.app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

_SYSTEM_PROMPT = (
    "You are a knowledgeable teaching assistant for a textbook search system.\n"
    "Rules:\n"
    "1. Answer the user's question using ONLY the provided textbook excerpts.\n"
    "2. Use inline citations like [1], [2] etc. to reference the numbered context excerpts.\n"
    "   Place them right after the relevant sentence, e.g. 'Binary search runs in O(log n) [3].'\n"
    "3. Use Markdown formatting: headings, bold, bullet lists, code blocks as appropriate.\n"
    "4. If the provided context is insufficient or irrelevant to the question, say so honestly.\n"
    "   Do NOT make up information that is not in the provided excerpts.\n"
    "5. Always reply in the SAME language the user used to ask the question.\n"
    "6. Keep answers concise but thorough.\n"
    "7. Do NOT add a 'References' or 'Sources' section at the end. "
    "The system will display references separately. Only use inline [N] citations in your answer."
)


def generate(question: str, context_chunks: list[dict], *, active_book_title: str | None = None) -> str:
    """Build a RAG prompt from *context_chunks* and call Ollama.

    Returns the generated answer text.  Raises ``RuntimeError`` when Ollama
    is unreachable.
    """
    context_block = _build_context(context_chunks)

    book_hint = ""
    if active_book_title:
        book_hint = f"The user is currently reading **{active_book_title}**.\n\n"

    user_msg = (
        f"{book_hint}"
        f"## Context\n\n{context_block}\n\n"
        f"## Question\n\n{question}"
    )

    try:
        client = _ollama.Client(host=OLLAMA_BASE_URL)
        resp = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        return resp["message"]["content"]
    except Exception as exc:
        raise RuntimeError(
            f"Ollama generation failed ({OLLAMA_BASE_URL}, model={OLLAMA_MODEL}): {exc}"
        ) from exc


def _build_context(chunks: list[dict]) -> str:
    parts: list[str] = []
    for i, c in enumerate(chunks, 1):
        book = c.get('book_title', '')
        chapter = c.get('chapter_title', '')
        locs = c.get('source_locators', [])
        page = (locs[0].get('page_number', 0) + 1) if locs else ''
        header = f"[{i}] {book}"
        if chapter:
            header += f" — {chapter}"
        if page:
            header += f" (p.{page})"
        parts.append(f"{header}\n{c.get('text', '')}")
    return "\n\n---\n\n".join(parts)
