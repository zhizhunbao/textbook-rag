"""Unified engine settings — configures LlamaIndex Settings singleton.

Aligns with llama_index.core.settings.Settings pattern:
    - Settings.llm       → Ollama or AzureOpenAI
    - Settings.embed_model → HuggingFaceEmbedding
    - Settings.chunk_size / chunk_overlap (not used, MinerU pre-chunks)

Also exports project-specific constants (paths, Payload CMS config).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(_PROJECT_ROOT / "data")))
CHROMA_PERSIST_DIR: Path = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_persist"))
)
MINERU_OUTPUT_DIR: Path = Path(
    os.getenv("MINERU_OUTPUT_DIR", str(DATA_DIR / "mineru_output"))
)

# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
AZURE_OAI_ENDPOINT: str = os.getenv("AZURE_OAI_ENDPOINT", "")
AZURE_OAI_KEY: str = os.getenv("AZURE_OAI_KEY", "")
AZURE_OAI_DEPLOYMENT: str = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OAI_API_VERSION: str = os.getenv(
    "AZURE_OAI_API_VERSION", "2024-08-01-preview"
)

# ---------------------------------------------------------------------------
# Payload CMS
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

# ---------------------------------------------------------------------------
# RAG defaults
# ---------------------------------------------------------------------------
TOP_K: int = int(os.getenv("TOP_K", "5"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "textbook_chunks")


# ---------------------------------------------------------------------------
# Configure LlamaIndex Settings singleton
# ---------------------------------------------------------------------------
def init_settings() -> None:
    """Initialise LlamaIndex global Settings.

    Call once at startup (in api/app.py lifespan or script entry).
    Configures:
        Settings.llm        → resolved via llms.resolver (Azure or Ollama)
        Settings.embed_model → HuggingFaceEmbedding
    """
    from llama_index.core.settings import Settings
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    from engine_v2.llms.resolver import resolve_llm

    # Embedding model (always local)
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)

    # LLM: delegate to llms/ module for provider routing
    Settings.llm = resolve_llm()
