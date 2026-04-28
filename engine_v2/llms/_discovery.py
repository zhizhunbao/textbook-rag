"""_discovery — Discover browsable models from Ollama Library + HuggingFace.

Responsibilities:
    - Fetch top models from HuggingFace by downloads, reverse-map to Ollama names
    - Scrape pullable model tags from live Ollama Library pages
    - Map Ollama names ↔ HuggingFace repo IDs (bidirectional)

Performance:
    - Shared httpx.AsyncClient per batch (connection pooling + keep-alive)
    - Pre-compiled reverse-map regex patterns (avoid re.compile per call)

Ref: Ollama model library — https://ollama.com/library
     HuggingFace API      — https://huggingface.co/docs/hub/api
"""

from __future__ import annotations

import asyncio
import re

import httpx
from loguru import logger

from engine_v2.llms.prompts import OLLAMA_TO_HF

# ============================================================
# Constants
# ============================================================
HF_TIMEOUT = 10.0
BROWSABLE_LIMIT = 120

# ── Junk tag filter (quantization/precision variants) ────────
# 量化、精度后缀以及无版本通用别名 — 对普通用户无意义，直接过滤
_JUNK_SUFFIXES = re.compile(
    r"(mxfp8|nvfp4|bf16|mlx|fp16|awq|gptq|coding|instruct|gguf|latest)",
    re.IGNORECASE,
)
# A valid size tag contains at least one digit (e.g. "7b", "14b", "35b-a3b")
_HAS_SIZE = re.compile(r"\d")


# ============================================================
# Pre-compiled reverse-map patterns (P2 — avoid per-call compile)
# ============================================================
# Each entry: (ollama_base, compiled_regex, has_size_var)
# Built once at module import, reused for every _reverse_map call
_REVERSE_PATTERNS: list[tuple[str, re.Pattern | None, str]] = []

for _base, _template in OLLAMA_TO_HF.items():
    if "{size}" not in _template:
        # Exact match — no regex needed
        _REVERSE_PATTERNS.append((_base, None, _template))
    else:
        # Build regex from template
        _pattern = re.escape(_template).replace(r"\{size\}", r"([A-Za-z0-9.\-]+)")
        _REVERSE_PATTERNS.append((_base, re.compile(f"^{_pattern}$", re.IGNORECASE), _template))


# ============================================================
# Bidirectional name mapping
# ============================================================
def reverse_map_hf_to_ollama(hf_repo: str) -> str | None:
    """Reverse-map a HuggingFace repo ID to an Ollama model name.
    将 HuggingFace 仓库 ID 反向映射为 Ollama 模型名称。

    Uses pre-compiled patterns for O(1) regex cost per pattern.
    """
    if hf_repo == "Qwen/Qwen3.6-35B-A3B":
        return "qwen3.6:35b"

    for ollama_base, compiled, template in _REVERSE_PATTERNS:
        if compiled is None:
            # Exact match
            if hf_repo == template:
                return ollama_base
            continue
        m = compiled.match(hf_repo)
        if m:
            size = m.group(1).lower()
            if not size.endswith("b") and re.fullmatch(r"[\d.]+", size):
                size = f"{size}b"
            return f"{ollama_base}:{size}"
    return None


def resolve_hf_repo(ollama_name: str) -> str | None:
    """Map an Ollama model name to its HuggingFace repository ID.
    将 Ollama 模型名称映射到 HuggingFace 仓库 ID。

    "qwen3:4b" → "Qwen/Qwen3-4B",  "llama3.2:3b" → "meta-llama/Llama-3.2-3B-Instruct"
    """
    parts = ollama_name.split(":")
    base = parts[0]
    tag = parts[1] if len(parts) > 1 else ""

    # Qwen3.6 MoE special case
    if base == "qwen3.6":
        tag_lower = tag.lower()
        if tag_lower in {"", "latest", "35b"} or tag_lower.startswith("35b-a3b"):
            return "Qwen/Qwen3.6-35B-A3B"
        if tag_lower.startswith("27b"):
            return "Qwen/Qwen3.6-27B"

    template = OLLAMA_TO_HF.get(base)
    if not template:
        return None

    if "{size}" in template:
        if not tag:
            return None
        tag_lower = tag.lower()
        if base == "gemma4":
            size = tag_lower.upper()
        else:
            numeric = re.match(r"([\d.]+)b$", tag_lower)
            size = numeric.group(1) if numeric else tag_lower.upper()
        if template.endswith("{size}B") and isinstance(size, str) and size.endswith("B"):
            return template.replace("{size}B", size)
        return template.replace("{size}", size)

    return template


