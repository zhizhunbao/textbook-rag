# 1.6 `engine_v2/settings.py` — 全局配置单例

> 本文件已固定，不可新增。模板仅供参考。

```python
"""settings — 全局配置单例 (环境变量、模型参数、路径).

Usage:
    from engine_v2.settings import settings
    settings.data_dir
    settings.embedding_model
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置 — 自动从 .env 和环境变量加载."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ============================================================
    # Data paths
    # ============================================================
    data_dir: Path = Path("data")
    chroma_persist_dir: Path = Path("data/chroma_persist")
    mineru_output_dir: Path = Path("data/mineru_output")

    # ============================================================
    # Model config
    # ============================================================
    embedding_model: str = "all-MiniLM-L6-v2"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"

    # ============================================================
    # Engine API
    # ============================================================
    engine_host: str = "0.0.0.0"
    engine_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    # ============================================================
    # Payload CMS
    # ============================================================
    payload_url: str = "http://localhost:3000"

    # ============================================================
    # RAG defaults
    # ============================================================
    top_k: int = 5
    chroma_collection: str = "textbook_chunks"


# ============================================================
# Singleton
# ============================================================
settings = Settings()


# ============================================================
# Init function
# ============================================================
def init_settings() -> None:
    """Initialise LlamaIndex global Settings singleton.

    Call once at startup (in api/app.py lifespan or script entry).
    """
    from llama_index.core.settings import Settings as LlamaSettings

    from engine_v2.embeddings import resolve_embed_model
    from engine_v2.llms.resolver import resolve_llm

    LlamaSettings.embed_model = resolve_embed_model()
    LlamaSettings.llm = resolve_llm()
```
