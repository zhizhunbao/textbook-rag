"""personas — Consulting persona knowledge base lifecycle management.

Public API:
    ensure_persona_collection — Idempotent ChromaDB collection creation
    get_persona_stats         — Collection metadata (chunk_count, doc_count)
"""

from .registry import ensure_persona_collection, get_persona_stats

__all__ = ["ensure_persona_collection", "get_persona_stats"]
