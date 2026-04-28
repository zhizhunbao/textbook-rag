"""user_docs — User private document lifecycle management.

Public API:
    user_collection_name   — Build user-private ChromaDB collection name
    ensure_user_collection — Idempotent creation of user-private collection
    get_user_doc_stats     — Collection stats for a user/persona pair
    update_user_doc        — Update UserDocuments record in Payload CMS
"""

from .manager import (
    ensure_user_collection,
    get_user_doc_stats,
    update_user_doc,
    user_collection_name,
)

__all__ = [
    "ensure_user_collection",
    "get_user_doc_stats",
    "update_user_doc",
    "user_collection_name",
]
