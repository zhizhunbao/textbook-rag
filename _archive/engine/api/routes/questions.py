"""POST /engine/questions — Auto-generate questions from book PDF via LLM.

Extracts a sample of chunks from the selected books, then asks the LLM
to generate study questions based on the content.
"""

from typing import Any

import json
import logging
import re
import sqlite3

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from engine.api.deps import get_rag_core
from engine.config import DATABASE_PATH, PAYLOAD_URL

logger = logging.getLogger(__name__)

router = APIRouter(tags=["questions"])

# ── Fallback prompt (used only when Payload CMS is unreachable) ──
_FALLBACK_SYSTEM_PROMPT = (
    "You are a study assistant that generates questions STRICTLY based on the "
    "textbook excerpts provided below. "
    "Every question MUST reference a specific concept from the excerpts. "
    "Do NOT generate generic questions. "
    "NEVER reference page numbers, chapter numbers, or section numbers in questions. "
    "Questions must be self-contained and answerable by searching for concepts. "
    "Generate exactly {count} questions. "
    "Return ONLY a JSON array. Each element: "
    '"question" (string), "book_title" (string), "topic_hint" (string). '
    "No markdown code blocks."
)

# In-memory prompt cache (populated on first call)
_cached_system_prompt: str | None = None


def _fetch_question_prompt() -> str:
    """Fetch the 'question-generation' system prompt from Payload CMS.
    
    Falls back to the built-in prompt if CMS is unreachable.
    """
    global _cached_system_prompt
    if _cached_system_prompt is not None:
        return _cached_system_prompt

    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/prompt-modes",
            params={"where[slug][equals]": "question-generation", "limit": 1},
            timeout=5.0,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if docs and docs[0].get("systemPrompt"):
            _cached_system_prompt = docs[0]["systemPrompt"]
            logger.info("Loaded question-generation prompt from Payload CMS")
            return _cached_system_prompt
    except Exception as e:
        logger.warning("Could not fetch prompt from Payload CMS: %s", e)

    _cached_system_prompt = _FALLBACK_SYSTEM_PROMPT
    return _cached_system_prompt


class GenerateQuestionsRequest(BaseModel):
    """Request body for question generation."""
    book_ids: list[str]     # engine text book_ids, e.g. ["bishop_prml", "james_ISLR"]
    count: int = 6          # how many questions to generate
    model: str | None = None


class GeneratedQuestion(BaseModel):
    """A single auto-generated question with metadata."""
    question: str
    book_id: str
    book_title: str
    topic_hint: str         # short label like "Chapter 3" or "BM25"


