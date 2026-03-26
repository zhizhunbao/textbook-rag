"""Generation service - call Ollama to produce an answer from retrieved context."""

from __future__ import annotations

import re
from typing import Any

import ollama as _ollama

from backend.app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from backend.app.schemas.query import ModelInfo

_SYSTEM_PROMPT = (
    "You are a knowledgeable teaching assistant for a textbook search system.\n"
    "Rules:\n"
    "1. Answer the user's question using ONLY the provided textbook excerpts.\n"
    "2. Use inline citations like [1], [2] etc. to reference the numbered context excerpts.\n"
    "   Place them right after the relevant sentence, e.g. 'Binary search runs in O(log n) [3].'\n"
    "3. Structure your answer in an IELTS-essay style:\n"
    "   - Start each paragraph with a **bold topic sentence** that states the main point.\n"
    "   - Follow with supporting details and evidence from the excerpts.\n"
    "   - Use clear paragraph breaks between distinct ideas.\n"
    "4. Use Markdown formatting: bold, bullet lists, code blocks as appropriate.\n"
    "5. If the provided context is insufficient or irrelevant to the question, say so honestly.\n"
    "   Do NOT make up information that is not in the provided excerpts.\n"
    "6. Always reply in the SAME language the user used to ask the question.\n"
    "7. Keep answers concise but thorough.\n"
    "8. Do NOT add a 'References' or 'Sources' section at the end. "
    "The system will display references separately. Only use inline [N] citations in your answer."
)


def generate(
    question: str,
    context_chunks: list[dict],
    *,
    active_book_title: str | None = None,
    model: str | None = None,
) -> str:
    """Build a RAG prompt from *context_chunks* and call Ollama."""
    messages = build_messages(
        question,
        context_chunks,
        active_book_title=active_book_title,
    )
    return generate_from_messages(messages, model=model, max_citation=len(context_chunks))


def build_messages(
    question: str,
    context_chunks: list[dict],
    *,
    active_book_title: str | None = None,
) -> list[dict[str, str]]:
    context_block = _build_context(context_chunks)

    book_hint = ""
    if active_book_title:
        book_hint = f"The user is currently reading **{active_book_title}**.\n\n"

    citation_hint = ""
    if context_chunks:
        citation_hint = (
            f"You may only use citation numbers [1] through [{len(context_chunks)}]. "
            "Do not cite any number outside that range.\n\n"
        )

    user_msg = (
        f"{book_hint}"
        f"{citation_hint}"
        f"## Context\n\n{context_block}\n\n"
        f"## Question\n\n{question}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


def generate_from_messages(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_citation: int,
) -> str:
    """Call Ollama with prebuilt messages and sanitize returned citations."""

    try:
        client = _ollama.Client(host=OLLAMA_BASE_URL)
        resp = client.chat(
            model=model or OLLAMA_MODEL,
            messages=messages,
        )
        return _sanitize_citations(resp["message"]["content"], max_citation)
    except Exception as exc:
        raise RuntimeError(
            f"Ollama generation failed ({OLLAMA_BASE_URL}, model={model or OLLAMA_MODEL}): {exc}"
        ) from exc


def list_available_models() -> list[ModelInfo]:
    """Return locally available Ollama models with the configured default marked."""

    try:
        client = _ollama.Client(host=OLLAMA_BASE_URL)
        response = client.list()
    except Exception as exc:
        raise RuntimeError(
            f"Ollama model listing failed ({OLLAMA_BASE_URL}): {exc}"
        ) from exc

    entries = response.get("models", [])
    models: list[ModelInfo] = []
    for entry in entries:
        name = entry.get("model") or entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        models.append(ModelInfo(name=name, is_default=name == OLLAMA_MODEL))

    if not any(model.name == OLLAMA_MODEL for model in models):
        models.insert(0, ModelInfo(name=OLLAMA_MODEL, is_default=True))

    return models


def get_effective_model_name(model: str | None = None) -> str:
    return model or OLLAMA_MODEL


def build_generation_trace(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    system_prompt = next(
        (message["content"] for message in messages if message["role"] == "system"),
        "",
    )
    user_prompt = next(
        (message["content"] for message in messages if message["role"] == "user"),
        "",
    )
    return {
        "model": get_effective_model_name(model),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def _sanitize_citations(text: str, max_citation: int) -> str:
    """Remove citation markers that do not map to the retrieved source list."""

    def replace(match: re.Match[str]) -> str:
        citation_num = int(match.group(1))
        if 1 <= citation_num <= max_citation:
            return match.group(0)
        return ""

    cleaned = re.sub(r"\[(\d+)\]", replace, text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _build_context(chunks: list[dict]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        book = chunk.get("book_title", "")
        chapter = chunk.get("chapter_title", "")
        locs = chunk.get("source_locators", [])
        page = (locs[0].get("page_number", 0) + 1) if locs else ""
        header = f"[{i}] {book}"
        if chapter:
            header += f" - {chapter}"
        if page:
            header += f" (p.{page})"
        parts.append(f"{header}\n{chunk.get('text', '')}")
    return "\n\n---\n\n".join(parts)
