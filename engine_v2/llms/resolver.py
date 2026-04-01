"""LLM resolver — dynamic routing between Ollama and Azure OpenAI.

Aligns with llama_index.core.llms module.
Uses LlamaIndex's LLM integration packages:
    - llama-index-llms-ollama       → local inference
    - llama-index-llms-azure-openai → cloud inference

The resolver picks the provider based on environment configuration:
    - If AZURE_OAI_ENDPOINT + AZURE_OAI_KEY are set → AzureOpenAI
    - Otherwise → Ollama (local fallback)
"""

from __future__ import annotations

import logging

from llama_index.core.llms import LLM

from engine_v2.settings import (
    AZURE_OAI_API_VERSION,
    AZURE_OAI_DEPLOYMENT,
    AZURE_OAI_ENDPOINT,
    AZURE_OAI_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)


def is_azure_configured() -> bool:
    """Check if Azure OpenAI credentials are available."""
    return bool(AZURE_OAI_ENDPOINT and AZURE_OAI_KEY)


def resolve_llm(
    model: str | None = None,
    streaming: bool = False,
) -> LLM:
    """Resolve the appropriate LLM instance based on configuration.

    Priority:
        1. Azure OpenAI (if AZURE_OAI_ENDPOINT + AZURE_OAI_KEY are set)
        2. Ollama (local fallback)

    Args:
        model: Override model name. If None, uses env defaults.
        streaming: Whether to enable streaming mode.

    Returns:
        LLM instance ready for use.
    """
    if is_azure_configured():
        return _create_azure_llm(model, streaming)
    return _create_ollama_llm(model, streaming)


def _create_azure_llm(model: str | None, streaming: bool) -> LLM:
    """Create an Azure OpenAI LLM instance."""
    from llama_index.llms.azure_openai import AzureOpenAI

    deployment = model or AZURE_OAI_DEPLOYMENT
    llm = AzureOpenAI(
        engine=deployment,
        azure_endpoint=AZURE_OAI_ENDPOINT,
        api_key=AZURE_OAI_KEY,
        api_version=AZURE_OAI_API_VERSION,
    )
    logger.info("LLM resolved: AzureOpenAI (deployment=%s)", deployment)
    return llm


def _create_ollama_llm(model: str | None, streaming: bool) -> LLM:
    """Create an Ollama LLM instance."""
    from llama_index.llms.ollama import Ollama

    model_name = model or OLLAMA_MODEL
    llm = Ollama(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        request_timeout=180.0,
    )
    logger.info("LLM resolved: Ollama (model=%s, base_url=%s)", model_name, OLLAMA_BASE_URL)
    return llm


def list_providers() -> list[dict]:
    """List available LLM providers and their status."""
    providers = []

    providers.append({
        "name": "ollama",
        "display_name": "Ollama (Local)",
        "model": OLLAMA_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "available": True,  # always available as fallback
    })

    providers.append({
        "name": "azure_openai",
        "display_name": "Azure OpenAI",
        "model": AZURE_OAI_DEPLOYMENT,
        "endpoint": AZURE_OAI_ENDPOINT or "(not configured)",
        "available": is_azure_configured(),
    })

    return providers
