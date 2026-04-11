"""Unified LLM client — routes calls to Ollama or Azure OpenAI.

根据 provider 参数自动选择后端:
  - "ollama"       → 本地 Ollama /api/chat
  - "azure_openai" → Azure OpenAI Chat Completions API

Provides a single `chat()` entry point used by GenerationEngine and
question generation, so callers don't need to know transport details.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from typing import Any

import httpx

from engine.config import (
    AZURE_OAI_API_VERSION,
    AZURE_OAI_DEPLOYMENT,
    AZURE_OAI_ENDPOINT,
    AZURE_OAI_KEY,
    OLLAMA_BASE_URL,
)

logger = logging.getLogger(__name__)

# ── Public API ───────────────────────────────────────────────────────────────


def chat(
    *,
    model: str,
    system: str,
    user: str,
    provider: str | None = None,
    timeout: float = 180.0,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    """Send a chat request and return the assistant's text reply.

    Args:
        model:          Model name (e.g. "qwen3.5:4b" or "gpt-4o-mini").
        system:         System prompt.
        user:           User prompt.
        provider:       "ollama" | "azure_openai" | None.
                        None → auto-detect based on Azure env vars.
        timeout:        HTTP timeout in seconds.
        extra_payload:  Extra keys merged into the request body (e.g. {"think": False}).

    Returns:
        The assistant message content string.
    """
    resolved = _resolve_provider(provider, model)

    if resolved == "azure_openai":
        return _call_azure_openai(model, system, user, timeout, extra_payload)
    return _call_ollama(model, system, user, timeout, extra_payload)


def is_azure_configured() -> bool:
    """Check whether Azure OpenAI credentials are set."""
    return bool(AZURE_OAI_ENDPOINT and AZURE_OAI_KEY)


def chat_stream(
    *,
    model: str,
    system: str,
    user: str,
    provider: str | None = None,
    timeout: float = 180.0,
    extra_payload: dict[str, Any] | None = None,
) -> Generator[str, None, None]:
    """Yield tokens as they arrive from the LLM (streaming).

    Same interface as chat() but returns a generator of token strings.
    Used by query_stream() for SSE responses.
    """
    resolved = _resolve_provider(provider, model)

    if resolved == "azure_openai":
        yield from _stream_azure_openai(model, system, user, timeout, extra_payload)
    else:
        yield from _stream_ollama(model, system, user, timeout, extra_payload)


# ── Internal helpers ─────────────────────────────────────────────────────────


def _resolve_provider(provider: str | None, model: str = "") -> str:
    """Determine which provider to use.

    Priority:
      1. Explicit provider param (from frontend or QueryConfig) — validated
      2. Infer from model name (gpt-* → azure_openai if configured)
      3. Fallback → "ollama"

    Raises RuntimeError if Azure is required but not configured.
    """
    # ── Explicit provider — validate it ──
    if provider:
        if provider == "azure_openai" and not is_azure_configured():
            raise RuntimeError(
                "Provider 'azure_openai' requested but Azure OpenAI is not configured. "
                "Set AZURE_OAI_ENDPOINT and AZURE_OAI_KEY in .env."
            )
        return provider

    # ── Auto-detect from model name ──
    model_lower = model.lower()
    if any(tag in model_lower for tag in ("gpt-", "o1-", "o3-", "text-embedding")):
        if is_azure_configured():
            return "azure_openai"
        raise RuntimeError(
            f"Model '{model}' requires Azure OpenAI but it is not configured. "
            "Set AZURE_OAI_ENDPOINT and AZURE_OAI_KEY in .env."
        )

    return "ollama"


def _call_ollama(
    model: str,
    system: str,
    user: str,
    timeout: float,
    extra: dict[str, Any] | None,
) -> str:
    """Call local Ollama /api/chat endpoint."""
    # 检测思考型模型，自动禁用 CoT / Detect thinking models, disable CoT
    is_thinking = any(
        tag in model.lower()
        for tag in ("qwen3", "qwen3.5", "deepseek-r1", "qwq")
    )

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    if is_thinking:
        payload["think"] = False
    if extra:
        payload.update(extra)

    url = f"{OLLAMA_BASE_URL}/api/chat"
    try:
        logger.info("LLM [ollama] model=%s url=%s", model, url)
        resp = httpx.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except httpx.HTTPError as e:
        logger.error("Ollama HTTP error: %s", e)
        return f"[Generation error: {e}]"
    except (json.JSONDecodeError, KeyError):
        return "[Generation error: unexpected Ollama response format]"


def _call_azure_openai(
    model: str,
    system: str,
    user: str,
    timeout: float,
    extra: dict[str, Any] | None,
) -> str:
    """Call Azure OpenAI Chat Completions REST API.

    Uses the deployment name from config (AZURE_OAI_DEPLOYMENT), ignoring the
    `model` parameter since Azure routes by deployment.

    Docs: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference
    """
    deployment = AZURE_OAI_DEPLOYMENT
    endpoint = AZURE_OAI_ENDPOINT.rstrip("/")
    api_version = AZURE_OAI_API_VERSION

    url = (
        f"{endpoint}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={api_version}"
    )

    payload: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    if extra:
        # 过滤掉 Ollama 专用字段 / Strip Ollama-specific fields
        azure_safe = {k: v for k, v in extra.items() if k not in ("think", "stream")}
        payload.update(azure_safe)

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OAI_KEY,
    }

    try:
        logger.info(
            "LLM [azure_openai] deployment=%s endpoint=%s",
            deployment, endpoint,
        )
        resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        logger.warning("Azure OpenAI returned no choices: %s", data)
        return "[Generation error: Azure OpenAI returned no choices]"
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500] if e.response else ""
        logger.error("Azure OpenAI HTTP %s: %s", e.response.status_code, body)
        return f"[Generation error: Azure OpenAI {e.response.status_code}]"
    except httpx.HTTPError as e:
        logger.error("Azure OpenAI request error: %s", e)
        return f"[Generation error: {e}]"
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Azure OpenAI parse error: %s", e)
        return "[Generation error: unexpected Azure OpenAI response format]"


# ── Streaming implementations ────────────────────────────────────────────────


def _stream_ollama(
    model: str,
    system: str,
    user: str,
    timeout: float,
    extra: dict[str, Any] | None,
) -> Generator[str, None, None]:
    """Stream tokens from local Ollama /api/chat (NDJSON format)."""
    is_thinking = any(
        tag in model.lower()
        for tag in ("qwen3", "qwen3.5", "deepseek-r1", "qwq")
    )

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
    }
    if is_thinking:
        payload["think"] = False
    if extra:
        payload.update(extra)
    # Force stream on even if extra tried to override
    payload["stream"] = True

    url = f"{OLLAMA_BASE_URL}/api/chat"
    try:
        logger.info("LLM [ollama/stream] model=%s url=%s", model, url)
        with httpx.stream("POST", url, json=payload, timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except httpx.HTTPError as e:
        logger.error("Ollama stream HTTP error: %s", e)
        yield f"[Generation error: {e}]"


def _stream_azure_openai(
    model: str,
    system: str,
    user: str,
    timeout: float,
    extra: dict[str, Any] | None,
) -> Generator[str, None, None]:
    """Stream tokens from Azure OpenAI Chat Completions (SSE format)."""
    deployment = AZURE_OAI_DEPLOYMENT
    endpoint = AZURE_OAI_ENDPOINT.rstrip("/")
    api_version = AZURE_OAI_API_VERSION

    url = (
        f"{endpoint}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={api_version}"
    )

    payload: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": True,
    }
    if extra:
        azure_safe = {k: v for k, v in extra.items() if k not in ("think",)}
        payload.update(azure_safe)
    # Force stream on
    payload["stream"] = True

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OAI_KEY,
    }

    try:
        logger.info(
            "LLM [azure_openai/stream] deployment=%s endpoint=%s",
            deployment, endpoint,
        )
        with httpx.stream("POST", url, json=payload, headers=headers, timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped == "data: [DONE]":
                    break
                if stripped.startswith("data: "):
                    json_str = stripped[6:]
                    try:
                        chunk = json.loads(json_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                    except json.JSONDecodeError:
                        continue
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500] if e.response else ""
        logger.error("Azure OpenAI stream HTTP %s: %s", e.response.status_code, body)
        yield f"[Generation error: Azure OpenAI {e.response.status_code}]"
    except httpx.HTTPError as e:
        logger.error("Azure OpenAI stream request error: %s", e)
        yield f"[Generation error: {e}]"
