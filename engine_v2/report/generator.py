"""generator — Report generation from chat history + evaluation data.

Responsibilities:
    - Collect chat messages from a Payload ChatSession
    - Collect evaluation scores from Payload Evaluations
    - Build a structured prompt with conversation + eval data
    - Call LLM to generate a 5-section Markdown report
    - Write the report back to Payload Reports collection

Ref: llama_index — LLM completion via Settings singleton
"""

from __future__ import annotations


from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from engine_v2.settings import PAYLOAD_URL, PAYLOAD_ADMIN_EMAIL, PAYLOAD_ADMIN_PASSWORD

# ============================================================
# Data models
# ============================================================

@dataclass
class ChatMessage:
    """A single chat message extracted from Payload."""

    role: str
    content: str
    sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class EvalScore:
    """Evaluation scores for a single Q&A pair."""

    query: str
    faithfulness: float | None = None
    relevancy: float | None = None
    correctness: float | None = None
    context_relevancy: float | None = None
    answer_relevancy: float | None = None
    question_depth: str | None = None
    question_depth_score: float | None = None
    feedback: dict[str, Any] | None = None


@dataclass
class ReportData:
    """Aggregated data for report generation."""

    session_title: str
    messages: list[ChatMessage]
    evaluations: list[EvalScore]
    book_titles: list[str]
    avg_scores: dict[str, float]
    depth_distribution: dict[str, int]
    source_stats: dict[str, int]


# ============================================================
# Payload auth
# ============================================================
_payload_token: str | None = None


async def _get_payload_token() -> str:
    """Authenticate with Payload CMS and cache the JWT token.

    Uses PAYLOAD_ADMIN_EMAIL / PAYLOAD_ADMIN_PASSWORD from settings.
    Token is cached module-level to avoid re-login on every request.
    """
    global _payload_token
    if _payload_token:
        return _payload_token

    if not PAYLOAD_ADMIN_EMAIL or not PAYLOAD_ADMIN_PASSWORD:
        raise RuntimeError(
            "PAYLOAD_ADMIN_EMAIL and PAYLOAD_ADMIN_PASSWORD must be set in .env "
            "for the engine to authenticate with Payload CMS."
        )

    url = f"{PAYLOAD_URL}/api/users/login"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json={
            "email": PAYLOAD_ADMIN_EMAIL,
            "password": PAYLOAD_ADMIN_PASSWORD,
        })
        resp.raise_for_status()
        data = resp.json()

    _payload_token = data.get("token")
    if not _payload_token:
        raise RuntimeError("Payload login succeeded but no token returned")

    logger.info("Report module authenticated with Payload CMS as {}", PAYLOAD_ADMIN_EMAIL)
    return _payload_token


