"""CitationEngine — validates, sanitizes, and maps citations.

Full implementation. Extracted and generalised from v1.0 generation_service._sanitize_citations().
"""

from __future__ import annotations

import re

from engine.rag.types import ChunkHit, CitationResult


class CitationEngine:
    """Validates and sanitizes [N] citation markers in generated answers.

    Responsibilities:
    - Identify citation markers [1], [2], ... in the raw answer
    - Validate each against the chunk list (must be in 1..len(chunks))
    - Remove invalid citations from the answer
    - Map valid [N] markers to SourceInfo dicts (including bbox)
    """

    _CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    def process(self, raw_answer: str, chunks: list[ChunkHit]) -> CitationResult:
        """Full citation pipeline: validate → sanitize → map.

        Args:
            raw_answer: Raw text from the LLM, may contain [N] markers.
            chunks:     The top_k chunks used as context (1-indexed in prompt).

        Returns:
            CitationResult with cleaned answer, valid/invalid lists, sources.
        """
        valid_range = set(range(1, len(chunks) + 1))
        found = {int(m) for m in self._CITATION_PATTERN.findall(raw_answer)}

        valid_citations = sorted(found & valid_range)
        invalid_citations = sorted(found - valid_range)

        # Remove invalid markers from answer
        cleaned = self._remove_invalid(raw_answer, invalid_citations)

        # Map valid citations to SourceInfo dicts
        sources = self._map_to_sources(valid_citations, chunks)

        return CitationResult(
            cleaned_answer=cleaned,
            raw_answer=raw_answer,
            valid_citations=valid_citations,
            invalid_citations=invalid_citations,
            sources=sources,
        )

    def _remove_invalid(self, text: str, invalid: list[int]) -> str:
        if not invalid:
            return text
        invalid_set = set(invalid)

        def replacer(m: re.Match) -> str:
            n = int(m.group(1))
            return "" if n in invalid_set else m.group(0)

        return self._CITATION_PATTERN.sub(replacer, text).strip()

    def _map_to_sources(
        self, valid_citations: list[int], chunks: list[ChunkHit]
    ) -> list[dict]:
        sources = []
        for n in valid_citations:
            idx = n - 1  # 1-indexed → 0-indexed
            if idx >= len(chunks):
                continue
            chunk = chunks[idx]

            # Build primary bbox from first source_locator
            bbox = None
            page_num = chunk.primary_page_number
            if chunk.source_locators:
                loc = chunk.source_locators[0]
                bbox = {
                    "x0": loc.get("x0"),
                    "y0": loc.get("y0"),
                    "x1": loc.get("x1"),
                    "y1": loc.get("y1"),
                    "page_width": loc.get("width"),
                    "page_height": loc.get("height"),
                }
                page_num = loc.get("page_number", page_num)

            sources.append({
                "citation_index": n,
                "chunk_id": chunk.chunk_id,
                "book_title": chunk.book_title,
                "chapter_title": chunk.chapter_title,
                "page_number": page_num,
                "content_type": chunk.content_type,
                "snippet": chunk.text[:300],
                "bbox": bbox,
                "rrf_score": chunk.rrf_score,
                "fts_score": chunk.fts_score,
                "vec_distance": chunk.vec_distance,
            })
        return sources
