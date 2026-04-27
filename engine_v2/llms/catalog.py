"""catalog — Dynamic Ollama model catalog for Model Hub.

Responsibilities:
    - Fetch model metadata dynamically from Ollama API + HuggingFace API
    - Browse BOTH installed and uninstalled models
    - No hardcoded model metadata — everything comes from live APIs
    - Only maintain: name→HF repo mapping + browsable model name list
    - Cache results with TTL to avoid hammering external APIs

Data sources:
    1. Ollama local API  → /api/tags (installed), /api/show (details)
    2. HuggingFace API   → /api/models/{repo} for rich metadata
    3. Seed name list    → just Ollama model name strings (no metadata)

Ref: Ollama model library — https://ollama.com/library
     HuggingFace API      — https://huggingface.co/docs/hub/api
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from engine_v2.settings import OLLAMA_BASE_URL


# ============================================================
# Constants
# ============================================================
OLLAMA_TIMEOUT = 15.0
HF_TIMEOUT = 10.0
CACHE_TTL_SECONDS = 300  # 5 min cache


# ── Ollama name → HuggingFace repo mapping ───────────────────
# 只维护名称映射关系，不含任何模型元数据
# Only maintains name mapping — zero model metadata here
OLLAMA_TO_HF: dict[str, str] = {
    # Qwen family (Alibaba)
    "qwen3": "Qwen/Qwen3-{size}B",
    "qwen2.5": "Qwen/Qwen2.5-{size}B-Instruct",
    "qwen2.5-coder": "Qwen/Qwen2.5-Coder-{size}B-Instruct",
    "qwq": "Qwen/QwQ-32B",
    # Llama family (Meta)
    "llama3.2": "meta-llama/Llama-3.2-{size}B-Instruct",
    "llama3.1": "meta-llama/Llama-3.1-{size}B-Instruct",
    "llama4-scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    # Gemma family (Google)
    "gemma3": "google/gemma-3-{size}b-it",
    "gemma2": "google/gemma-2-{size}b-it",
    # Phi family (Microsoft)
    "phi4-mini": "microsoft/Phi-4-mini-instruct",
    "phi4": "microsoft/phi-4",
    # DeepSeek
    "deepseek-r1": "deepseek-ai/DeepSeek-R1-Distill-Qwen-{size}B",
    # Mistral
    "mistral-small": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    "devstral": "mistralai/Devstral-Small-2505",
    # Embedding models
    "nomic-embed-text": "nomic-ai/nomic-embed-text-v1.5",
    "mxbai-embed-large": "mixedbread-ai/mxbai-embed-large-v1",
    # Small models
    "smollm2": "HuggingFaceTB/SmolLM2-{size}B-Instruct",
    # Reader
    "reader-lm": "jinaai/reader-lm-0.5b",
}

# ── Fallback browsable list (used when HF API is unreachable) ─
# 后备列表 — 仅在 HuggingFace API 不可用时使用
_FALLBACK_MODELS: list[str] = [
    "qwen3:4b", "qwen3:8b", "phi4-mini", "gemma3:4b",
    "llama3.2:3b", "deepseek-r1:7b", "qwq",
    "nomic-embed-text", "mxbai-embed-large",
]

# Max browsable models to fetch from HuggingFace
BROWSABLE_LIMIT = 30


# ── HF → Ollama reverse mapping ─────────────────────────────
def _reverse_map_hf_to_ollama(hf_repo: str) -> str | None:
    """Reverse-map a HuggingFace repo ID to an Ollama model name.
    将 HuggingFace 仓库 ID 反向映射为 Ollama 模型名称。

    Examples:
        "Qwen/Qwen3-8B"                       → "qwen3:8b"
        "meta-llama/Llama-3.2-3B-Instruct"    → "llama3.2:3b"
        "microsoft/phi-4"                      → "phi4"
    """
    for ollama_base, template in OLLAMA_TO_HF.items():
        if "{size}" not in template:
            # Exact match (no size variable)
            if hf_repo == template:
                return ollama_base
            continue
        # Build regex: "Qwen/Qwen3-{size}B" → r"^Qwen/Qwen3\-([\d.]+)B$"
        pattern = re.escape(template).replace(r"\{size\}", r"([\d.]+)")
        m = re.match(f"^{pattern}$", hf_repo, re.IGNORECASE)
        if m:
            size = m.group(1)
            return f"{ollama_base}:{size}b"
    return None


async def _fetch_browsable_from_hf(limit: int = BROWSABLE_LIMIT) -> list[str]:
    """Dynamically fetch top Ollama-compatible models from HuggingFace by downloads.
    从 HuggingFace API 动态获取按下载量排名的热门模型，映射为 Ollama 名称。

    Strategy:
        1. Query HF for top models from each known org (sorted by downloads)
        2. Reverse-map each HF repo ID to Ollama name
        3. Deduplicate and return top N
        4. Fallback to _FALLBACK_MODELS if HF is unreachable
    """
    # Extract unique HF organizations from the forward mapping
    orgs: set[str] = set()
    for template in OLLAMA_TO_HF.values():
        if "/" in template:
            orgs.add(template.split("/")[0])
    logger.debug("Fetching top models from HF orgs: {}", orgs)

    all_hf_models: list[dict] = []

    try:
        sem = asyncio.Semaphore(3)

        async def fetch_org(org: str) -> list[dict]:
            async with sem:
                async with httpx.AsyncClient(timeout=HF_TIMEOUT) as client:
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

        results = await asyncio.gather(
            *[fetch_org(org) for org in orgs],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, list):
                all_hf_models.extend(r)
    except Exception as exc:
        logger.warning("HF API error, falling back to seed list: {}", exc)
        return _FALLBACK_MODELS[:limit]

    if not all_hf_models:
        logger.warning("No HF models returned, falling back to seed list")
        return _FALLBACK_MODELS[:limit]

    # Sort globally by downloads (descending)
    all_hf_models.sort(key=lambda m: m.get("downloads", 0), reverse=True)

    # Reverse-map to Ollama names, dedup
    ollama_names: list[str] = []
    seen: set[str] = set()
    for hf_model in all_hf_models:
        repo_id = hf_model.get("modelId", "") or hf_model.get("id", "")
        name = _reverse_map_hf_to_ollama(repo_id)
        if name and name not in seen:
            seen.add(name)
            ollama_names.append(name)
        if len(ollama_names) >= limit:
            break

    # Supplement with fallback if we got very few
    if len(ollama_names) < 10:
        for seed in _FALLBACK_MODELS:
            if seed not in seen:
                seen.add(seed)
                ollama_names.append(seed)
            if len(ollama_names) >= limit:
                break

    logger.info("Dynamic browsable list: {} models from HF (top by downloads)", len(ollama_names))
    return ollama_names


# ── Category classification rules ───────────────────────────
# 模型分类规则 — 根据模型名称和参数量自动分类
CATEGORY_RULES: dict[str, list[str]] = {
    "reasoning": ["deepseek-r1", "qwq"],
    "lightweight": [],  # auto: parameter_size < 2B
    "specialized": [
        "qwen2.5-coder", "devstral", "nomic-embed-text",
        "mxbai-embed-large", "reader-lm",
    ],
    # Everything else → "recommended"
}


# ============================================================
# Data classes
# ============================================================
@dataclass
class CatalogModel:
    """A model entry in the catalog — populated from APIs, not hardcoded.
    目录中的模型条目 — 从 API 填充，不硬编码。
    """

    name: str  # Ollama model name (e.g. "qwen3:4b")
    display_name: str
    family: str  # e.g. "qwen", "llama", "gemma"
    category: str  # "recommended" | "reasoning" | "lightweight" | "specialized"
    parameter_size: str  # e.g. "4B", "7B"
    description: str
    advantages: list[str] = field(default_factory=list)
    best_for: list[str] = field(default_factory=list)
    context_window: int = 0
    released: str = ""  # e.g. "2025-04"
    min_ram_gb: float = 0.0
    languages: str = ""
    downloads: int = 0  # HuggingFace download count
    likes: int = 0  # HuggingFace likes
    license: str = ""  # e.g. "apache-2.0"
    hf_repo: str = ""  # HuggingFace repo ID
    installed: bool = False  # Whether model is installed locally
    source: str = "ollama"  # 模型来源 / Model source ("ollama", "huggingface")


# ============================================================
# In-memory cache
# ============================================================
_cache: dict[str, Any] = {
    "catalog": [],
    "timestamp": 0.0,
}


# ============================================================
# Ollama API helpers
# ============================================================
async def _ollama_list_models() -> list[dict]:
    """Fetch locally installed models from Ollama /api/tags.
    从本地 Ollama 获取已安装模型列表。
    """
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])
    except Exception as exc:
        logger.warning("Cannot reach Ollama /api/tags: {}", exc)
        return []


async def _ollama_show_model(name: str) -> dict | None:
    """Get detailed model info from Ollama /api/show.
    获取单个模型的详细信息（context_length, capabilities 等）。
    """
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/show",
                json={"model": name},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.debug("Cannot fetch Ollama show for {}: {}", name, exc)
        return None


# ============================================================
# HuggingFace API helpers
# ============================================================
def _resolve_hf_repo(ollama_name: str) -> str | None:
    """Map an Ollama model name to its HuggingFace repository ID.
    将 Ollama 模型名称映射到 HuggingFace 仓库 ID。

    Examples:
        "qwen3:4b" → "Qwen/Qwen3-4B"
        "llama3.2:3b" → "meta-llama/Llama-3.2-3B-Instruct"
    """
    # Split "model:tag" → base, tag
    parts = ollama_name.split(":")
    base = parts[0]
    tag = parts[1] if len(parts) > 1 else ""

    # Extract size from tag (e.g. "4b" → "4", "1.7b" → "1.7")
    size_match = re.match(r"([\d.]+)b", tag.lower()) if tag else None
    size = size_match.group(1) if size_match else ""

    # Look up template
    template = OLLAMA_TO_HF.get(base)
    if not template:
        return None

    if "{size}" in template:
        if not size:
            return None
        return template.replace("{size}", size)

    return template


async def _hf_fetch_model(repo_id: str) -> dict | None:
    """Fetch model metadata from HuggingFace API.
    从 HuggingFace REST API 获取模型元数据。

    Returns a dict with: id, tags, downloads, likes, cardData, config, etc.
    """
    url = f"https://huggingface.co/api/models/{repo_id}"
    try:
        async with httpx.AsyncClient(timeout=HF_TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                logger.debug("HF model not found: {}", repo_id)
                return None
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.debug("HF API error for {}: {}", repo_id, exc)
        return None


# ============================================================
# Metadata extraction from API responses
# ============================================================
def _extract_context_length(ollama_show: dict | None) -> int:
    """Extract context_length from Ollama /api/show response.
    从 Ollama show 响应中提取 context_length。
    """
    if not ollama_show:
        return 0

    model_info = ollama_show.get("model_info", {})
    # Try architecture-specific keys like "llama.context_length", "qwen2.context_length"
    for key, val in model_info.items():
        if key.endswith(".context_length") and isinstance(val, (int, float)):
            return int(val)

    # Fallback: parse from modelfile PARAMETER num_ctx
    modelfile = ollama_show.get("modelfile", "")
    ctx_match = re.search(r"PARAMETER\s+num_ctx\s+(\d+)", modelfile)
    if ctx_match:
        return int(ctx_match.group(1))

    return 0


def _extract_description_from_hf(hf_data: dict | None) -> str:
    """Extract a clean description from HuggingFace model card.
    从 HuggingFace 模型卡片中提取描述。
    """
    if not hf_data:
        return ""

    # cardData sometimes has a description
    card_data = hf_data.get("cardData", {}) or {}
    if isinstance(card_data, dict):
        desc = card_data.get("description", "")
        if desc:
            return desc[:200]

    # Fallback: use the repo description if available
    desc = hf_data.get("description", "")
    if desc:
        return desc[:200]

    return ""


def _extract_tags_from_hf(hf_data: dict | None) -> dict[str, Any]:
    """Extract structured tags from HuggingFace response.
    从 HuggingFace 响应中提取结构化标签。

    Returns dict with: pipeline_tag, license, languages, capabilities
    """
    if not hf_data:
        return {}

    tags = hf_data.get("tags", [])
    card_data = hf_data.get("cardData", {}) or {}

    result: dict[str, Any] = {}

    # License
    license_val = card_data.get("license", "")
    if not license_val:
        for t in tags:
            if t.startswith("license:"):
                license_val = t.split(":", 1)[1]
                break
    result["license"] = license_val

    # Language
    languages = card_data.get("language", [])
    if isinstance(languages, list):
        result["languages"] = ", ".join(languages[:8])
    elif isinstance(languages, str):
        result["languages"] = languages

    # Pipeline tag (text-generation, etc)
    result["pipeline_tag"] = hf_data.get("pipeline_tag", "")

    # Downloads / Likes
    result["downloads"] = hf_data.get("downloads", 0)
    result["likes"] = hf_data.get("likes", 0)

    # Created date
    created = hf_data.get("createdAt", "")
    if created:
        result["released"] = created[:7]  # "2025-04-27..." → "2025-04"

    return result


def _estimate_ram_gb(param_size_str: str) -> float:
    """Estimate minimum RAM requirement from parameter size string.
    根据参数量估算最低 RAM 需求。

    Q4_K_M quantization: ~0.6 GB per billion parameters + ~0.5 GB overhead.
    Handles both 'B' (billion) and 'M' (million) units.

    Examples:
        "4B"      → 4.0 * 0.6 + 0.5 = 2.9 GB
        "1.5B"    → 1.5 * 0.6 + 0.5 = 1.4 GB
        "494.03M" → 0.494 * 0.6 + 0.5 = 0.8 GB
    """
    match = re.match(r"([\d.]+)\s*([BMbm])?", param_size_str)
    if not match:
        return 0.0
    value = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    # Normalize to billions
    param_b = value / 1000.0 if unit == "M" else value
    # Q4_K_M weights + system/KV-cache overhead
    ram = param_b * 0.6 + 0.5
    return round(max(ram, 0.5), 1)


def _classify_category(ollama_name: str, param_size_str: str) -> str:
    """Auto-classify model into a category based on name and size.
    根据模型名称和参数量自动分类。
    """
    base = ollama_name.split(":")[0]

    for cat, names in CATEGORY_RULES.items():
        if base in names:
            return cat

    # Auto-classify lightweight: < 2B params
    match = re.match(r"([\d.]+)", param_size_str)
    if match and float(match.group(1)) < 2.0:
        return "lightweight"

    return "recommended"


def _infer_advantages(hf_data: dict | None, ollama_show: dict | None) -> list[str]:
    """Infer model advantages from API data.
    从 API 数据推断模型优势标签。
    """
    advantages: list[str] = []

    if ollama_show:
        caps = ollama_show.get("capabilities", [])
        if "vision" in caps:
            advantages.append("Vision capable")
        if "tools" in caps:
            advantages.append("Tool calling")
        if "thinking" in caps:
            advantages.append("Chain-of-thought")

    if hf_data:
        tags = hf_data.get("tags", [])
        if "conversational" in tags:
            advantages.append("Conversational")
        downloads = hf_data.get("downloads", 0)
        if downloads > 1_000_000:
            advantages.append("Popular (1M+ downloads)")
        elif downloads > 100_000:
            advantages.append("Well-tested")

        card_data = hf_data.get("cardData", {}) or {}
        license_val = card_data.get("license", "")
        if license_val in ("apache-2.0", "mit"):
            advantages.append(f"Open ({license_val})")

    return advantages[:6]


def _infer_best_for(
    pipeline_tag: str,
    category: str,
    ollama_show: dict | None,
    *,
    family: str = "",
    param_size_str: str = "",
    ollama_name: str = "",
) -> list[str]:
    """Infer 'best for' tags aligned with system personas.
    根据模型家族、参数量、pipeline_tag 和 category 推断最佳用途。

    Tags are aligned with frontend persona filters:
      - Analyst   : analysis, summarization, rag, report, data analysis, insight
      - Student   : study, learning, q&a, chat, tutoring, homework
      - Auditor   : compliance, audit, regulation, verification, policy
      - Math      : math, reasoning, logic, step-by-step, proof, stem, calculation
      - Developer : code, debugging, refactoring, code review, development, api
      - Researcher: research, paper, embedding, semantic search, retrieval, literature
      - Writer    : writing, content, translation, long-form, creative, multilingual
    """
    # Parse param size as float for tiering
    _m = re.match(r"([\d.]+)", param_size_str)
    param_b = float(_m.group(1)) if _m else 0.0
    fam = family.lower()
    name_lower = ollama_name.lower()

    # ── Embedding models → Researcher ─────────────────────────
    if pipeline_tag == "feature-extraction" or "embed" in name_lower:
        if "nomic" in name_lower:
            return ["Semantic search", "RAG retrieval", "Research", "Retrieval"]
        if "mxbai" in name_lower:
            return ["Semantic search", "Research", "Retrieval", "Data analysis"]
        return ["Semantic search", "RAG retrieval", "Research"]

    # ── Reader / HTML extraction → Researcher ─────────────────
    if "reader" in name_lower:
        return ["Content extraction", "Research", "Literature", "Paper"]

    # ── Coding models → Developer ─────────────────────────────
    if "coder" in name_lower or "devstral" in name_lower:
        return ["Code", "Debugging", "Code review", "Refactoring", "Development", "API"]

    # ── Reasoning models → Math / Auditor ─────────────────────
    if category == "reasoning" or "deepseek-r1" in name_lower or "qwq" in name_lower:
        return ["Math", "Reasoning", "Logic", "Step-by-step", "Proof", "STEM", "Compliance"]

    # ── Family-specific + size-aware (persona-aligned) ────────
    if fam.startswith("qwen"):
        if param_b <= 2:
            return ["Study", "Learning", "Q&A", "Homework", "Quick testing"]
        if param_b <= 4:
            return ["Study", "Chat", "Q&A", "Tutoring", "RAG", "Analysis"]
        if param_b <= 8:
            return ["Analysis", "Summarization", "RAG", "Report", "Study", "Writing", "Translation"]
        return ["Analysis", "Report", "Insight", "Long-form", "Writing", "Research", "Compliance"]

    if fam.startswith("llama"):
        if param_b <= 3:
            return ["Study", "Learning", "Chat", "Q&A", "Homework"]
        if param_b <= 8:
            return ["Chat", "RAG", "Analysis", "Study", "Tutoring", "Summarization"]
        return ["Analysis", "Report", "Content", "Research", "Compliance", "Governance"]

    if fam.startswith("gemma"):
        if param_b <= 1:
            return ["Study", "Learning", "Q&A", "Homework", "Quick testing"]
        if param_b <= 4:
            return ["Study", "Chat", "Summarization", "RAG", "Analysis"]
        return ["Analysis", "Research", "Multilingual", "Writing", "Report", "Compliance"]

    if fam.startswith("phi"):
        return ["Reasoning", "STEM", "Math", "Code", "Analysis", "Study", "Calculation"]

    if fam.startswith("mistral") or fam.startswith("devstral"):
        if param_b <= 8:
            return ["Chat", "Study", "Multilingual", "Translation", "Writing"]
        return ["Analysis", "RAG", "Compliance", "Multilingual", "Writing", "Content"]

    if fam.startswith("smollm"):
        return ["Study", "Learning", "Quick testing", "Homework"]

    # ── Generic fallback by size ──────────────────────────────
    if param_b < 2:
        return ["Study", "Learning", "Q&A", "Quick testing"]
    if param_b <= 7:
        return ["Analysis", "Chat", "RAG", "Summarization", "Study"]
    return ["Analysis", "Report", "Research", "Content", "Writing", "Compliance"]


def _make_display_name(ollama_name: str, details: dict | None = None) -> str:
    """Generate a human-friendly display name.
    生成用户友好的显示名称。

    "qwen3:4b" → "Qwen3 4B"
    "llama3.2:3b" → "Llama3.2 3B"
    "deepseek-r1:7b" → "Deepseek R1 7B"
    """
    base, tag = (ollama_name.split(":") + [""])[:2]

    # Clean up base name: split on hyphens, capitalize
    parts = base.replace("_", "-").split("-")
    name = " ".join(p.capitalize() for p in parts)

    # Add tag as size
    if tag:
        name = f"{name} {tag.upper()}"

    return name


def _extract_param_size_from_name(ollama_name: str) -> str:
    """Extract parameter size from the Ollama model name tag.
    从 Ollama 模型名称标签中提取参数量。

    "qwen3:4b" → "4B"
    "deepseek-r1:1.5b" → "1.5B"
    "qwq" → ""
    """
    parts = ollama_name.split(":")
    if len(parts) < 2:
        return ""
    tag = parts[1]
    match = re.match(r"([\d.]+b)", tag.lower())
    return match.group(1).upper() if match else tag.upper()


# ============================================================
# Core: Enrich a single model from APIs
# ============================================================
async def _enrich_model(
    name: str,
    *,
    ollama_details: dict | None = None,
    is_installed: bool = False,
) -> CatalogModel | None:
    """Enrich a single model with data from Ollama + HuggingFace APIs.
    使用 Ollama + HuggingFace API 数据充实单个模型。

    Args:
        name: Ollama model name (e.g. "qwen3:4b")
        ollama_details: Pre-fetched details from /api/tags (for installed models)
        is_installed: Whether the model is locally installed
    """
    if not name:
        return None

    # Details from Ollama /api/tags (if installed)
    details = ollama_details or {}
    family = details.get("family", "")
    param_size = details.get("parameter_size", "")

    # If not installed, infer family and param_size from name
    if not family:
        family = name.split(":")[0].split("-")[0].replace(".", "")
    if not param_size:
        param_size = _extract_param_size_from_name(name)

    # Ollama /api/show for deep metadata (only for installed models)
    ollama_show = None
    if is_installed:
        ollama_show = await _ollama_show_model(name)

    # HuggingFace for rich metadata (for all models)
    hf_repo = _resolve_hf_repo(name)
    hf_data = None
    if hf_repo:
        hf_data = await _hf_fetch_model(hf_repo)

    # Extract context length (only available for installed models via /api/show)
    context_window = _extract_context_length(ollama_show)

    # Extract description from HuggingFace
    description = _extract_description_from_hf(hf_data)
    if not description:
        description = f"{family.capitalize()} model with {param_size} parameters."

    # Extract HF tags
    hf_tags = _extract_tags_from_hf(hf_data)

    # Auto-classify
    category = _classify_category(name, param_size)

    # Infer advantages & best_for
    advantages = _infer_advantages(hf_data, ollama_show)
    pipeline_tag = hf_tags.get("pipeline_tag", "")
    best_for = _infer_best_for(
        pipeline_tag, category, ollama_show,
        family=family, param_size_str=param_size, ollama_name=name,
    )

    return CatalogModel(
        name=name,
        display_name=_make_display_name(name, details),
        family=family,
        category=category,
        parameter_size=param_size,
        description=description,
        advantages=advantages,
        best_for=best_for,
        context_window=context_window,
        released=hf_tags.get("released", ""),
        min_ram_gb=_estimate_ram_gb(param_size),
        languages=hf_tags.get("languages", ""),
        downloads=hf_tags.get("downloads", 0),
        likes=hf_tags.get("likes", 0),
        license=hf_tags.get("license", ""),
        hf_repo=hf_repo or "",
        installed=is_installed,
        source="ollama" if is_installed else "huggingface",  # local installed vs browsable
    )


# ============================================================
# Core: Build catalog from live APIs
# ============================================================
async def build_catalog_from_apis() -> list[CatalogModel]:
    """Build the full model catalog: installed + top HF models by downloads.
    构建完整模型目录：已安装 + HuggingFace 下载量 Top N。

    Strategy:
    1. Fetch installed models from Ollama /api/tags → mark installed=True
    2. Dynamically fetch top 30 models from HuggingFace by downloads
    3. Reverse-map HF repos to Ollama names, skip already-installed
    4. Enrich ALL models with HuggingFace metadata concurrently
    5. Deduplicate by name (installed version wins)
    """
    logger.info("Building catalog from live APIs (installed + browsable)...")

    # Step 1: Get installed models
    installed_raw = await _ollama_list_models()
    installed_names: set[str] = set()

    # Build enrichment tasks
    tasks: list[tuple[str, dict | None, bool]] = []

    for m in installed_raw:
        name = m.get("name", "")
        if not name:
            continue
        installed_names.add(name)
        # Also add the normalized name (without ":latest")
        normalized = name.replace(":latest", "")
        installed_names.add(normalized)
        tasks.append((name, m.get("details"), True))

    # Step 2: Fetch top browsable models from HuggingFace (dynamic, sorted by downloads)
    browsable = await _fetch_browsable_from_hf(limit=BROWSABLE_LIMIT)
    for seed_name in browsable:
        # Check if already installed (exact or with :latest)
        if seed_name in installed_names or f"{seed_name}:latest" in installed_names:
            continue
        tasks.append((seed_name, None, False))

    # Step 3: Enrich all concurrently (bounded concurrency for rate limits)
    semaphore = asyncio.Semaphore(5)

    async def bounded_enrich(name: str, details: dict | None, installed: bool) -> CatalogModel | None:
        async with semaphore:
            return await _enrich_model(name, ollama_details=details, is_installed=installed)

    results = await asyncio.gather(
        *[bounded_enrich(n, d, i) for n, d, i in tasks],
        return_exceptions=True,
    )

    # Step 4: Collect and deduplicate
    seen: set[str] = set()
    catalog: list[CatalogModel] = []
    for r in results:
        if isinstance(r, CatalogModel) and r.name not in seen:
            seen.add(r.name)
            catalog.append(r)
        elif isinstance(r, Exception):
            logger.warning("Failed to enrich model: {}", r)

    # Sort: installed first, then by newest (released desc), then downloads
    catalog.sort(key=lambda m: (
        0 if m.installed else 1,
        m.released or "0000-00",  # newer released dates first
        -m.downloads,
    ), reverse=False)
    # Re-sort properly: installed first, then newest, then popular
    catalog.sort(key=lambda m: (
        0 if m.installed else 1,
        -(int(m.released.replace("-", "")) if m.released else 0),
        -m.downloads,
    ))

    logger.info(
        "Catalog built — {} total ({} installed, {} browsable)",
        len(catalog),
        sum(1 for m in catalog if m.installed),
        sum(1 for m in catalog if not m.installed),
    )
    return catalog


# ============================================================
# Cached search interface
# ============================================================
async def get_catalog() -> list[CatalogModel]:
    """Get the catalog, using cache if fresh enough.
    获取目录，如果缓存足够新则使用缓存。
    """
    now = time.time()
    if _cache["catalog"] and (now - _cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _cache["catalog"]

    catalog = await build_catalog_from_apis()
    _cache["catalog"] = catalog
    _cache["timestamp"] = now
    return catalog


def invalidate_cache() -> None:
    """Force catalog rebuild on next request.
    强制下次请求时重新构建目录。
    """
    _cache["timestamp"] = 0.0


# Category display order and labels
CATEGORIES = {
    "recommended": "Recommended",
    "reasoning": "Reasoning",
    "lightweight": "Lightweight",
    "specialized": "Specialized",
}


async def search_catalog(
    query: str | None = None,
    category: str | None = None,
    source: str | None = None,
    sort: str | None = None,
) -> list[CatalogModel]:
    """搜索和过滤模型目录（异步版本）。
    Search and filter the model catalog (async version).

    Args:
        query: Optional text search (matches name, family, description).
        category: Optional category filter.
        source: Optional source filter ("ollama", "huggingface").
        sort: Sort order — "newest" (default), "downloads", "name".

    Returns:
        Filtered list of CatalogModel.
    """
    catalog = await get_catalog()
    results = catalog

    if category:
        results = [m for m in results if m.category == category]

    if source:
        results = [m for m in results if m.source == source]

    if query:
        q = query.lower()
        results = [
            m for m in results
            if q in m.name.lower()
            or q in m.family.lower()
            or q in m.display_name.lower()
            or q in m.description.lower()
        ]

    # Apply sorting
    if sort == "downloads":
        results.sort(key=lambda m: (0 if m.installed else 1, -m.downloads))
    elif sort == "name":
        results.sort(key=lambda m: (0 if m.installed else 1, m.name.lower()))
    # else: default = newest (already sorted by build_catalog_from_apis)

    logger.debug(
        "Catalog search — query={}, category={}, source={}, sort={}, results={}",
        query, category, source, sort, len(results),
    )
    return results


def catalog_to_dict(model: CatalogModel) -> dict:
    """Serialize CatalogModel to JSON-safe dict."""
    return {
        "name": model.name,
        "displayName": model.display_name,
        "family": model.family,
        "category": model.category,
        "parameterSize": model.parameter_size,
        "description": model.description,
        "advantages": model.advantages,
        "bestFor": model.best_for,
        "contextWindow": model.context_window,
        "released": model.released,
        "minRamGb": model.min_ram_gb,
        "languages": model.languages,
        "downloads": model.downloads,
        "likes": model.likes,
        "license": model.license,
        "hfRepo": model.hf_repo,
        "installed": model.installed,
        "source": model.source,
    }
