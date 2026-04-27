"""settings — Unified engine configuration + LlamaIndex Settings singleton.

Responsibilities:
    - Load .env from project root
    - Export project-specific constants (paths, model config, Payload CMS)
    - Configure LlamaIndex Settings singleton (llm, embed_model)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# Load .env from project root
# ============================================================
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# ============================================================
# Data paths
# ============================================================
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(_PROJECT_ROOT / "data")))
CHROMA_PERSIST_DIR: Path = Path(
    os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_persist"))
)
MINERU_OUTPUT_DIR: Path = Path(
    os.getenv("MINERU_OUTPUT_DIR", str(DATA_DIR / "mineru_output"))
)

# ============================================================
# Model config
# ============================================================
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
AZURE_OAI_ENDPOINT: str = os.getenv("AZURE_OAI_ENDPOINT", "")
AZURE_OAI_KEY: str = os.getenv("AZURE_OAI_KEY", "")
AZURE_OAI_DEPLOYMENT: str = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OAI_API_VERSION: str = os.getenv(
    "AZURE_OAI_API_VERSION", "2024-08-01-preview"
)

# ============================================================
# Payload CMS
# ============================================================
PAYLOAD_URL: str = os.getenv("PAYLOAD_URL", "http://localhost:3001")
PAYLOAD_API_KEY: str = os.getenv("PAYLOAD_API_KEY", "")
PAYLOAD_ADMIN_EMAIL: str = os.getenv("PAYLOAD_ADMIN_EMAIL", "")
PAYLOAD_ADMIN_PASSWORD: str = os.getenv("PAYLOAD_ADMIN_PASSWORD", "")

# ============================================================
# Engine API
# ============================================================
ENGINE_HOST: str = os.getenv("ENGINE_HOST", "0.0.0.0")
ENGINE_PORT: int = int(os.getenv("ENGINE_PORT", "8001"))
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:3001"
).split(",")

# ============================================================
# RAG defaults
# ============================================================
TOP_K: int = int(os.getenv("TOP_K", "5"))
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "textbook_chunks")

# ============================================================
# Reranker (Stage 2 — semantic reranking after retrieval)
# ============================================================
# CrossEncoder reranker — lightweight, ~100MB model, <100ms inference
# Always-on by default to filter BM25 keyword noise (e.g. cross-book contamination)
RERANKER_ENABLED: bool = os.getenv("RERANKER_ENABLED", "true").lower() in (
    "true", "1", "yes",
)
RERANKER_MODEL: str = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
RERANKER_TOP_N: int = int(os.getenv("RERANKER_TOP_N", "5"))
# Similarity cutoff — drop chunks below this threshold after reranking
# 0.0 = keep all; increase to filter more aggressively
SIMILARITY_CUTOFF: float = float(os.getenv("SIMILARITY_CUTOFF", "0.01"))

# ============================================================
# Auto-evaluation (EV2-T3)
# ============================================================
AUTO_EVAL_ENABLED: bool = os.getenv("AUTO_EVAL_ENABLED", "false").lower() in (
    "true", "1", "yes",
)
# Pass thresholds: faithfulness ≥ 0.7 AND answer_score ≥ 0.6
EVAL_PASS_FAITHFULNESS: float = float(os.getenv("EVAL_PASS_FAITHFULNESS", "0.7"))
EVAL_PASS_ANSWER_SCORE: float = float(os.getenv("EVAL_PASS_ANSWER_SCORE", "0.6"))

# ============================================================
# Guidelines for GuidelineEvaluator (EI-T3-01)
# ============================================================
QUALITY_GUIDELINES = (
    "The response MUST directly answer the user's question.\n"
    "The response MUST cite specific evidence from the provided context.\n"
    "The response MUST NOT include information not supported by the context.\n"
    "The response MUST use professional, clear language.\n"
    "The response MUST include quantitative data when available in the context.\n"
    "The response MUST acknowledge when the context does not contain sufficient information.\n"
)


# ============================================================
# Configure LlamaIndex Settings singleton
# ============================================================
def init_settings() -> None:
    """Initialise LlamaIndex global Settings.

    Call once at startup (in api/app.py lifespan or script entry).
    Configures:
        Settings.llm        → resolved via llms.resolver (Azure or Ollama)
        Settings.embed_model → resolved via embeddings.resolver (HuggingFace)
    """
    from llama_index.core.settings import Settings

    from engine_v2.embeddings import resolve_embed_model
    from engine_v2.llms.resolver import resolve_llm

    # Embedding model (delegates to embeddings/ module)
    Settings.embed_model = resolve_embed_model()

    # LLM: delegate to llms/ module for provider routing
    Settings.llm = resolve_llm()
