"""resolver — Select and configure embedding models.

Responsibilities:
    - Resolve embedding model instance by name or settings default
    - Expose current embedding configuration for API introspection

Ref: llama_index — BaseEmbedding, resolve_embed_model()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    pass  # type-only imports

from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from engine_v2.settings import EMBEDDING_MODEL


# ============================================================
# Resolver
# ============================================================
def resolve_embed_model(
    model_name: str | None = None,
) -> BaseEmbedding:
    """Resolve and return an embedding model instance.

    Priority:
        1. Explicit model_name parameter
        2. EMBEDDING_MODEL env var (default: all-MiniLM-L6-v2)

    Currently always returns HuggingFaceEmbedding (local).
    Future: add OpenAI / Azure OpenAI embedding support.

    Args:
        model_name: Override model name. If None, uses settings.

    Returns:
        BaseEmbedding instance ready for use.
    """
    name = model_name or EMBEDDING_MODEL
    logger.info("Resolving embedding model: {}", name)

    # 强制离线模式 — 模型已缓存在 ~/.cache/huggingface/hub/
    # 避免每次启动都 HEAD 请求 huggingface.co 检查更新（网络不稳定时会超时卡死）
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    # Currently only HuggingFace local is supported
    return HuggingFaceEmbedding(model_name=name)


# ============================================================
# Info
# ============================================================
def get_embed_info() -> dict[str, Any]:
    """Return current embedding model configuration info.

    Returns:
        Dict with model details for API exposure.
    """
    from llama_index.core.settings import Settings

    embed = Settings.embed_model
    if embed is None:
        return {
            "model": None,
            "provider": "none",
            "status": "not_initialized",
        }

    model_name = getattr(embed, "model_name", str(embed))
    embed_dim = getattr(embed, "embed_batch_size", None)

    return {
        "model": model_name,
        "provider": "huggingface",
        "embed_batch_size": embed_dim,
        "status": "ready",
    }
