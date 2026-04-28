"""_metadata — Model metadata extraction, inference, and serialization.

Responsibilities:
    - Parse parameter sizes and estimate RAM requirements
    - Extract structured metadata from Ollama /api/show and HuggingFace API
    - Infer model type, category, advantages, best-for tags
    - Generate display names and infer family lineage
    - Filter superseded model generations

All functions are pure (no I/O) — they transform API response dicts
into structured values consumed by catalog.py's enrichment pipeline.

Ref: Ollama model library — https://ollama.com/library
     HuggingFace API      — https://huggingface.co/docs/hub/api
"""

from __future__ import annotations

import re
from typing import Any

from engine_v2.llms.prompts import (
    BEST_FOR_BY_FAMILY,
    BEST_FOR_GENERIC,
    CATEGORY_RULES,
    lookup_known_description,
)


# ============================================================
# Parameter size parsing
# ============================================================
def parse_param_b(param_size_str: str) -> float:
    """Parse parameter size strings such as 4B, 494M, E2B, or 35B-A3B.

    MoE notation "35B-A3B" = 35B total / 3B active parameters.
    RAM estimation uses TOTAL params — all expert weights must reside in
    memory even though only ~3B are active per forward pass.
    """
    # MoE: "35B-A3B" → use total (35B), NOT active (3B)
    moe_match = re.match(r"([\d.]+)b-a[\d.]+b", param_size_str, re.IGNORECASE)
    if moe_match:
        return float(moe_match.group(1))
    # Efficient: "E2B" → 2B
    efficient_match = re.match(r"e([\d.]+)b", param_size_str, re.IGNORECASE)
    if efficient_match:
        return float(efficient_match.group(1))
    # Standard: "7B", "1.5B", "494M"
    match = re.match(r"([\d.]+)\s*([BMbm])?", param_size_str)
    if not match:
        return 0.0
    value = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    return value / 1000.0 if unit == "M" else value


def estimate_ram_gb(param_size_str: str) -> float:
    """Estimate minimum RAM requirement from parameter size string.
    根据参数量估算最低 RAM 需求。

    Q4_K_M quantization: ~0.6 GB per billion parameters + ~0.5 GB overhead.
    """
    param_b = parse_param_b(param_size_str)
    if param_b <= 0:
        return 0.0
    ram = param_b * 0.6 + 0.5
    return round(max(ram, 0.5), 1)


# ============================================================
# Name / family extraction
# ============================================================
def extract_param_size_from_name(ollama_name: str) -> str:
    """Extract parameter size from the Ollama model name tag.
    从 Ollama 模型名称标签中提取参数量。

    "qwen3:4b" → "4B",  "deepseek-r1:1.5b" → "1.5B",  "qwq" → ""
    """
    parts = ollama_name.split(":")
    if len(parts) < 2:
        return ""
    tag = parts[1]
    lower = tag.lower()
    if lower in {"e2b", "e4b"}:
        return lower.upper()
    moe = re.match(r"([\d.]+b-a[\d.]+b)", lower)
    if moe:
        return moe.group(1).upper()
    match = re.match(r"([\d.]+b)", lower)
    return match.group(1).upper() if match else tag.upper()


def infer_family_from_name(ollama_name: str) -> str:
    """Infer a display/filter family from an Ollama model name."""
    base = ollama_name.split(":")[0].lower()
    if base.startswith(("qwen", "gemma", "llama")):
        return base
    if base == "qwq":
        return "qwen"
    if base.startswith("deepseek"):
        return "deepseek"
    if base.startswith("mistral") or base == "devstral":
        return "mistral"
    if base.startswith("phi"):
        return "phi"
    return base.split("-")[0].replace(".", "")


def make_display_name(ollama_name: str) -> str:
    """Generate a human-friendly display name.
    生成用户友好的显示名称。

    "qwen3:4b" → "Qwen3 4B",  "deepseek-r1:7b" → "Deepseek R1 7B"
    """
    base, tag = (ollama_name.split(":") + [""])[:2]
    parts = base.replace("_", "-").split("-")
    name = " ".join(p.capitalize() for p in parts)
    if tag:
        name = f"{name} {tag.upper()}"
    return name


# ============================================================
# Metadata extraction from API responses
# ============================================================
def extract_context_length(ollama_show: dict | None) -> int:
    """Extract context_length from Ollama /api/show response.
    从 Ollama show 响应中提取 context_length。
    """
    if not ollama_show:
        return 0
    model_info = ollama_show.get("model_info", {})
    for key, val in model_info.items():
        if key.endswith(".context_length") and isinstance(val, (int, float)):
            return int(val)
    modelfile = ollama_show.get("modelfile", "")
    ctx_match = re.search(r"PARAMETER\s+num_ctx\s+(\d+)", modelfile)
    return int(ctx_match.group(1)) if ctx_match else 0


def extract_description(ollama_name: str, hf_data: dict | None) -> str:
    """Extract description: hand-written → HuggingFace → empty.
    描述优先级：手写描述库 → HuggingFace → 空。
    """
    desc = lookup_known_description(ollama_name)
    if desc:
        return desc
    if not hf_data:
        return ""
    card_data = hf_data.get("cardData", {}) or {}
    if isinstance(card_data, dict):
        d = card_data.get("description", "")
        if d:
            return d[:200]
    d = hf_data.get("description", "")
    return d[:200] if d else ""