# ============================================================
# Report generator
# ============================================================
class ReportGenerator:
    """ReportGenerator — generates Markdown reports from chat + evaluation data."""

    def __init__(self) -> None:
        logger.info("ReportGenerator initialized")

    # ----------------------------------------------------------
    # Data collection
    # ----------------------------------------------------------
    async def _fetch_session(self, session_id: str) -> dict[str, Any]:
        """Fetch a single ChatSession from Payload."""
        url = f"{PAYLOAD_URL}/api/chat-sessions/{session_id}"
        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def _fetch_messages(self, session_id: str) -> list[ChatMessage]:
        """Fetch all ChatMessages for a session from Payload."""
        url = f"{PAYLOAD_URL}/api/chat-messages"
        params = {
            "where[session][equals]": session_id,
            "sort": "createdAt",
            "limit": 100,
        }
        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        messages: list[ChatMessage] = []
        for doc in data.get("docs", []):
            messages.append(ChatMessage(
                role=doc.get("role", "user"),
                content=doc.get("content", ""),
                sources=doc.get("sources") or [],
            ))
        logger.info("Fetched {} messages for session {}", len(messages), session_id)
        return messages

    async def _fetch_evaluations(self, messages: list[ChatMessage]) -> list[EvalScore]:
        """Fetch evaluation records that match the user questions in this session."""
        user_questions = [m.content for m in messages if m.role == "user"]
        if not user_questions:
            return []

        evals: list[EvalScore] = []
        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            # Fetch all recent evaluations and match by question text
            resp = await client.get(
                f"{PAYLOAD_URL}/api/evaluations",
                params={"limit": 200, "sort": "-createdAt"},
                headers=headers,
            )
            resp.raise_for_status()
            all_evals = resp.json().get("docs", [])

        # Match evaluations to session questions
        question_set = set(q.strip().lower() for q in user_questions)
        for ev in all_evals:
            q = (ev.get("query") or "").strip().lower()
            if q in question_set:
                evals.append(EvalScore(
                    query=ev.get("query", ""),
                    faithfulness=ev.get("faithfulness"),
                    relevancy=ev.get("relevancy"),
                    correctness=ev.get("correctness"),
                    context_relevancy=ev.get("contextRelevancy"),
                    answer_relevancy=ev.get("answerRelevancy"),
                    question_depth=ev.get("questionDepth"),
                    question_depth_score=ev.get("questionDepthScore"),
                    feedback=ev.get("feedback"),
                ))

        logger.info("Matched {} evaluations for {} questions", len(evals), len(user_questions))
        return evals

    def _compute_stats(
        self, messages: list[ChatMessage], evaluations: list[EvalScore],
    ) -> tuple[dict[str, float], dict[str, int], dict[str, int]]:
        """Compute aggregate statistics from messages and evaluations."""
        # Average scores across all evaluated Q&As
        score_fields = [
            "faithfulness", "relevancy", "correctness",
            "context_relevancy", "answer_relevancy",
        ]
        avg_scores: dict[str, float] = {}
        for field_name in score_fields:
            values = [
                getattr(ev, field_name) for ev in evaluations
                if getattr(ev, field_name) is not None
            ]
            if values:
                avg_scores[field_name] = round(sum(values) / len(values), 3)

        # Question depth distribution
        depth_dist: dict[str, int] = {}
        for ev in evaluations:
            if ev.question_depth:
                depth_dist[ev.question_depth] = depth_dist.get(ev.question_depth, 0) + 1

        # Source statistics from assistant messages
        all_sources: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "assistant" and m.sources:
                all_sources.extend(m.sources)

        source_books: dict[str, int] = {}
        for src in all_sources:
            title = src.get("book_title") or src.get("citation_label") or "Unknown"
            source_books[title] = source_books.get(title, 0) + 1

        return avg_scores, depth_dist, source_books

    async def collect_data(self, session_id: str) -> ReportData:
        """Collect all data needed for report generation."""
        session = await self._fetch_session(session_id)
        messages = await self._fetch_messages(session_id)
        evaluations = await self._fetch_evaluations(messages)
        avg_scores, depth_dist, source_stats = self._compute_stats(messages, evaluations)

        return ReportData(
            session_title=session.get("title", "Untitled Session"),
            messages=messages,
            evaluations=evaluations,
            book_titles=session.get("bookTitles") or [],
            avg_scores=avg_scores,
            depth_distribution=depth_dist,
            source_stats=source_stats,
        )

    # ----------------------------------------------------------
    # LLM report generation
    # ----------------------------------------------------------
    def _build_prompt(self, data: ReportData) -> str:
        """Build the report generation prompt from collected data."""
        # Build conversation transcript
        transcript_lines: list[str] = []
        for m in data.messages:
            prefix = "User" if m.role == "user" else "Assistant"
            transcript_lines.append(f"**{prefix}**: {m.content[:500]}")
        transcript = "\n\n".join(transcript_lines[-20:])  # Last 20 messages to fit context

        # Build evaluation summary
        eval_summary = "No evaluation data available."
        if data.avg_scores:
            score_lines = [f"- {k.replace('_', ' ').title()}: {v:.1%}" for k, v in data.avg_scores.items()]
            eval_summary = "Average scores across evaluated Q&A pairs:\n" + "\n".join(score_lines)

        if data.depth_distribution:
            depth_lines = [f"- {k}: {v} question(s)" for k, v in data.depth_distribution.items()]
            eval_summary += "\n\nQuestion cognitive depth distribution:\n" + "\n".join(depth_lines)

        # Build source stats
        source_summary = "No source data available."
        if data.source_stats:
            source_lines = [f"- {title}: {count} citation(s)" for title, count in
                           sorted(data.source_stats.items(), key=lambda x: -x[1])]
            source_summary = "Citation frequency by document:\n" + "\n".join(source_lines)

        # Build per-question evaluation detail
        per_q_detail = ""
        if data.evaluations:
            detail_lines: list[str] = []
            for ev in data.evaluations:
                scores = []
                if ev.faithfulness is not None:
                    scores.append(f"Faith: {ev.faithfulness:.0%}")
                if ev.answer_relevancy is not None:
                    scores.append(f"Relevancy: {ev.answer_relevancy:.0%}")
                if ev.context_relevancy is not None:
                    scores.append(f"Context: {ev.context_relevancy:.0%}")
                depth_str = f" | Depth: {ev.question_depth}" if ev.question_depth else ""
                detail_lines.append(
                    f"- Q: \"{ev.query[:100]}\" → {', '.join(scores)}{depth_str}"
                )
            per_q_detail = "\n\nPer-question evaluation:\n" + "\n".join(detail_lines)

        prompt = f"""You are a research report writer. Generate a professional Markdown research report based on the following chat session data and evaluation metrics.

## Session: {data.session_title}
## Documents referenced: {', '.join(data.book_titles) if data.book_titles else 'All available documents'}

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

# Research Report: {data.session_title}

## 1. Executive Summary
Write a concise overview of what was discussed, key topics explored, and the overall quality of the research session. Include the number of questions asked ({len([m for m in data.messages if m.role == 'user'])} user messages) and documents referenced.

## 2. Key Findings
Extract and synthesize the most important findings and insights from the assistant's responses. Present as numbered bullet points with specific data points and conclusions drawn from the source documents.

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
- Evaluation framework (5-dimensional: faithfulness, relevancy, correctness, context relevancy, answer relevancy)
- Question depth classification system (surface → understanding → synthesis)

Write in a professional, analytical tone. Use Markdown formatting (headers, bullet points, bold for emphasis). Keep the total report between 800-1500 words."""

        return prompt

    async def generate(
        self,
        session_id: str,
        user_id: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate a report from a chat session.

        Returns the created report document from Payload.
        """
        logger.info("Generating report for session {}", session_id)

        # 1. Collect data
        data = await self.collect_data(session_id)
        message_count = len([m for m in data.messages if m.role == "user"])

        if not data.messages:
            raise ValueError(f"No messages found for session {session_id}")

        # 2. Generate report title
        title = f"Research Report: {data.session_title}"

        # 3. Create a placeholder report in Payload (status: generating)
        report_payload: dict[str, Any] = {
            "title": title,
            "sessionId": session_id,
            "sessionTitle": data.session_title,
            "status": "generating",
            "content": "",
            "stats": {
                "messageCount": message_count,
                "sourceCount": sum(data.source_stats.values()) if data.source_stats else 0,
                "avgScores": data.avg_scores,
                "questionDepths": data.depth_distribution,
            },
        }
        if user_id is not None:
            report_payload["user"] = user_id

        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{PAYLOAD_URL}/api/reports",
                json=report_payload,
                headers=headers,
            )
            resp.raise_for_status()
            report_doc = resp.json().get("doc", resp.json())
            report_id = report_doc["id"]

        logger.info("Created report placeholder id={}", report_id)

        # 4. Generate report content via LLM
        try:
            prompt = self._build_prompt(data)
            content = await self._call_llm(prompt, model=model)

            # 5. Update report with content
            model_name = model or "default"
            token = await _get_payload_token()
            headers = {"Authorization": f"JWT {token}"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.patch(
                    f"{PAYLOAD_URL}/api/reports/{report_id}",
                    json={
                        "content": content,
                        "status": "completed",
                        "model": model_name,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                report_doc = resp.json().get("doc", resp.json())

            logger.info("Report {} completed ({} chars)", report_id, len(content))

        except Exception as exc:
            logger.error("Report generation failed for {}: {}", report_id, exc)
            # Mark as failed
            token_fail = await _get_payload_token()
            headers_fail = {"Authorization": f"JWT {token_fail}"}
            async with httpx.AsyncClient(timeout=15) as client:
                await client.patch(
                    f"{PAYLOAD_URL}/api/reports/{report_id}",
                    json={"status": "failed", "content": f"Generation failed: {exc}"},
                    headers=headers_fail,
                )
            raise

        return report_doc

    async def _call_llm(self, prompt: str, model: str | None = None) -> str:
        """Call the LLM to generate report content."""
        from llama_index.core.settings import Settings as LlamaSettings

        # Resolve LLM — use model override or fall back to default
        if model:
            from engine_v2.llms.resolver import resolve_llm
            llm = resolve_llm(model_name=model)
        else:
            llm = LlamaSettings.llm

        logger.info("Calling LLM for report generation (model={})", model or "default")
        response = await llm.acomplete(prompt)
        return response.text
