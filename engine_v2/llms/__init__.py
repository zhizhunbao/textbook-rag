"""llms — LLM provider routing (Ollama / Azure OpenAI)."""

from engine_v2.llms.resolver import resolve_llm, is_azure_configured

__all__ = ["resolve_llm", "is_azure_configured"]
