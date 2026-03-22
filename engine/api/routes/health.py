"""Health, strategies, models, providers endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from engine.config import OLLAMA_BASE_URL, AZURE_OAI_ENDPOINT
from engine.api.deps import get_rag_core

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}


@router.get("/strategies")
def list_strategies():
    """List all registered retrieval strategies."""
    core = get_rag_core()
    return {"strategies": core.list_strategies()}


@router.get("/models")
def list_models():
    """List available Ollama models."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        models = [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        models = []
    return {"models": models}


@router.get("/providers")
def list_providers():
    """List available LLM providers."""
    providers = ["ollama"]
    if AZURE_OAI_ENDPOINT:
        providers.append("azure_openai")
    return {"providers": providers}


@router.get("/prompt-templates")
def list_prompt_templates():
    """List available prompt templates."""
    from engine.rag.config import PROMPT_DEFAULT, PROMPT_CONCISE, PROMPT_DETAILED, PROMPT_ACADEMIC
    return {
        "templates": [
            {"id": PROMPT_DEFAULT, "name": "Default"},
            {"id": PROMPT_CONCISE, "name": "Concise"},
            {"id": PROMPT_DETAILED, "name": "Detailed"},
            {"id": PROMPT_ACADEMIC, "name": "Academic"},
        ]
    }