# ============================================================
# HuggingFace API — batch fetch top models
# ============================================================
async def fetch_browsable_from_hf(
    limit: int = BROWSABLE_LIMIT,
) -> tuple[list[str], dict[str, dict]]:
    """Dynamically fetch top Ollama-compatible models from HuggingFace by downloads.
    从 HuggingFace API 动态获取按下载量排名的热门模型，映射为 Ollama 名称。

    Returns:
        (ollama_names, hf_data_map) — names list + pre-fetched HF metadata keyed
        by HF repo ID.  Metadata is reused during enrichment (no per-model calls).

    Performance: uses a single shared httpx.AsyncClient for all org fetches.
    """
    orgs: set[str] = set()
    for template in OLLAMA_TO_HF.values():
        if "/" in template:
            orgs.add(template.split("/")[0])
    logger.debug("Fetching top models from HF orgs: {}", orgs)

    all_hf_models: list[dict] = []
    try:
        sem = asyncio.Semaphore(3)

        async def fetch_org(client: httpx.AsyncClient, org: str) -> list[dict]:
            async with sem:
                resp = await client.get(
                    "https://huggingface.co/api/models",
                    params={
                        "sort": "downloads",
                        "direction": "-1",
                        "limit": "15",
                        "author": org,
                    },
                )
                resp.raise_for_status()
                return resp.json()

        # P1: Single shared client — connection pooling for all org fetches
        async with httpx.AsyncClient(timeout=HF_TIMEOUT) as client:
            results = await asyncio.gather(
                *[fetch_org(client, org) for org in orgs],
                return_exceptions=True,
            )
        for r in results:
            if isinstance(r, list):
                all_hf_models.extend(r)
    except Exception as exc:
        logger.warning("HF API error while building browsable models: {}", exc)
        return [], {}

    if not all_hf_models:
        logger.warning("No HF models returned while building browsable models")
        return [], {}

    all_hf_models.sort(key=lambda m: m.get("downloads", 0), reverse=True)

    # Build repo_id → full HF response map (reused during enrichment)
    hf_data_map: dict[str, dict] = {}
    for hf_model in all_hf_models:
        repo_id = hf_model.get("modelId", "") or hf_model.get("id", "")
        if repo_id:
            hf_data_map[repo_id] = hf_model

    # Reverse-map to Ollama names, dedup
    ollama_names: list[str] = []
    seen: set[str] = set()
    for hf_model in all_hf_models:
        repo_id = hf_model.get("modelId", "") or hf_model.get("id", "")
        name = reverse_map_hf_to_ollama(repo_id)
        if name and name not in seen:
            seen.add(name)
            ollama_names.append(name)
        if len(ollama_names) >= limit:
            break

    logger.info("Dynamic browsable list: {} models from HF (top by downloads)", len(ollama_names))
    return ollama_names, hf_data_map


# ============================================================
# Ollama Library — scrape pullable tags
# ============================================================
async def fetch_browsable_from_ollama_library(limit: int = BROWSABLE_LIMIT) -> list[str]:
    """Fetch pullable model tags from live Ollama Library pages.
    只保留带明确尺寸 tag 的条目，过滤裸 base 名和量化/精度特定变体。

    Performance: uses a single shared httpx.AsyncClient for all base fetches.
    """
    bases = list(OLLAMA_TO_HF.keys())
    names: list[str] = []
    seen: set[str] = set()
    sem = asyncio.Semaphore(4)

    async def fetch_base(client: httpx.AsyncClient, base: str) -> list[str]:
        async with sem:
            url = f"https://ollama.com/library/{base}"
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                html = resp.text
            except Exception as exc:
                logger.debug("Ollama Library fetch failed for {}: {}", base, exc)
                return []

            pattern = rf"{re.escape(base)}(?::[A-Za-z0-9_.-]+)?"
            local_seen: set[str] = set()
            tagged: list[str] = []
            for match in re.finditer(pattern, html, re.IGNORECASE):
                model_name = match.group(0).lower()
                if "cloud" in model_name:
                    continue
                tag = model_name.split(":", 1)[1] if ":" in model_name else ""
                if _JUNK_SUFFIXES.search(tag):
                    continue
                # Only include tags with explicit size (e.g. :7b, :14b)
                if ":" not in model_name or not _HAS_SIZE.search(tag):
                    continue
                if model_name not in local_seen:
                    local_seen.add(model_name)
                    tagged.append(model_name)
            return tagged

    # P1: Single shared client — connection pooling for all base fetches
    async with httpx.AsyncClient(timeout=HF_TIMEOUT, follow_redirects=True) as client:
        results = await asyncio.gather(
            *[fetch_base(client, base) for base in bases],
            return_exceptions=True,
        )

    for result in results:
        if not isinstance(result, list):
            continue
        for name in result:
            if name not in seen:
                seen.add(name)
                names.append(name)
            if len(names) >= limit:
                return names

    logger.info("Dynamic browsable list: {} models from Ollama Library", len(names))
    return names


# ============================================================
# Individual HuggingFace model fetch (fallback for cache miss)
# ============================================================
async def hf_fetch_model(
    repo_id: str,
    client: httpx.AsyncClient | None = None,
) -> dict | None:
    """Fetch model metadata from HuggingFace API.
    从 HuggingFace REST API 获取模型元数据。

    If a shared client is provided, reuses its connection pool.
    """
    url = f"https://huggingface.co/api/models/{repo_id}"
    try:
        if client:
            resp = await client.get(url)
        else:
            async with httpx.AsyncClient(timeout=HF_TIMEOUT) as c:
                resp = await c.get(url)
        if resp.status_code == 404:
            logger.debug("HF model not found: {}", repo_id)
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("HF API error for {}: {}", repo_id, exc)
        return None
