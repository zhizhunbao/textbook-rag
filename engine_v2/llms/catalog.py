"""catalog — Dynamic Ollama model catalog for Model Hub.

Responsibilities:
    - CatalogModel dataclass — the single model representation
    - Enrich models from Ollama + HuggingFace APIs
    - Build full catalog (installed + browsable) with caching
    - Search / filter / serialize catalog entries

Data flow:
    _discovery.py  →  model names + HF metadata
    _metadata.py   →  pure extraction / inference helpers
    catalog.py     →  orchestrate enrichment + cache + public API

Ref: Ollama model library — https://ollama.com/library
     HuggingFace API      — https://huggingface.co/docs/hub/api
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from engine_v2.settings import OLLAMA_BASE_URL
from engine_v2.llms.prompts import CATEGORIES  # noqa: F401 — re-exported
from engine_v2.llms._discovery import (
    fetch_browsable_from_hf,
    fetch_browsable_from_ollama_library,
    hf_fetch_model,
    resolve_hf_repo,
    reverse_map_hf_to_ollama,
    BROWSABLE_LIMIT,
)
from engine_v2.llms._metadata import (
    classify_category,
    estimate_ram_gb,
    extract_context_length,
    extract_description,
    extract_tags_from_hf,
    hide_superseded_generations,
    infer_advantages,
    infer_best_for,
    infer_family_from_name,
    infer_model_type,
    make_display_name,
    extract_param_size_from_name,
    parse_param_b,
)


# ============================================================
# Constants
# ============================================================
OLLAMA_TIMEOUT = 15.0
CACHE_TTL_SECONDS = 300  # 5 min cache


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
    model_type: str  # "chat" | "embedding" | "vision"
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
    source: str = "ollama"  # 模型来源 (\"ollama\", \"huggingface\")


# ============================================================
# In-memory cache
# ============================================================
_cache: dict[str, Any] = {
    "catalog": [],        # last known good catalog
    "timestamp": 0.0,    # when the catalog was last built
    "fingerprint": "",   # hash of installed model list for change detection
    "rebuilding": False, # guard against concurrent rebuilds
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
            return resp.json().get("models", [])
    except Exception as exc:
        logger.warning("Cannot reach Ollama /api/tags: {}", exc)
        return []


async def _ollama_show_model(
    name: str, client: httpx.AsyncClient | None = None,
) -> dict | None:
    """Get detailed model info from Ollama /api/show.
    获取单个模型的详细信息（context_length, capabilities 等）。

    If a shared client is provided, reuses its connection pool.
    """
    try:
        if client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/show", json={"model": name},
            )
        else:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as c:
                resp = await c.post(
                    f"{OLLAMA_BASE_URL}/api/show", json={"model": name},
                )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("Cannot fetch Ollama show for {}: {}", name, exc)
        return None


# ============================================================
# Core: Enrich a single model from APIs
# ============================================================
async def _enrich_model(
    name: str,
    *,
    ollama_details: dict | None = None,
    is_installed: bool = False,
    source: str | None = None,
    hf_data: dict | None = None,
    hf_repo_id: str | None = None,
    ollama_client: httpx.AsyncClient | None = None,
) -> CatalogModel | None:
    """Enrich a single model with data from Ollama + HuggingFace APIs.
    使用 Ollama + HuggingFace API 数据充实单个模型。

    P3: hf_repo_id passed directly — avoids redundant _resolve_hf_repo calls.
    P1: ollama_client shared — avoids per-model TCP connection setup.
    """
    if not name:
        return None

    details = ollama_details or {}
    family = details.get("family", "") or infer_family_from_name(name)
    param_size = details.get("parameter_size", "") or extract_param_size_from_name(name)

    # Ollama /api/show for deep metadata (only for installed models)
    ollama_show = None
    if is_installed:
        ollama_show = await _ollama_show_model(name, client=ollama_client)

    # HuggingFace metadata — use pre-fetched, then resolve + fetch as fallback
    hf_repo = hf_repo_id or resolve_hf_repo(name)
    if hf_data is None and hf_repo:
        hf_data = await hf_fetch_model(hf_repo)

    # Extract all metadata
    hf_tags = extract_tags_from_hf(hf_data)
    pipeline_tag = hf_tags.get("pipeline_tag", "")
    category = classify_category(name, param_size)

    return CatalogModel(
        name=name,
        display_name=make_display_name(name),
        family=family,
        category=category,
        model_type=infer_model_type(name, pipeline_tag, ollama_show),
        parameter_size=param_size,
        description=extract_description(name, hf_data),
        advantages=infer_advantages(hf_data, ollama_show),
        best_for=infer_best_for(
            pipeline_tag, category, ollama_show,
            family=family, param_size_str=param_size, ollama_name=name,
        ),
        context_window=extract_context_length(ollama_show),
        released=hf_tags.get("released", ""),
        min_ram_gb=estimate_ram_gb(param_size),
        languages=hf_tags.get("languages", ""),
        downloads=hf_tags.get("downloads", 0),
        likes=hf_tags.get("likes", 0),
        license=hf_tags.get("license", ""),
        hf_repo=hf_repo or "",
        installed=is_installed,
        source=source or ("ollama" if is_installed else "huggingface"),
    )


# ============================================================
# Core: Build catalog from live APIs
# ============================================================
async def build_catalog_from_apis() -> list[CatalogModel]:
    """Build the full model catalog: installed + top HF models by downloads.
    构建完整模型目录：已安装 + HuggingFace 下载量 Top N。

    Strategy:
    1. Fetch installed models from Ollama /api/tags → mark installed=True
    2. Dynamically fetch browsable models from HF + Ollama Library
    3. Build HF pre-fetch lookup, enrich ALL concurrently
    4. Deduplicate, filter superseded generations, sort
    """
    logger.info("Building catalog from live APIs (installed + browsable)...")

    # Step 1: Get installed models + browsable lists concurrently
    installed_raw, (ollama_browsable, (hf_browsable, hf_data_map)) = await asyncio.gather(
        _ollama_list_models(),
        asyncio.gather(
            fetch_browsable_from_ollama_library(limit=BROWSABLE_LIMIT),
            fetch_browsable_from_hf(limit=BROWSABLE_LIMIT),
        ),
    )

    installed_names = _collect_installed_names(installed_raw)
    logger.info(
        "Catalog sources — installed={}, ollama_library={}, hf={}, hf_prefetched={}",
        len(installed_names), len(ollama_browsable), len(hf_browsable), len(hf_data_map),
    )

    # Step 2: Build pre-fetched HF data lookup (ollama_name → HF data)
    name_to_hf = _build_hf_lookup(installed_raw, hf_data_map)

    # Step 3: Build enrichment task list
    tasks = _build_enrichment_tasks(installed_raw, installed_names, ollama_browsable, hf_browsable)

    # Step 4: Enrich all concurrently with shared clients
    catalog = await _enrich_all(tasks, name_to_hf)

    # Step 5: Filter and sort
    catalog = hide_superseded_generations(catalog)
    catalog.sort(key=_sort_key)

    logger.info(
        "Catalog built — {} total ({} installed, {} browsable)",
        len(catalog),
        sum(1 for m in catalog if m.installed),
        sum(1 for m in catalog if not m.installed),
    )
    return catalog


def _collect_installed_names(installed_raw: list[dict]) -> set[str]:
    """Build set of installed model names (both raw and normalized)."""
    names: set[str] = set()
    for m in installed_raw:
        name = m.get("name", "")
        if name:
            names.add(name)
            names.add(name.replace(":latest", ""))
    return names


def _build_hf_lookup(
    installed_raw: list[dict], hf_data_map: dict[str, dict],
) -> dict[str, dict]:
    """Build ollama_name → pre-fetched HF data lookup table.
    构建 ollama_name → 预取 HF 数据查找表。
    """
    name_to_hf: dict[str, dict] = {}
    for repo_id, data in hf_data_map.items():
        ollama_name = reverse_map_hf_to_ollama(repo_id)
        if ollama_name:
            name_to_hf[ollama_name] = data
    for m in installed_raw:
        iname = m.get("name", "")
        if not iname:
            continue
        canonical = iname.replace(":latest", "")
        if canonical not in name_to_hf:
            hf_repo = resolve_hf_repo(canonical)
            if hf_repo and hf_repo in hf_data_map:
                name_to_hf[canonical] = hf_data_map[hf_repo]
    return name_to_hf


def _build_enrichment_tasks(
    installed_raw: list[dict],
    installed_names: set[str],
    ollama_browsable: list[str],
    hf_browsable: list[str],
) -> list[tuple[str, dict | None, bool, str]]:
    """Build (name, details, is_installed, source) task list."""
    tasks: list[tuple[str, dict | None, bool, str]] = []

    # Installed models
    for m in installed_raw:
        name = m.get("name", "")
        if name:
            tasks.append((name, m.get("details"), True, "ollama"))

    # Browsable (not installed)
    seen: set[str] = set()
    browsable = [(n, "ollama") for n in ollama_browsable] + [(n, "huggingface") for n in hf_browsable]
    for seed_name, seed_source in browsable:
        canonical = seed_name[:-7] if seed_name.endswith(":latest") else seed_name
        if canonical in installed_names or f"{canonical}:latest" in installed_names:
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        tasks.append((canonical, None, False, seed_source))

    return tasks


async def _enrich_all(
    tasks: list[tuple[str, dict | None, bool, str]],
    name_to_hf: dict[str, dict],
) -> list[CatalogModel]:
    """Enrich all models concurrently with shared HTTP clients.
    P1: 共享 httpx 客户端，避免逐模型创建连接。
    """
    semaphore = asyncio.Semaphore(15)

    async def bounded_enrich(
        name: str, details: dict | None, installed: bool, model_source: str,
        *, ollama_client: httpx.AsyncClient,
    ) -> CatalogModel | None:
        async with semaphore:
            canonical = name.replace(":latest", "")
            return await _enrich_model(
                name,
                ollama_details=details,
                is_installed=installed,
                source=model_source,
                hf_data=name_to_hf.get(canonical),
                ollama_client=ollama_client if installed else None,
            )

    # P1: Single Ollama client shared across all installed model /api/show calls
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as ollama_client:
        results = await asyncio.gather(
            *[
                bounded_enrich(n, d, i, s, ollama_client=ollama_client)
                for n, d, i, s in tasks
            ],
            return_exceptions=True,
        )

    # Deduplicate: normalize :latest, installed version wins
    seen: set[str] = set()
    catalog: list[CatalogModel] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Failed to enrich model: {}", r)
            continue
        if not isinstance(r, CatalogModel):
            continue
        canonical = r.name[:-7] if r.name.endswith(":latest") else r.name
        if canonical in seen:
            continue
        seen.add(canonical)
        r.name = canonical
        catalog.append(r)
    return catalog


def _sort_key(m: CatalogModel) -> tuple:
    """Sort: ① installed first ② downloads desc ③ params asc."""
    param_b = parse_param_b(m.parameter_size) if m.parameter_size else 999.0
    return (0 if m.installed else 1, -m.downloads, param_b)


# ============================================================
# Cached search interface
# ============================================================
def _compute_installed_fingerprint(installed_raw: list[dict]) -> str:
    """Compute a fingerprint from the installed model list for change detection.
    用已安装模型列表生成指纹，用于检测变更。
    """
    tokens = sorted(
        f"{m.get('name', '')}:{m.get('modified_at', '')}"
        for m in installed_raw
    )
    return hashlib.md5("|".join(tokens).encode()).hexdigest()[:12]


async def _rebuild_in_background() -> None:
    """Rebuild the catalog in the background and update the cache.
    在后台重新构建目录并更新缓存（不阻塞当前请求）。
    """
    if _cache["rebuilding"]:
        return
    _cache["rebuilding"] = True
    try:
        catalog = await build_catalog_from_apis()
        _cache["catalog"] = catalog
        _cache["timestamp"] = time.time()
        logger.info("Catalog rebuilt in background ({} models)", len(catalog))
    except Exception as exc:
        logger.warning("Background catalog rebuild failed: {}", exc)
    finally:
        _cache["rebuilding"] = False


async def get_catalog() -> list[CatalogModel]:
    """Return catalog immediately from cache; rebuild in background only if changed.
    立即从缓存返回数据；仅当检测到 Ollama 模型列表变化时才后台重建。

    Strategy — Stale-While-Revalidate:
      1. Fetch /api/tags (fast, local network ~5ms)
      2. If installed list fingerprint unchanged AND cache non-empty → return stale
      3. If fingerprint changed OR cache empty → trigger background rebuild
    """
    installed_raw = await _ollama_list_models()
    new_fp = _compute_installed_fingerprint(installed_raw)

    if _cache["catalog"] and new_fp == _cache["fingerprint"]:
        return _cache["catalog"]

    if not _cache["catalog"]:
        logger.info("Cold start: building catalog synchronously...")
        catalog = await build_catalog_from_apis()
        _cache["catalog"] = catalog
        _cache["timestamp"] = time.time()
        _cache["fingerprint"] = new_fp
        return catalog

    logger.info(
        "Installed models changed (fp {} → {}), triggering background rebuild",
        _cache["fingerprint"], new_fp,
    )
    _cache["fingerprint"] = new_fp
    asyncio.create_task(_rebuild_in_background())
    return _cache["catalog"]


def invalidate_cache() -> None:
    """Force catalog rebuild on next request by clearing the fingerprint.
    强制下次请求重建目录（清空指纹）。
    """
    _cache["fingerprint"] = ""
    _cache["timestamp"] = 0.0


# ============================================================
# Search and serialize
# ============================================================
async def search_catalog(
    query: str | None = None,
    category: str | None = None,
    source: str | None = None,
    sort: str | None = None,
) -> list[CatalogModel]:
    """搜索和过滤模型目录。
    Search and filter the model catalog.
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

    if sort == "downloads":
        results.sort(key=lambda m: (0 if m.installed else 1, -m.downloads))
    elif sort == "name":
        results.sort(key=lambda m: (0 if m.installed else 1, m.name.lower()))

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
        "modelType": model.model_type,
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
