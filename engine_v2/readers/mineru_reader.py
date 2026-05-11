"""MinerUReader — reads MinerU content_list.json into LlamaIndex Documents.

Aligns with llama_index.core.readers.base.BaseReader interface.
Each content item (text / table / image caption) becomes one Document
with rich metadata (page, bbox, content_type, chapter).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from loguru import logger

from engine_v2.chunking import assign_chapter, build_chapter_ranges, extract_chapters


class MinerUReader(BaseReader):
    """Read MinerU auto-parsed output for one book into LlamaIndex Documents.

    Each item in content_list.json becomes a Document with metadata:
        - book_id, category, content_type, page_idx
        - bbox (normalised to PDF points)
        - chapter_key, reading_order

    Args:
        mineru_dir: Root directory of MinerU output.
        merge_sections: If True, merge consecutive body-text items into
            section-level chunks via SectionMerger. Default False — raw MinerU
            chunks are kept for granular retrieval + CrossEncoder reranking.
    """

    def __init__(
        self, mineru_dir: Path | str, *, merge_sections: bool = False,
    ) -> None:
        self._mineru_dir = Path(mineru_dir)
        self._merge_sections = merge_sections

    # ------------------------------------------------------------------
    # Auto-dir resolution: supports both flattened and legacy layouts
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_auto_dir(
        book_root: Path, book_dir_name: str,
    ) -> tuple[Path | None, str | None]:
        """Find the auto/ directory and file stem under a book's output dir.

        Supports two layouts:
          - Flattened (post flatten_mineru.py):
              <book_root>/auto/<book_dir_name>_content_list.json
          - Legacy nested (raw MinerU output):
              <book_root>/<pdf_stem>/auto/<pdf_stem>_content_list.json

        Returns:
            (auto_dir, file_stem) or (None, None) if not found.
        """
        # Try flattened layout first
        flat_auto = book_root / "auto"
        if flat_auto.is_dir():
            # Verify it has content_list.json (not just an empty dir)
            cl = list(flat_auto.glob("*_content_list.json"))
            if cl:
                file_stem = cl[0].stem.replace("_content_list", "")
                return flat_auto, file_stem

        # Try legacy nested layout: <book_root>/<inner_dir>/auto/
        for inner in book_root.iterdir():
            if inner.is_dir() and inner.name != "auto":
                nested_auto = inner / "auto"
                if nested_auto.is_dir():
                    cl = list(nested_auto.glob("*_content_list.json"))
                    if cl:
                        file_stem = cl[0].stem.replace("_content_list", "")
                        return nested_auto, file_stem

        return None, None

    def lazy_load_data(  # type: ignore[override]
        self,
        book_dir_name: str,
        category: str = "textbook",
        **kwargs: Any,
    ) -> Iterable[Document]:
        """Yield one Document per content item (or per merged section if enabled).

        When merge_sections=False (default), each raw MinerU content item
        becomes one Document. When True, SectionMerger groups consecutive
        body-text items into larger semantic chunks.

        Args:
            book_dir_name: Directory name of the book under mineru_dir/category/
            category: textbook | ecdev | real_estate | federal-ircc | prov-* | algonquin-*
        """
        book_root = self._mineru_dir / category / book_dir_name
        auto_dir, file_stem = self._resolve_auto_dir(book_root, book_dir_name)
        if auto_dir is None:
            logger.warning("auto/ dir not found under: {}", book_root)
            return

        content_list_path = auto_dir / f"{file_stem}_content_list.json"
        middle_json_path = auto_dir / f"{file_stem}_middle.json"

        if not content_list_path.exists():
            logger.warning("content_list.json not found: {}", content_list_path)
            return

        with open(content_list_path, "r", encoding="utf-8") as f:
            content_list: list[dict] = json.load(f)

        page_sizes = self._load_page_sizes(middle_json_path)
        chapters = self._extract_chapters(content_list)
        chapter_ranges = self._build_chapter_ranges(content_list, chapters)

        if self._merge_sections:
            yield from self._load_merged(
                content_list, page_sizes, chapter_ranges,
                book_dir_name, category,
            )
        else:
            yield from self._load_raw(
                content_list, page_sizes, chapter_ranges,
                book_dir_name, category,
            )

    # ------------------------------------------------------------------
    # Raw mode: one Document per MinerU content item (no merging)
    # ------------------------------------------------------------------

    def _load_raw(
        self,
        content_list: list[dict],
        page_sizes: dict[int, tuple[float, float]],
        chapter_ranges: list[tuple[str, int, int]],
        book_dir_name: str,
        category: str,
    ) -> Iterable[Document]:
        """Yield one Document per raw content item."""
        reading_order = 0
        for item in content_list:
            item_type = item.get("type", "")
            text = self._extract_text(item, item_type)
            if not text or item_type == "discarded":
                continue

            page_idx = item.get("page_idx", 0)
            raw_bbox = item.get("bbox", [0, 0, 0, 0])
            bbox = self._normalise_bbox(raw_bbox, page_idx, page_sizes)
            chapter_key = self._assign_chapter(page_idx, chapter_ranges)
            pw, ph = page_sizes.get(page_idx, (0.0, 0.0))

            source_bboxes = [{
                "page_idx": page_idx,
                "bbox": bbox,
                "page_width": pw,
                "page_height": ph,
            }]

            doc_id = f"{book_dir_name}_{reading_order:06d}"
            yield Document(
                doc_id=doc_id,
                text=text,
                metadata={
                    "book_id": book_dir_name,
                    "category": category,
                    "content_type": item_type or "text",
                    "page_idx": page_idx,
                    "bbox": bbox,
                    "page_width": pw,
                    "page_height": ph,
                    "chapter_key": chapter_key,
                    "reading_order": reading_order,
                    "text_level": item.get("text_level"),
                    "source_bboxes": source_bboxes,
                },
                excluded_llm_metadata_keys=[
                    "bbox", "reading_order", "page_width", "page_height",
                    "source_bboxes",
                ],
            )
            reading_order += 1

        logger.info(
            "MinerUReader: loaded {} documents from {} (raw mode, with context prefix)",
            reading_order, book_dir_name,
        )

    # ------------------------------------------------------------------
    # Merged mode: section-aware chunking via SectionMerger
    # ------------------------------------------------------------------

    def _load_merged(
        self,
        content_list: list[dict],
        page_sizes: dict[int, tuple[float, float]],
        chapter_ranges: list[tuple[str, int, int]],
        book_dir_name: str,
        category: str,
    ) -> Iterable[Document]:
        """Yield one Document per merged section chunk."""
        from engine_v2.chunking.section_merger import merge_content_items

        merged_items = merge_content_items(
            content_list,
            page_sizes=page_sizes,
        )

        reading_order = 0
        for merged in merged_items:
            text = self._clean_latex_artifacts(merged.text)
            if not text:
                continue

            page_idx = merged.page_idx

            # Primary bbox (union of all sub-items) — normalised to PDF points
            if merged.bboxes:
                primary_bbox = merged.primary_bbox
                primary_bbox = self._normalise_bbox(
                    primary_bbox, page_idx, page_sizes,
                )
            else:
                primary_bbox = [0.0, 0.0, 0.0, 0.0]

            chapter_key = self._assign_chapter(page_idx, chapter_ranges)
            pw, ph = page_sizes.get(page_idx, (0.0, 0.0))

            source_bboxes = []
            for bb in merged.bboxes:
                norm_bbox = self._normalise_bbox(
                    bb.bbox, bb.page_idx, page_sizes,
                )
                source_bboxes.append({
                    "page_idx": bb.page_idx,
                    "bbox": norm_bbox,
                    "page_width": bb.page_width,
                    "page_height": bb.page_height,
                })

            doc_id = f"{book_dir_name}_{reading_order:06d}"
            yield Document(
                doc_id=doc_id,
                text=text,
                metadata={
                    "book_id": book_dir_name,
                    "category": category,
                    "content_type": merged.content_type,
                    "page_idx": page_idx,
                    "bbox": primary_bbox,
                    "page_width": pw,
                    "page_height": ph,
                    "chapter_key": chapter_key,
                    "reading_order": reading_order,
                    "text_level": merged.text_level,
                    "source_bboxes": source_bboxes,
                },
                excluded_llm_metadata_keys=[
                    "bbox", "reading_order", "page_width", "page_height",
                    "source_bboxes",
                ],
            )
            reading_order += 1

        logger.info(
            "MinerUReader: loaded {} documents from {} (merged mode)",
            reading_order, book_dir_name,
        )

    # ------------------------------------------------------------------
    # Internal helpers — text extraction and bbox normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_latex_artifacts(text: str) -> str:
        """Strip LaTeX math-mode artifacts from MinerU PDF text.

        MinerU wraps numbers/percentages/currency in LaTeX math delimiters:
            $4 . 1 \\%$   →  4.1%
            $\\$ 709,002$  →  $709,002
            $36 . 2 \\%$  →  36.2%
            $2 , 851$     →  2,851

        Also fixes:
            \\mathsf{up}:  \\mathsf { u p }  →  up
            spaced digits:    5 6.1  →  56.1
            spaced decimals:  1 . 5  →  1.5
            spaced commas:    709 , 002  →  709,002
            dangling $:       leftover dollar signs from math mode
            \\% outside math: \\%  →  %
        """
        import re

        if "$" not in text and "\\" not in text:
            return text  # fast path: nothing to clean

        # Step 0: Strip LaTeX font commands: \mathsf{up}, \mathrm{GDP}, \textbf{...}
        # e.g. \mathsf { u p }  →  up  (also collapse inner spaces for single-char tokens)
        text = re.sub(
            r'\\(?:math(?:sf|rm|bf|it|bb|cal)|text(?:bf|it|rm|sf))\s*\{([^}]*)\}',
            lambda m: m.group(1).replace(" ", ""),
            text,
        )

        # Step 1: Handle $\$ NNN$ pattern (currency)  →  $NNN
        # e.g. $\$ 709,002$  →  $709,002
        text = re.sub(
            r'\$\s*\\?\$\s*([0-9][0-9, .]*)\$',
            lambda m: "$" + m.group(1).replace(" ", ""),
            text,
        )

        # Step 2: Handle $N . N \%$ pattern (percentages)  →  N.N%
        # e.g. $4 . 1 \%$  →  4.1%
        text = re.sub(
            r'\$\s*([0-9][0-9 ,.]*)\\?%\s*\$',
            lambda m: m.group(1).replace(" ", "") + "%",
            text,
        )

        # Step 3: Handle remaining $number$ patterns (plain numbers in math mode)
        # e.g. $2 , 851$  →  2,851
        text = re.sub(
            r'\$\s*([0-9][0-9 ,.]*[0-9])\s*\$',
            lambda m: m.group(1).replace(" ", ""),
            text,
        )

        # Step 4: Merge spaced digits before decimals: 5 6.1 → 56.1
        # Handles MinerU splitting numbers across PDF character positions
        text = re.sub(r'(\d)\s+(\d+\.\d+)', r'\1\2', text)

        # Step 5: Fix spaced decimals outside math mode: 1 . 5 → 1.5
        text = re.sub(r'(\d)\s+\.\s+(\d)', r'\1.\2', text)

        # Step 6: Fix spaced commas in numbers: 709 , 002 → 709,002
        text = re.sub(r'(\d)\s+,\s+(\d)', r'\1,\2', text)

        # Step 7: Fix standalone \% → %
        text = text.replace("\\%", "%")

        # Step 8: Clean up any remaining single $ that aren't currency
        # (don't remove $ followed by a digit — that's likely currency like $633,000)
        # Remove isolated $ not adjacent to digits
        text = re.sub(r'\$(?!\d)', '', text)

        # Step 9: Fix smart quote / encoding artifacts
        text = text.replace("\u0092", "'").replace("\u0093", "\u201c").replace("\u0094", "\u201d")

        return text

    @staticmethod
    def _extract_text(item: dict, item_type: str) -> str:
        """Extract text content from a MinerU content item."""
        text = item.get("text", "").strip()
        if not text and item_type == "table":
            table_body = item.get("table_body", "")
            if table_body:
                text = MinerUReader._html_table_to_text(table_body)
        if not text and item_type == "image":
            captions = item.get("image_caption", [])
            text = " ".join(captions) if captions else ""
        text = text.strip()
        # Clean LaTeX artifacts from MinerU output
        if text:
            text = MinerUReader._clean_latex_artifacts(text)
        return text

    @staticmethod
    def _html_table_to_text(html: str) -> str:
        """Convert HTML table to readable plain text.

        Transforms <table><tr><td>...</td></tr></table> into a readable
        format where each row is on a new line and cells are separated
        by ' | '. This makes table content comprehensible for both
        embedding models and LLM synthesizers.

        Example:
            <table><tr><td>CRS score</td><td>400</td></tr></table>
            → "CRS score | 400"
        """
        import re
        # Replace row boundaries
        text = re.sub(r'</tr>\s*<tr[^>]*>', '\n', html, flags=re.IGNORECASE)
        # Replace cell boundaries
        text = re.sub(r'</t[dh]>\s*<t[dh][^>]*>', ' | ', text, flags=re.IGNORECASE)
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r' +', ' ', text)
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        return text

    @staticmethod
    def _load_page_sizes(path: Path) -> dict[int, tuple[float, float]]:
        """Load page dimensions from middle.json."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            return {}

        pages = data.get("pdf_info", data) if isinstance(data, dict) else data
        if not isinstance(pages, list):
            return {}

        result: dict[int, tuple[float, float]] = {}
        for page in pages:
            idx = page.get("page_idx")
            size = page.get("page_size")
            if idx is not None and size and len(size) == 2:
                result[idx] = (float(size[0]), float(size[1]))
        return result

    @staticmethod
    def _normalise_bbox(
        raw_bbox: list,
        page_idx: int,
        page_sizes: dict[int, tuple[float, float]],
    ) -> list[float]:
        """Convert normalised 1000x1000 canvas → PDF points."""
        if len(raw_bbox) < 4:
            return [0.0, 0.0, 0.0, 0.0]
        pw, ph = page_sizes.get(page_idx, (0.0, 0.0))
        if pw and ph:
            return [
                raw_bbox[0] / 1000 * pw,
                raw_bbox[1] / 1000 * ph,
                raw_bbox[2] / 1000 * pw,
                raw_bbox[3] / 1000 * ph,
            ]
        return [float(v) for v in raw_bbox[:4]]

    # ------------------------------------------------------------------
    # Chapter structure — delegates to chunking/ module
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_chapters(content_list: list[dict]) -> list[dict]:
        """Extract chapter headings (delegates to chunking.extract_chapters)."""
        return extract_chapters(content_list)

    @staticmethod
    def _build_chapter_ranges(
        content_list: list[dict],
        chapters: list[dict],
    ) -> list[tuple[str, int, int]]:
        """Build chapter page ranges (delegates to chunking.build_chapter_ranges)."""
        return build_chapter_ranges(content_list, chapters)

    @staticmethod
    def _assign_chapter(
        page_idx: int,
        ranges: list[tuple[str, int, int]],
    ) -> str | None:
        """Assign chapter key to page (delegates to chunking.assign_chapter)."""
        return assign_chapter(page_idx, ranges)