def _sample_chunks(book_ids: list[str], sample_size: int = 6) -> list[dict[str, Any]]:
    """Sample random chunks from the specified books in the SQLite DB.
    
    Args:
        book_ids: Engine text book_ids (e.g. ["bishop_prml"]).
                  These match `books.book_id` column in the engine DB.
        sample_size: Max number of chunks to sample.
    """
    db_path = str(DATABASE_PATH)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Build parameterized IN clause for the selected books
    placeholders = ",".join("?" for _ in book_ids)
    rows = conn.execute(
        f"""
        SELECT c.chunk_id, c.text, p.page_number,
               b.id AS engine_book_id, b.book_id AS book_dir_name,
               b.title AS book_title
        FROM chunks c
        JOIN books b ON c.book_id = b.id
        LEFT JOIN pages p ON c.primary_page_id = p.id
        WHERE b.book_id IN ({placeholders})
          AND length(c.text) > 120
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (*book_ids, sample_size),
    ).fetchall()
    conn.close()

    if not rows:
        return []

    return [dict(r) for r in rows]




def _extract_json_array(raw: str) -> list[dict[str, Any]]:
    """Robustly extract a JSON array from LLM output.
    
    Handles common issues:
    - Markdown code fences (```json ... ```)
    - Extra text before/after the JSON array
    - Trailing commas (best-effort)
    """
    text = raw.strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Find the first '[' and match to its closing ']'
    start = text.find("[")
    if start == -1:
        raise ValueError("No JSON array found in LLM output")

    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    candidate = text[start:end]
    return json.loads(candidate)


def _generate_questions_via_llm(
    chunks: list[dict[str, Any]],
    count: int,
    model: str,
    ollama_url: str,
) -> list[dict[str, Any]]:
    """Call LLM (Ollama or Azure OpenAI) to generate questions from sampled chunks."""
    from engine.rag.llm_client import chat as llm_chat

    # Build context from chunks
    context_parts = []
    for i, c in enumerate(chunks, 1):
        # Omit page numbers from context to prevent LLM from referencing them
        # in generated questions (RAG retrieval can't search by page number)
        header = f"[{i}] {c.get('book_title', '')}"
        text = c.get("text", "")[:400]
        context_parts.append(f"{header}\n{text}")
    context = "\n\n---\n\n".join(context_parts)

    # Fetch prompt from Payload CMS (cached after first call)
    prompt_template = _fetch_question_prompt()
    system_prompt = prompt_template.replace("{count}", str(count))

    user_content = f"Textbook excerpts:\n\n{context}"

    try:
        logger.info("Generating questions via llm_client, model=%s", model)
        content = llm_chat(
            model=model,
            system=system_prompt,
            user=user_content,
            timeout=60.0,
        )
        if content.startswith("[Generation error"):
            logger.error("LLM returned error: %s", content)
            return []
        questions = _extract_json_array(content)
        if isinstance(questions, list):
            return questions[:count]
    except Exception as e:
        logger.exception("LLM question generation failed (model=%s): %s", model, e)

    return []


@router.post("/questions")
def generate_questions(req: GenerateQuestionsRequest):
    """Generate study questions from book content using LLM."""
    core = get_rag_core()
    config = core._config

    model = req.model or config.default_model
    ollama_url = config.ollama_base_url

    # Sample chunks from requested books
    chunks = _sample_chunks(req.book_ids, sample_size=6)
    if not chunks:
        return {"questions": []}

    # Get title → book_id mapping for attaching correct IDs
    book_id_map: dict[str, str] = {}
    for c in chunks:
        title = c.get("book_title", "")
        bid = c.get("book_dir_name", "")
        if title and bid:
            book_id_map[title] = bid

    raw_questions = _generate_questions_via_llm(chunks, req.count, model, ollama_url)

    questions = []
    for q in raw_questions:
        if not isinstance(q, dict):
            logger.warning("Skipping non-dict question item: %s", type(q).__name__)
            continue
        title = q.get("book_title", "")
        questions.append({
            "question": q.get("question", ""),
            "book_id": book_id_map.get(title, req.book_ids[0] if req.book_ids else ""),
            "book_title": title,
            "topic_hint": q.get("topic_hint", ""),
        })

    # 自动保存到 Payload CMS / Auto-persist to Payload for analysis
    if questions:
        _persist_to_payload(questions, model)

    return {"questions": questions}


def _persist_to_payload(questions: list[dict[str, Any]], model: str) -> None:
    """Save generated questions to Payload CMS, then auto-score each one.

    Flow: create doc → score via LLM → PATCH scores back.
    """
    if not PAYLOAD_URL:
        return

    from engine.rag.llm_client import chat as llm_chat

    api_url = f"{PAYLOAD_URL}/api/questions"
    for q in questions:
        doc = {
            "question": q.get("question", ""),
            "bookId": q.get("book_id", ""),
            "bookTitle": q.get("book_title", ""),
            "topicHint": q.get("topic_hint", ""),
            "source": "ai",
            "likes": 0,
            "model": model,
        }
        try:
            resp = httpx.post(api_url, json=doc, timeout=5.0)
            if resp.status_code >= 400:
                logger.warning("Payload save failed (%s): %s", resp.status_code, resp.text[:200])
                continue

            # Auto-score the question / 自动评分
            doc_id = resp.json().get("doc", {}).get("id")
            if doc_id:
                scores = _score_question(q.get("question", ""), q.get("book_title", ""), model)
                if scores:
                    httpx.patch(
                        f"{api_url}/{doc_id}",
                        json=scores,
                        timeout=5.0,
                    )
        except Exception as e:
            logger.debug("Failed to persist/score question: %s", e)


_SCORE_SYSTEM_PROMPT = (
    "You are a question quality evaluator. "
    "Score the following study question on 3 dimensions (1-5 scale):\n"
    "- relevance: Is it based on specific textbook content? (1=generic, 5=very specific)\n"
    "- clarity: Is the question clearly written and unambiguous? (1=confusing, 5=crystal clear)\n"
    "- difficulty: How hard is it to answer? (1=trivial, 5=very challenging)\n\n"
    "Return ONLY a JSON object: {\"relevance\": N, \"clarity\": N, \"difficulty\": N}\n"
    "No explanation, no markdown."
)


def _score_question(question: str, book_title: str, model: str) -> dict[str, Any] | None:
    """Call LLM to auto-score a question on relevance, clarity, difficulty."""
    from engine.rag.llm_client import chat as llm_chat

    user_prompt = f"Book: {book_title}\nQuestion: {question}"
    try:
        raw = llm_chat(
            model=model,
            system=_SCORE_SYSTEM_PROMPT,
            user=user_prompt,
            timeout=15.0,
        )
        # Parse JSON from response
        data = json.loads(raw.strip().strip("`").replace("json\n", ""))
        rel = min(5, max(1, int(data.get("relevance", 3))))
        cla = min(5, max(1, int(data.get("clarity", 3))))
        dif = min(5, max(1, int(data.get("difficulty", 3))))
        overall = round((rel + cla) / 2, 1)
        logger.info("Scored question: rel=%d cla=%d dif=%d → overall=%.1f", rel, cla, dif, overall)
        return {
            "scoreRelevance": rel,
            "scoreClarity": cla,
            "scoreDifficulty": dif,
            "scoreOverall": overall,
        }
    except Exception as e:
        logger.debug("Auto-score failed: %s", e)
        return None

