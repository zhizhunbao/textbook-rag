"""LLMs route — GET /engine/llms/providers, /engine/llms/models."""

from __future__ import annotations

from fastapi import APIRouter

from engine_v2.llms.resolver import is_azure_configured, list_providers

router = APIRouter(prefix="/llms", tags=["llms"])


@router.get("/providers")
async def providers():
    """List available LLM providers and their status."""
    return {"providers": list_providers()}


@router.get("/models")
async def models():
    """Return current LLM and embedding model info."""
    from llama_index.core.settings import Settings

    return {
        "llm": {
            "model": str(Settings.llm.metadata.model_name) if Settings.llm else None,
            "provider": "azure_openai" if is_azure_configured() else "ollama",
        },
        "embed_model": {
            "model": str(Settings.embed_model.model_name) if Settings.embed_model else None,
        },
    }
