"""Engine configuration — reads environment variables with sensible defaults.

v2.0: 统一配置，合并 v1.1 backend/app/config.py 内容。
新增: Azure OpenAI / Azure AI Search / Payload 连接配置。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root: one level up from engine/config.py
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data paths — 所有持久化数据统一在 data/ 目录
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(
    os.getenv("DATA_DIR", str(_PROJECT_ROOT / "data"))
)
DATABASE_PATH: Path = Path(
    os.getenv("DATABASE_PATH", str(DATA_DIR / "textbook_rag.sqlite3"))
)
CHROMA_PERSIST_DIR: Path = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_persist"))
)
TEXTBOOKS_DIR: Path = Path(
    os.getenv("TEXTBOOKS_DIR", str(DATA_DIR / "raw_pdfs" / "textbooks"))
)
MINERU_OUTPUT_DIR: Path = Path(
    os.getenv("MINERU_OUTPUT_DIR", str(DATA_DIR / "mineru_output"))
)

# ---------------------------------------------------------------------------
# Ollama (v1.1 保留)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ---------------------------------------------------------------------------
# Azure OpenAI (v2.0 新增)
# ---------------------------------------------------------------------------
AZURE_OAI_ENDPOINT: str = os.getenv("AZURE_OAI_ENDPOINT", "")
AZURE_OAI_KEY: str = os.getenv("AZURE_OAI_KEY", "")
AZURE_OAI_DEPLOYMENT: str = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o")
AZURE_OAI_API_VERSION: str = os.getenv("AZURE_OAI_API_VERSION", "2024-08-01-preview")

# ---------------------------------------------------------------------------
# Azure AI Search (v2.0 新增)
# ---------------------------------------------------------------------------
AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX", "")

# ---------------------------------------------------------------------------
# Payload CMS (v2.0 新增)
# ---------------------------------------------------------------------------
PAYLOAD_URL: str = os.getenv("PAYLOAD_URL", "http://localhost:3000")
PAYLOAD_API_KEY: str = os.getenv("PAYLOAD_API_KEY", "")

# ---------------------------------------------------------------------------
# Engine API
# ---------------------------------------------------------------------------
ENGINE_HOST: str = os.getenv("ENGINE_HOST", "0.0.0.0")
ENGINE_PORT: int = int(os.getenv("ENGINE_PORT", "8000"))

CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000"
).split(",")

TOP_K_DEFAULT: int = int(os.getenv("TOP_K_DEFAULT", "5"))
