"""llms — LLM provider routing + Model Hub (catalog, benchmark).

Public API:
    resolve_llm          — dynamic routing between Ollama / Azure OpenAI
    is_azure_configured  — check Azure credentials
    search_catalog       — search curated model catalog
    run_benchmark        — run a single benchmark test
"""

from engine_v2.llms.resolver import is_azure_configured, resolve_llm

__all__ = ["is_azure_configured", "resolve_llm"]