def extract_tags_from_hf(hf_data: dict | None) -> dict[str, Any]:
    """Extract structured tags from HuggingFace response.
    从 HuggingFace 响应中提取结构化标签。

    Returns dict with: pipeline_tag, license, languages, downloads, likes, released
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

    result["pipeline_tag"] = hf_data.get("pipeline_tag", "")
    result["downloads"] = hf_data.get("downloads", 0)
    result["likes"] = hf_data.get("likes", 0)

    created = hf_data.get("createdAt", "")
    if created:
        result["released"] = created[:7]
    return result


# ============================================================
# Model classification and inference
# ============================================================
def infer_model_type(
    ollama_name: str,
    pipeline_tag: str,
    ollama_show: dict | None,
) -> str:
    """Infer model type: 'chat' | 'embedding' | 'vision'.
    根据模型名称、HF pipeline_tag 和 Ollama capabilities 自动分类模型类型。
    """
    name_lower = ollama_name.lower()
    if pipeline_tag == "feature-extraction" or "embed" in name_lower:
        return "embedding"
    if ollama_show:
        caps = ollama_show.get("capabilities", [])
        if "vision" in caps:
            return "vision"
    if any(kw in name_lower for kw in ("vision", "vlm", "llava", "moondream", "minicpm-v")):
        return "vision"
    return "chat"


def classify_category(ollama_name: str, param_size_str: str) -> str:
    """Auto-classify model into a category based on name and size.
    根据模型名称和参数量自动分类。
    """
    base = ollama_name.split(":")[0]
    for cat, names in CATEGORY_RULES.items():
        if base in names:
            return cat
    param_b = parse_param_b(param_size_str)
    if 0 < param_b < 2.0:
        return "lightweight"
    return "recommended"


def infer_advantages(hf_data: dict | None, ollama_show: dict | None) -> list[str]:
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


def _match_size_tier(tiers: list[tuple[float, list[str]]], param_b: float) -> list[str]:
    """Return the first tier whose max_param_b >= param_b."""
    for max_b, tags in tiers:
        if param_b <= max_b:
            return tags
    return tiers[-1][1]


def infer_best_for(
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
    """
    param_b = parse_param_b(param_size_str)
    name_lower = ollama_name.lower()

    # Special model types (short-circuit)
    if pipeline_tag == "feature-extraction" or "embed" in name_lower:
        if "nomic" in name_lower:
            return ["Semantic search", "RAG retrieval", "Research", "Retrieval"]
        if "mxbai" in name_lower:
            return ["Semantic search", "Research", "Retrieval", "Data analysis"]
        return ["Semantic search", "RAG retrieval", "Research"]
    if "reader" in name_lower:
        return ["Content extraction", "Research", "Literature", "Paper"]
    if "coder" in name_lower or "devstral" in name_lower:
        return ["Code", "Debugging", "Code review", "Refactoring", "Development", "API"]
    if category == "reasoning" or "deepseek-r1" in name_lower or "qwq" in name_lower:
        return ["Math", "Reasoning", "Logic", "Step-by-step", "Proof", "STEM", "Compliance"]

    # Family-specific size-tiered lookup
    fam = family.lower()
    for prefix, tiers in BEST_FOR_BY_FAMILY.items():
        if fam.startswith(prefix):
            return _match_size_tier(tiers, param_b)
    return _match_size_tier(BEST_FOR_GENERIC, param_b)


# ============================================================
# Generation tracking and filtering
# ============================================================
def _model_lineage_and_generation(model_name: str) -> tuple[str, int]:
    """Return a broad family lineage and generation rank for hiding old series."""
    base = model_name.split(":")[0].lower()
    versioned = re.match(r"^(qwen|llama|gemma|phi)([\d.]+)", base)
    if versioned:
        lineage = versioned.group(1)
        digits = versioned.group(2).split(".")
        major = int(digits[0]) if digits and digits[0].isdigit() else 0
        minor = int(digits[1]) if len(digits) > 1 and digits[1].isdigit() else 0
        return lineage, major * 100 + minor
    if base.startswith("deepseek"):
        release = re.search(r"r(\d+)", base)
        return "deepseek", int(release.group(1)) if release else 0
    if base.startswith("mistral"):
        return "mistral", 0
    if base.startswith("smollm"):
        release = re.search(r"smollm(\d+)", base)
        return "smollm", int(release.group(1)) if release else 0
    return base.split("-")[0].replace(".", ""), 0


def hide_superseded_generations(
    catalog: list,  # list[CatalogModel] — avoid circular import
) -> list:
    """Keep only the newest generation for each broad model family."""
    newest_by_lineage: dict[str, int] = {}
    for model in catalog:
        lineage, generation = _model_lineage_and_generation(model.name)
        if generation <= 0:
            continue
        newest_by_lineage[lineage] = max(newest_by_lineage.get(lineage, 0), generation)

    filtered = []
    for model in catalog:
        lineage, generation = _model_lineage_and_generation(model.name)
        newest = newest_by_lineage.get(lineage, 0)
        if generation > 0 and newest > generation:
            continue
        filtered.append(model)
    return filtered
