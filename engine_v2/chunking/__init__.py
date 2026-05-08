"""chunking — MinerU PDF parsing and text splitting (GPU-accelerated).

Aligns with llama_index.core.node_parser (aliased as 'chunking' for clarity).

This module handles the heavy lifting of converting raw PDFs into structured
text chunks via MinerU's GPU-accelerated layout analysis pipeline:

    1. PDF → MinerU GPU parsing → content_list.json (layout + OCR)
    2. Chapter/section detection from heading structure
    3. Section-aware merging of small content items into retrieval-ready chunks
    4. Content item extraction (text blocks, tables, image captions)

Components:
    - chapter_extractor.py  — Chapter/section heading detection and assignment
    - section_merger.py     — Merge small body-text items into section-level chunks
    - (future) mineru_runner.py — MinerU CLI/API wrapper for GPU parsing

Used by:
    - readers/   — MinerUReader loads parsed chunks, uses chapter assignment
    - ingestion/ — IngestionPipeline composes chunking + embeddings
    - toc/       — TOC extraction reuses chapter detection
"""

from engine_v2.chunking.chapter_extractor import (
    extract_chapters,
    build_chapter_ranges,
    assign_chapter,
)
from engine_v2.chunking.section_merger import merge_content_items

__all__ = [
    "extract_chapters",
    "build_chapter_ranges",
    "assign_chapter",
    "merge_content_items",
]

