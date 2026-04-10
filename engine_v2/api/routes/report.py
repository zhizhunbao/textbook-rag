"""report routes — Report generation + retrieval + PDF export endpoints.

Endpoints:
    POST   /engine/report/generate                — generate report from chat session
    GET    /engine/report/list                    — list current user's reports
    GET    /engine/report/sessions/available      — list available chat sessions
    GET    /engine/report/{report_id}             — get report by ID
    GET    /engine/report/{report_id}/pdf         — download report as PDF

NOTE: Static routes (/list, /sessions/available) MUST be defined before
      dynamic routes (/{report_id}) so FastAPI doesn't try to match
      "list" or "sessions" as a report_id parameter.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel

import httpx
from engine_v2.settings import PAYLOAD_URL
from engine_v2.report.generator import _get_payload_token

# ============================================================
# Router
# ============================================================
router = APIRouter(prefix="/report", tags=["report"])


# ============================================================
# Request models
# ============================================================
class GenerateReportRequest(BaseModel):
    """Request to generate a report from a chat session."""

    sessionId: str
    userId: int | None = None
    model: str | None = None


# ============================================================
# POST /engine/report/generate
# ============================================================
@router.post("/generate")
async def generate_report(req: GenerateReportRequest):
    """Generate a Markdown report from a chat session + evaluation data."""
    logger.info("Report generation requested for session={}", req.sessionId)

    from engine_v2.report.generator import ReportGenerator

    generator = ReportGenerator()
    try:
        report = await generator.generate(
            session_id=req.sessionId,
            user_id=req.userId,
            model=req.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Report generation failed: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {"report": report}


# ============================================================
# GET /engine/report/list
# ============================================================
@router.get("/list")
async def list_reports(userId: int | None = None, limit: int = 50):
    """List reports, optionally filtered by user."""
    logger.info("Listing reports (userId={}, limit={})", userId, limit)

    params: dict = {"limit": limit, "sort": "-createdAt"}
    if userId:
        params["where[user][equals]"] = userId

    token = await _get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PAYLOAD_URL}/api/reports", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return {
        "reports": data.get("docs", []),
        "count": data.get("totalDocs", 0),
    }


# ============================================================
# GET /engine/report/sessions/available — MUST be before /{report_id}
# ============================================================
@router.get("/sessions/available")
async def list_available_sessions(limit: int = 50):
    """List chat sessions available for report generation."""
    logger.info("Listing available sessions for report generation")

    token = await _get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{PAYLOAD_URL}/api/chat-sessions",
            params={"limit": limit, "sort": "-createdAt"},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    sessions = []
    for doc in data.get("docs", []):
        sessions.append({
            "id": doc.get("id"),
            "title": doc.get("title", "Untitled"),
            "bookTitles": doc.get("bookTitles") or [],
            "createdAt": doc.get("createdAt"),
            "updatedAt": doc.get("updatedAt"),
        })

    return {"sessions": sessions, "count": len(sessions)}


# ============================================================
# GET /engine/report/{report_id} — dynamic route AFTER static ones
# ============================================================
@router.get("/{report_id}")
async def get_report(report_id: int):
    """Get a single report by ID."""
    logger.info("Fetching report id={}", report_id)

    token = await _get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PAYLOAD_URL}/api/reports/{report_id}", headers=headers)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Report not found")
        resp.raise_for_status()

    return resp.json()


# ============================================================
# GET /engine/report/{report_id}/pdf
# ============================================================
@router.get("/{report_id}/pdf")
async def download_report_pdf(report_id: int):
    """Download a report as a PDF file."""
    logger.info("PDF export requested for report id={}", report_id)

    # Fetch report content
    token = await _get_payload_token()
    headers = {"Authorization": f"JWT {token}"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{PAYLOAD_URL}/api/reports/{report_id}", headers=headers)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Report not found")
        resp.raise_for_status()

    report = resp.json()
    content = report.get("content", "")
    title = report.get("title", "Report")

    if not content:
        raise HTTPException(status_code=400, detail="Report has no content")

    # Generate PDF
    from engine_v2.report.export import markdown_to_pdf

    try:
        pdf_bytes = markdown_to_pdf(content, title=title)
    except Exception as exc:
        logger.exception("PDF export failed: {}", exc)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {exc}")

    # Build safe filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)[:60]
    filename = f"{safe_title}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
