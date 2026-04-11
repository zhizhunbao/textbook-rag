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


@router.get("/models/discover")
def discover_models():
    """Discover all locally installed Ollama models with full details.
    
    Returns model name, size, modified time, and technical details
    (parameter_size, quantization_level, family, format).
    This allows the frontend to auto-detect local models that 
    may not yet be registered in the CMS.
    """
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        raw_models = resp.json().get("models", [])
        models = []
        for m in raw_models:
            models.append({
                "name": m.get("name", ""),
                "model": m.get("model", m.get("name", "")),
                "size": m.get("size", 0),
                "modified_at": m.get("modified_at", ""),
                "digest": m.get("digest", ""),
                "details": m.get("details", {}),
            })
        return {"models": models, "ollama_url": OLLAMA_BASE_URL}
    except Exception as e:
        return {"models": [], "error": str(e), "ollama_url": OLLAMA_BASE_URL}


@router.delete("/models/{model_name:path}")
def remove_model(model_name: str):
    """Remove a model from local Ollama.
    
    Calls Ollama's DELETE /api/delete to uninstall a model.
    """
    try:
        resp = httpx.request(
            "DELETE",
            f"{OLLAMA_BASE_URL}/api/delete",
            json={"name": model_name},
            timeout=30.0,
        )
        if resp.status_code == 200:
            return {"status": "ok", "model": model_name}
        else:
            return {
                "status": "error",
                "model": model_name,
                "error": f"Ollama returned {resp.status_code}: {resp.text}",
            }
    except Exception as e:
        return {"status": "error", "model": model_name, "error": str(e)}


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
