"""Shared data types — aligns with llama_index.core.schema.

Extends LlamaIndex's Document/TextNode with textbook-specific metadata.
Replaces engine v1's rag/types.py + ingest/chunk_builder.py dataclasses.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class BookMeta:
    """Metadata for a single book (lives in Payload CMS)."""

    book_id: str
    title: str
    authors: str = ""
    category: str = "textbook"
    total_pages: int = 0


@dataclass
class SourceLocator:
    """Bounding box for a chunk on a PDF page."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    page_width: float = 0.0
    page_height: float = 0.0


@dataclass
class RAGResponse:
    """Full response from QueryEngine.query()."""

    answer: str
    sources: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Source builder — shared across query routes + query_engine
# ============================================================
# Maximum characters to include in full_content (for hover preview)
_FULL_CONTENT_MAX = 2000
# Maximum characters for the backwards-compatible snippet field
_SNIPPET_MAX = 300


def build_source(node_with_score: Any, index: int) -> dict[str, Any]:
    """Convert a LlamaIndex NodeWithScore to our source dict.

    Used by both the sync query route and the SSE streaming route.

    Fields added for Citation UX (Sprint 2):
        full_content  — complete chunk text (≤2000 chars) for hover preview
        book_title    — human-readable book name from node metadata
        chapter_title — chapter heading from node metadata
    """
    node = node_with_score.node
    meta = node.metadata
    page_idx = meta.get("page_idx", 0)
    content = node.get_content()

    # Strip "Source N:\n" prefix added by CitationLabelPostprocessor
    content = re.sub(r"^Source \d+:\n", "", content)

    # ── Bounding box resolution ──────────────────────────────
    x0 = float(meta.get("bbox_x0", 0))
    y0 = float(meta.get("bbox_y0", 0))
    x1 = float(meta.get("bbox_x1", 0))
    y1 = float(meta.get("bbox_y1", 0))
    pw = float(meta.get("page_width", 0))
    ph = float(meta.get("page_height", 0))
    has_bbox = any(v != 0 for v in (x0, y0, x1, y1))

    # Fallback: legacy flat bbox array (from MinerUReader ingestion path)
    if not has_bbox:
        bbox = meta.get("bbox", [0, 0, 0, 0])
        if bbox and any(v != 0 for v in bbox):
            x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
            has_bbox = True

    bboxes = []
    if has_bbox:
        bboxes.append({
            "x0": x0, "y0": y0,
            "x1": x1, "y1": y1,
            "page_number": page_idx + 1,
            "page_width": pw,
            "page_height": ph,
        })

    return {
        "citation_index": index,
        "chunk_id": node.id_,
        "book_id": meta.get("book_id", ""),
        "book_title": meta.get("book_title", ""),
        "chapter_title": meta.get("chapter_title", meta.get("chapter_key", "")),
        "page_number": page_idx + 1,
        "content_type": meta.get("content_type", "text"),
        "chapter_key": meta.get("chapter_key"),
        "category": meta.get("category", "textbook"),
        "full_content": content[:_FULL_CONTENT_MAX],
        "snippet": content[:_SNIPPET_MAX],
        "score": node_with_score.score,
        "bbox": {
            "x0": x0, "y0": y0,
            "x1": x1, "y1": y1,
            "page": page_idx,
        } if has_bbox else None,
        "bboxes": bboxes,
    }


# ============================================================
# Source deduplication — DEPRECATED
# ============================================================
# This post-hoc dedup is superseded by
# TextbookCitationQueryEngine._create_citation_nodes() which merges
# same-page chunks BEFORE LLM synthesis. Kept for backwards compat.

def deduplicate_sources(
    answer: str,
    sources: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Merge sources that share the same book_id + page_number.

    When the hybrid retriever returns multiple chunks from the same
    page of the same document, the user sees redundant citation chips
    (e.g. [1] 王鹏 p.2, [2] 王鹏 p.2, [3] 王鹏 p.2).

    This function:
        1. Groups sources by (book_id, page_number).
        2. Merges each group into a single canonical source, combining
           full_content/snippet, keeping the best score, and merging bboxes.
        3. Remaps [N] markers in the answer text to reflect the new indices.

    Args:
        answer: LLM answer text containing [N] citation markers.
        sources: Original source list from build_source().

    Returns:
        (remapped_answer, deduplicated_sources) tuple.
    """
    if not sources:
        return answer, sources

    # ── Step 1: Group by (book_id, page_number) ──────────────
    # Preserve insertion order so the first occurrence defines the group.
    groups: OrderedDict[tuple[str, int], list[dict[str, Any]]] = OrderedDict()
    for src in sources:
        key = (src.get("book_id", ""), src.get("page_number", 0))
        groups.setdefault(key, []).append(src)

    # ── Step 2: Merge each group into a single source ────────
    merged: list[dict[str, Any]] = []
    # old_index → new_index mapping for answer text rewriting
    index_remap: dict[int, int] = {}

    for new_idx_0, ((_bid, _pn), group) in enumerate(groups.items()):
        new_idx = new_idx_0 + 1  # 1-based citation index

        # Record remapping for every old citation_index in this group
        for src in group:
            old_ci = src.get("citation_index")
            if old_ci is not None:
                index_remap[old_ci] = new_idx

        # Pick the source with the highest score as the canonical entry
        best = max(group, key=lambda s: s.get("score") or 0)
        canonical = {**best, "citation_index": new_idx}

        # Merge full_content from all chunks (separated by \n---\n)
        contents = []
        seen_content: set[str] = set()
        for src in group:
            fc = src.get("full_content", "")
            if fc and fc not in seen_content:
                seen_content.add(fc)
                contents.append(fc)
        if len(contents) > 1:
            merged_content = "\n---\n".join(contents)
            canonical["full_content"] = merged_content[:_FULL_CONTENT_MAX]
            canonical["snippet"] = merged_content[:_SNIPPET_MAX]

        # Merge bboxes from all chunks
        all_bboxes: list[dict[str, Any]] = []
        for src in group:
            for bb in src.get("bboxes", []):
                all_bboxes.append(bb)
        if all_bboxes:
            canonical["bboxes"] = all_bboxes
            # Keep bbox as the first valid bbox (for backwards compat)
            canonical["bbox"] = best.get("bbox")

        merged.append(canonical)

    # Short-circuit: no duplicates found
    if len(merged) == len(sources):
        return answer, sources

    # ── Step 3: Remap [N] markers in the answer text ─────────
    # Keep the FIRST occurrence of each [N] per paragraph;
    # remove later duplicates that were created by merging.
    seen_per_para: set[int] = set()

    def _replace_citation(m: re.Match) -> str:
        old_idx = int(m.group(1))
        new_idx = index_remap.get(old_idx, old_idx)
        if new_idx in seen_per_para:
            return ""  # drop later duplicate
        seen_per_para.add(new_idx)
        return f"[{new_idx}]"

    # Process paragraph by paragraph so [1] in different paragraphs is kept
    paragraphs = answer.split("\n\n")
    remapped_parts: list[str] = []
    for para in paragraphs:
        seen_per_para = set()
        remapped = re.sub(r"\[(\d+)\]", _replace_citation, para)
        # Clean up leftover whitespace from removed markers
        remapped = re.sub(r"  +", " ", remapped).strip()
        remapped_parts.append(remapped)

    remapped_answer = "\n\n".join(remapped_parts)

    logger.info(
        "Deduplicated sources: {} → {} (merged {} duplicates)",
        len(sources), len(merged), len(sources) - len(merged),
    )

    return remapped_answer, merged
