"""LLM resolver — dynamic routing between Ollama and Azure OpenAI.

Aligns with llama_index.core.llms module.
Uses LlamaIndex's LLM integration packages:
    - llama-index-llms-ollama       → local inference
    - llama-index-llms-azure-openai → cloud inference

The resolver picks the provider based on:
    1. Explicit `provider` parameter from frontend model selector
    2. Auto-detection from model name (Ollama models contain ':')
    3. Default fallback: Azure if configured, else Ollama
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


# Well-known Azure model names (without ':' — Ollama models always have ':')
_AZURE_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4", "gpt-35-turbo", "gpt-3.5-turbo"}


def _detect_provider(model: str | None, provider: str | None) -> str:
    """Determine correct provider from explicit param or model name heuristics.

    Returns 'azure' or 'ollama'.
    """
    # Explicit provider from frontend
    if provider:
        p = provider.lower()
        if "azure" in p or "openai" in p:
            return "azure"
        if "ollama" in p:
            return "ollama"

    # Auto-detect from model name
    if model:
        # Ollama models always contain ':' (e.g., llama3.2:3b, qwen2:7b)
        if ":" in model:
            return "ollama"
        # Known Azure model names
        if model.lower() in _AZURE_MODELS:
            return "azure"

    # Default: Azure if configured, else Ollama
    return "azure" if is_azure_configured() else "ollama"


def resolve_llm(
    model: str | None = None,
    streaming: bool = False,
    provider: str | None = None,
) -> LLM:
    """Resolve the appropriate LLM instance based on provider and model.

    Priority:
        1. Explicit `provider` parameter ('ollama' or 'azure_openai')
        2. Auto-detect from model name (models with ':' → Ollama)
        3. Azure OpenAI (if AZURE_OAI_ENDPOINT + AZURE_OAI_KEY are set)
        4. Ollama (local fallback)

    Args:
        model: Override model name. If None, uses env defaults.
        streaming: Whether to enable streaming mode.
        provider: Explicit provider name ('ollama', 'azure_openai', etc.).

    Returns:
        LLM instance ready for use.
    """
    resolved = _detect_provider(model, provider)
    logger.info("LLM routing: model=%s, provider_hint=%s → %s", model, provider, resolved)

    if resolved == "azure":
        if not is_azure_configured():
            logger.warning("Azure requested but not configured, falling back to Ollama")
            return _create_ollama_llm(model, streaming)
        return _create_azure_llm(model, streaming)
    return _create_ollama_llm(model, streaming)


def _create_azure_llm(model: str | None, streaming: bool) -> LLM:
    """Create an Azure OpenAI LLM instance."""
    from llama_index.llms.azure_openai import AzureOpenAI
    import os

    # Map UI model names → actual Azure deployment names.
    # Azure deployments may use different names than the model itself.
    # Check AZURE_OAI_DEPLOYMENT_* env vars for overrides first.
    DEPLOYMENT_MAP: dict[str, str] = {
        "gpt-4o": os.getenv("AZURE_OAI_DEPLOYMENT_GPT4O", "gpt-4o"),
        "gpt-4o-mini": os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini"),
        "gpt-4.1-mini": os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini"),
    }

    raw_model = model or AZURE_OAI_DEPLOYMENT
    deployment = DEPLOYMENT_MAP.get(raw_model, raw_model)

    logger.info("Azure LLM: model=%s → deployment=%s", raw_model, deployment)

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
        context_window=8192,
        additional_kwargs={"num_ctx": 8192},
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
